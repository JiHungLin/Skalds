"""
Dispatcher Module

Handles task assignment to available Skalds based on configured strategies.
Based on the reference implementation but enhanced for SystemController use.
"""

import asyncio
import time
import threading
import json
from typing import Dict, List, Optional
from skald.proxy.redis import RedisProxy
from skald.proxy.mongo import MongoProxy
from skald.proxy.kafka import KafkaProxy, KafkaTopic
from skald.model.event import TaskEvent
from skald.system_controller.store.skald_store import SkaldStore
from skald.model.task import TaskLifecycleStatus
from skald.repository.repository import TaskRepository
from skald.config.systemconfig import SystemConfig
from skald.config._enum import DispatcherStrategyEnum
from skald.utils.logging import logger


class Dispatcher:
    """
    Dispatches tasks to available Skalds based on assignment strategies.
    
    This dispatcher:
    - Finds tasks that need assignment
    - Selects appropriate Skalds based on strategy
    - Updates task executor and status
    - Sends assignment events via Kafka
    """
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls, redis_proxy: RedisProxy, mongo_proxy: MongoProxy, kafka_proxy: KafkaProxy, duration: int = 5):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, redis_proxy: RedisProxy, mongo_proxy: MongoProxy, kafka_proxy: KafkaProxy, duration: int = 5):
        if not getattr(self, '_initialized', False):
            self.redis_proxy = redis_proxy
            self.mongo_proxy = mongo_proxy
            self.kafka_proxy = kafka_proxy
            self.duration = duration
            self.skald_store = SkaldStore()
            self.task_repository = TaskRepository(mongo_proxy)
            self.strategy = SystemConfig.DISPATCHER_STRATEGY
            
            self._running = False
            self._thread: Optional[threading.Thread] = None
            self._event_loop: Optional[asyncio.AbstractEventLoop] = None
            self._initialized = True
            logger.info(f"Dispatcher initialized with {duration}s interval, strategy: {self.strategy}")

    def _work(self) -> None:
        """Main dispatching loop with async support."""
        # Create new event loop for this thread
        self._event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._event_loop)
        
        try:
            while self._running:
                try:
                    self._event_loop.run_until_complete(self._dispatch_tasks())
                    time.sleep(self.duration)
                except Exception as e:
                    logger.error(f"Dispatcher error: {e}")
                    time.sleep(self.duration)
        finally:
            if self._event_loop:
                self._event_loop.close()

    async def _dispatch_tasks(self) -> None:
        """Main dispatching logic."""
        try:
            # First check if we have available Skalds before doing anything
            available_skalds = self._get_available_skalds()
            
            if not available_skalds:
                logger.debug("No Skalds available for task assignment")
                return
            
            # Only get tasks that need assignment if we have available Skalds
            tasks_to_assign = await self._get_tasks_needing_assignment()
            
            if not tasks_to_assign:
                logger.debug("No tasks need assignment")
                return
            
            logger.info(f"Found {len(tasks_to_assign)} tasks to assign and {len(available_skalds)} available Skalds")
            
            # Assign tasks using the configured strategy
            assignments = self._calculate_assignments(tasks_to_assign, available_skalds)
            
            if not assignments:
                logger.debug("No task assignments calculated")
                return
            
            # Execute assignments
            for task, skald_id in assignments:
                await self._assign_task_to_skald(task, skald_id)
                
        except Exception as e:
            logger.error(f"Error in _dispatch_tasks: {e}")

    async def _get_tasks_needing_assignment(self) -> List:
        """Get tasks from MongoDB that need assignment."""
        try:
            collection = self.mongo_proxy.db.tasks
            
            # Find tasks that are not Running, Cancelled, or Assigning
            excluded_statuses = [
                TaskLifecycleStatus.RUNNING.value,
                TaskLifecycleStatus.CANCELLED.value,
                TaskLifecycleStatus.PAUSED.value,
                TaskLifecycleStatus.ASSIGNING.value,
                TaskLifecycleStatus.FINISHED.value,
            ]
            
            cursor = collection.find({
                "lifecycleStatus": {"$nin": excluded_statuses},
                "mode": "Passive"
            })
            
            tasks = []
            for doc in cursor:  # Use regular for loop instead of async for
                # Convert MongoDB document to task object
                task = type('Task', (), {
                    'id': doc['id'],
                    'className': doc.get('className', ''),
                    'lifecycleStatus': doc.get('lifecycleStatus', TaskLifecycleStatus.CREATED.value),
                    'priority': doc.get('priority', 0),
                    'executor': doc.get('executor')
                })()
                tasks.append(task)
            
            logger.debug(f"Found {len(tasks)} tasks needing assignment")
            return tasks
            
        except Exception as e:
            logger.error(f"Error getting tasks needing assignment: {e}")
            return []

    def _get_available_skalds(self) -> Dict[str, int]:
        """Get available Skalds with their current task counts."""
        try:
            # Get online node-type Skalds (only nodes can be assigned tasks)
            available_skalds = self.skald_store.get_node_skalds()
            
            # Create mapping of Skald ID to task count
            skald_task_counts = {}
            for skald_id, skald_data in available_skalds.items():
                skald_task_counts[skald_id] = skald_data.get_task_count()
            
            logger.debug(f"Found {len(skald_task_counts)} available Skalds")
            return skald_task_counts
            
        except Exception as e:
            logger.error(f"Error getting available Skalds: {e}")
            return {}

    def _calculate_assignments(self, tasks: List, available_skalds: Dict[str, int]) -> List[tuple]:
        """Calculate task assignments based on the configured strategy."""
        assignments = []
        
        # Sort tasks by priority (higher priority first)
        sorted_tasks = sorted(tasks, key=lambda t: getattr(t, 'priority', 0), reverse=True)
        
        # Create a working copy of Skald task counts
        skald_task_counts = available_skalds.copy()
        
        for task in sorted_tasks:
            if not skald_task_counts:
                logger.warning("No more Skalds available for assignment")
                break
            
            # Select Skald based on strategy
            selected_skald = self._select_skald_by_strategy(task, skald_task_counts)
            
            if selected_skald:
                assignments.append((task, selected_skald))
                # Update task count for the selected Skald
                skald_task_counts[selected_skald] += 1
                logger.debug(f"Planned assignment: Task {task.id} -> Skald {selected_skald}")
            else:
                logger.warning(f"Could not find suitable Skald for task {task.id}")
        
        return assignments

    def _select_skald_by_strategy(self, task, skald_task_counts: Dict[str, int]) -> Optional[str]:
        """Select a Skald based on the configured strategy."""
        if not skald_task_counts:
            return None
        
        if self.strategy == DispatcherStrategyEnum.LEAST_TASKS:
            # Select Skald with the least number of tasks
            return min(skald_task_counts.keys(), key=lambda x: skald_task_counts[x])
        
        elif self.strategy == DispatcherStrategyEnum.ROUND_ROBIN:
            # Simple round-robin selection
            skald_ids = list(skald_task_counts.keys())
            # Use task ID hash for consistent selection
            task_hash = hash(task.id) % len(skald_ids)
            return skald_ids[task_hash]
        
        elif self.strategy == DispatcherStrategyEnum.RANDOM:
            # Random selection
            import random
            return random.choice(list(skald_task_counts.keys()))
        
        else:
            # Default to least_tasks strategy
            logger.warning(f"Unknown strategy '{self.strategy}', using 'least_tasks'")
            return min(skald_task_counts.keys(), key=lambda x: skald_task_counts[x])

    async def _assign_task_to_skald(self, task, skald_id: str) -> None:
        """Assign a task to a specific Skald."""
        try:
            # Update task executor in MongoDB
            await self._update_task_executor(task.id, skald_id)
            
            # Update task status to Assigning
            await self._update_task_status(task.id, TaskLifecycleStatus.ASSIGNING)
            
            # Send assignment event via Kafka
            await self._send_assignment_event(task, skald_id)
            
            logger.info(f"Assigned task {task.id} to Skald {skald_id}")
            
        except Exception as e:
            logger.error(f"Error assigning task {task.id} to Skald {skald_id}: {e}")

    async def _update_task_executor(self, task_id: str, executor: str) -> None:
        """Update task executor in MongoDB."""
        try:
            collection = self.mongo_proxy.db.tasks
            result = collection.update_one(  # Remove await since pymongo is synchronous
                {"id": task_id},
                {"$set": {"executor": executor}}
            )
            
            if result.modified_count > 0:
                logger.debug(f"Updated task {task_id} executor to {executor}")
            else:
                logger.warning(f"No task found to update executor: {task_id}")
                
        except Exception as e:
            logger.error(f"Error updating task executor for {task_id}: {e}")

    async def _update_task_status(self, task_id: str, status: TaskLifecycleStatus) -> None:
        """Update task status in MongoDB."""
        try:
            collection = self.mongo_proxy.db.tasks
            result = collection.update_one(  # Remove await since pymongo is synchronous
                {"id": task_id},
                {"$set": {"lifecycleStatus": status.value}}
            )
            
            if result.modified_count > 0:
                logger.debug(f"Updated task {task_id} status to {status.value}")
            else:
                logger.warning(f"No task found to update status: {task_id}")
                
        except Exception as e:
            logger.error(f"Error updating task status for {task_id}: {e}")

    async def _send_assignment_event(self, task, skald_id: str) -> None:
        """Send task assignment event via Kafka."""
        try:
            event = TaskEvent(
                id=task.id,
                title=None,
                initiator=None,
                recipient=None,
                create_date_time=int(time.time() * 1000),
                update_date_time=int(time.time() * 1000),
                task_ids=[task.id]
            )

            assignment_message = event.model_dump_json(by_alias=True)

            self.kafka_proxy.produce(
                topic_name=KafkaTopic.TASK_ASSIGN,
                key=task.id,
                value=assignment_message
            )

            logger.debug(f"Sent assignment event for task {task.id} to Skald {skald_id}")
            
        except Exception as e:
            logger.error(f"Error sending assignment event for task {task.id}: {e}")

    def start(self) -> None:
        """Start the dispatching thread."""
        if self._running:
            logger.warning("Dispatcher is already running")
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._work, daemon=True, name="Dispatcher")
        self._thread.start()
        logger.info("Dispatcher started")

    def stop(self) -> None:
        """Stop the dispatching thread."""
        if not self._running:
            logger.warning("Dispatcher is not running")
            return
            
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
            if self._thread.is_alive():
                logger.warning("Dispatcher thread did not stop gracefully")
        logger.info("Dispatcher stopped")

    def is_running(self) -> bool:
        """Check if the dispatcher is currently running."""
        return self._running

    def get_status(self) -> Dict:
        """Get dispatcher status information."""
        available_skalds = self._get_available_skalds()
        
        return {
            "running": self._running,
            "interval": self.duration,
            "strategy": self.strategy,
            "thread_alive": self._thread.is_alive() if self._thread else False,
            "available_skalds": len(available_skalds),
            "total_skald_tasks": sum(available_skalds.values()) if available_skalds else 0
        }

    def set_strategy(self, strategy: DispatcherStrategyEnum) -> None:
        """Change the assignment strategy."""
        if isinstance(strategy, DispatcherStrategyEnum):
            self.strategy = strategy
            logger.info(f"Dispatcher strategy changed to: {strategy.value}")
        else:
            valid_strategies = DispatcherStrategyEnum.list()
            logger.error(f"Invalid strategy: {strategy}. Valid options: {valid_strategies}")

    def force_assignment_check(self) -> None:
        """Force an immediate assignment check (for testing/debugging)."""
        if self._event_loop and self._running:
            asyncio.run_coroutine_threadsafe(self._dispatch_tasks(), self._event_loop)
            logger.info("Forced assignment check triggered")
        else:
            logger.warning("Cannot force assignment check - dispatcher not running")