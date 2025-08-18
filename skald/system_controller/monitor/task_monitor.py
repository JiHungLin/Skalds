"""
TaskMonitor Module

Monitors Redis for task heartbeats, errors, and exceptions.
Also handles task lifecycle management and status updates.
Based on the reference implementation but enhanced for SystemController use.
"""

import asyncio
import time
import threading
from typing import Dict, List, Optional, Set
from skald.proxy.redis import RedisProxy, RedisKey
from skald.proxy.mongo import MongoProxy
from skald.proxy.kafka import KafkaProxy
from skald.system_controller.store.task_store import TaskStore
from skald.model.task import TaskLifecycleStatus
from skald.repository.repository import TaskRepository
from skald.config.systemconfig import SystemConfig
from skald.utils.logging import logger


class TaskMonitor:
    """
    Monitors task heartbeats and manages task lifecycle.
    
    This monitor tracks:
    - Task heartbeats from Redis
    - Task errors and exceptions
    - Task lifecycle status updates
    - Automatic task failure detection
    """
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls, redis_proxy: RedisProxy, mongo_proxy: MongoProxy, kafka_proxy: KafkaProxy, duration: int = 3):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, redis_proxy: RedisProxy, mongo_proxy: MongoProxy, kafka_proxy: KafkaProxy, duration: int = 3):
        if not getattr(self, '_initialized', False):
            self.redis_proxy = redis_proxy
            self.mongo_proxy = mongo_proxy
            self.kafka_proxy = kafka_proxy
            self.duration = duration
            self.task_store = TaskStore()
            self.task_repository = TaskRepository(mongo_proxy)
            
            self._running = False
            self._thread: Optional[threading.Thread] = None
            self._event_loop: Optional[asyncio.AbstractEventLoop] = None
            self._initialized = True
            logger.info(f"TaskMonitor initialized with {duration}s interval")

    async def _initialize_task_sync(self, page_size: int = 100) -> None:
        """
        Initialize task synchronization by fetching all tasks from DB and updating
        their status based on Redis heartbeat values.
        
        Args:
            page_size: Number of tasks to process per batch
        """
        logger.info("Starting task synchronization initialization...")
        
        try:
            total_synced = 0
            page = 0
            
            while True:
                # Fetch tasks with paging
                tasks = await self._get_all_tasks_paged(page, page_size)
                if not tasks:
                    break
                
                logger.debug(f"Processing page {page} with {len(tasks)} tasks")
                
                # Process each task in the current page
                for task in tasks:
                    try:
                        await self._sync_task_status_from_redis(task['id'])
                        total_synced += 1
                    except Exception as e:
                        logger.error(f"Error syncing task {task['id']}: {e}")
                
                page += 1
                
                # Break if we got fewer tasks than page_size (last page)
                if len(tasks) < page_size:
                    break
            
            logger.info(f"Task synchronization completed. Synced {total_synced} tasks")
            
        except Exception as e:
            logger.error(f"Error during task synchronization initialization: {e}")
            raise

    async def _get_all_tasks_paged(self, page: int, page_size: int) -> List[Dict]:
        """
        Get all tasks from MongoDB with paging support.
        
        Args:
            page: Page number (0-based)
            page_size: Number of tasks per page
            
        Returns:
            List of task documents
        """
        try:
            collection = self.mongo_proxy.db.tasks
            skip = page * page_size
            
            cursor = collection.find({}).skip(skip).limit(page_size)
            tasks = []
            
            for doc in cursor:
                tasks.append(doc)
            
            return tasks
            
        except Exception as e:
            logger.error(f"Error fetching tasks page {page}: {e}")
            return []

    async def _sync_task_status_from_redis(self, task_id: str) -> None:
        """
        Sync a single task's status based on its Redis heartbeat value.
        
        Args:
            task_id: The task ID to sync
        """
        try:
            # Get heartbeat from Redis
            heartbeat = self._get_task_heartbeat(task_id)
            
            if heartbeat is None:
                # No heartbeat found, skip this task
                return
            
            # Map heartbeat to status
            new_status = self._map_heartbeat_to_status(heartbeat)
            
            if new_status is None:
                # Heartbeat value doesn't require status update
                return
            
            # Update status in MongoDB
            await self._update_task_status(task_id, new_status)
            logger.debug(f"Synced task {task_id}: heartbeat {heartbeat} → {new_status.value}")
            
        except Exception as e:
            logger.error(f"Error syncing task {task_id} from Redis: {e}")

    def _map_heartbeat_to_status(self, heartbeat: int) -> Optional[TaskLifecycleStatus]:
        """
        Map heartbeat value to corresponding TaskLifecycleStatus.
        
        Args:
            heartbeat: The heartbeat value from Redis
            
        Returns:
            TaskLifecycleStatus if mapping exists, None otherwise
        """
        # Based on HeartBeat enum from skald.handler.survive
        heartbeat_status_map = {
            200: TaskLifecycleStatus.FINISHED,  # SUCCESS
            -1: TaskLifecycleStatus.FAILED,     # FAILED
            -2: TaskLifecycleStatus.CANCELLED   # CANCELED
        }
        
        return heartbeat_status_map.get(heartbeat)

    def _work(self) -> None:
        """Main monitoring loop with async support."""
        # Create new event loop for this thread
        self._event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._event_loop)
        
        try:
            while self._running:
                try:
                    self._event_loop.run_until_complete(self._monitor_tasks())
                    time.sleep(self.duration)
                except Exception as e:
                    logger.error(f"TaskMonitor error: {e}")
                    time.sleep(self.duration)
        finally:
            if self._event_loop:
                self._event_loop.close()

    async def _monitor_tasks(self) -> None:
        """Monitor all task-related Redis keys and update store."""
        try:
            # Get all tasks that should be monitored (Assigning and Running)
            running_tasks = await self._get_all_running_and_assigning_tasks()
            running_task_ids = {task.id for task in running_tasks}
            
            # Add new tasks to monitoring
            for task in running_tasks:
                self.task_store.add_task(task.id, task.lifecycleStatus, 0)

            # Update heartbeats and check for status changes
            await self._update_task_heartbeats(running_task_ids)
            
            # Handle tasks that are no longer in MongoDB but still in store
            await self._cleanup_orphaned_tasks(running_task_ids)
            
            # Process task status changes
            await self._process_task_status_changes()
            
        except Exception as e:
            logger.error(f"Error in _monitor_tasks: {e}")

    async def _get_all_running_and_assigning_tasks(self) -> List:
        """Get all tasks from MongoDB that are in Assigning or Running status."""
        try:
            # This would be implemented in TaskRepository
            # For now, we'll use a placeholder
            collection = self.mongo_proxy.db.tasks
            cursor = collection.find({
                "lifecycleStatus": {
                    "$in": [TaskLifecycleStatus.ASSIGNING.value, TaskLifecycleStatus.RUNNING.value]
                }
            })
            
            tasks = []
            for doc in cursor:  # Use regular for loop instead of async for
                # Convert MongoDB document to Task object
                tasks.append(type('Task', (), {'id': doc['id'], 'lifecycleStatus': doc['lifecycleStatus']})())
            
            return tasks
        except Exception as e:
            logger.error(f"Error getting running tasks: {e}")
            return []

    async def _update_task_heartbeats(self, running_task_ids: Set[str]) -> None:
        """Update heartbeats for all monitored tasks."""
        for task_id in running_task_ids:
            try:
                # Get heartbeat
                heartbeat = self._get_task_heartbeat(task_id)
                if heartbeat is None:
                    heartbeat = 0  # Treat missing heartbeat as 0
                self.task_store.update_task_heartbeat(task_id, heartbeat)
                
                # Get error message
                error = self._get_task_error(task_id)
                if error:
                    self.task_store.set_task_error(task_id, error)
                
                # Get exception message
                exception = self._get_task_exception(task_id)
                if exception:
                    self.task_store.set_task_exception(task_id, exception)
                    
            except Exception as e:
                logger.error(f"Error updating task {task_id}: {e}")

    def _get_task_heartbeat(self, task_id: str) -> Optional[int]:
        """Get heartbeat value for a task."""
        try:
            heartbeat_key = RedisKey.task_heartbeat(task_id)
            heartbeat_str = self.redis_proxy.get_message(heartbeat_key)
            
            if heartbeat_str is not None:
                if isinstance(heartbeat_str, bytes):
                    heartbeat_str = heartbeat_str.decode()
                return int(heartbeat_str)
            return None
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid heartbeat for task {task_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting heartbeat for task {task_id}: {e}")
            return None

    def _get_task_error(self, task_id: str) -> Optional[str]:
        """Get error message for a task."""
        try:
            error_key = RedisKey.task_has_error(task_id)
            error_msg = self.redis_proxy.get_message(error_key)
            
            if error_msg is not None:
                if isinstance(error_msg, bytes):
                    error_msg = error_msg.decode()
                return error_msg
            return None
        except Exception as e:
            logger.error(f"Error getting error message for task {task_id}: {e}")
            return None

    def _get_task_exception(self, task_id: str) -> Optional[str]:
        """Get exception message for a task."""
        try:
            exception_key = RedisKey.task_exception(task_id)
            exception_msg = self.redis_proxy.get_message(exception_key)
            
            if exception_msg is not None:
                if isinstance(exception_msg, bytes):
                    exception_msg = exception_msg.decode()
                return exception_msg
            return None
        except Exception as e:
            logger.error(f"Error getting exception message for task {task_id}: {e}")
            return None

    async def _cleanup_orphaned_tasks(self, running_task_ids: Set[str]) -> None:
        """Handle tasks that are in store but not in MongoDB."""
        stored_tasks = self.task_store.get_all_tasks()
        
        for task_id in list(stored_tasks.keys()):
            if task_id not in running_task_ids:
                # Task is no longer in MongoDB, send cancel event and remove from store
                await self._send_cancel_event(task_id)
                self.task_store.del_task(task_id)
                logger.info(f"Cleaned up orphaned task: {task_id}")

    async def _process_task_status_changes(self) -> None: # TODO: Need To strictly test.
        """Process tasks that need status updates."""
        stored_tasks = self.task_store.get_all_tasks()
        for task_id, record in stored_tasks.items():
            try:
                current_status = record.get_status()
                # Handle different status transitions
                if record.is_completed_status():
                    # Task has completed
                    await self._handle_completed_task(task_id)
                elif record.is_cancelled_status():
                    # Task was cancelled
                    await self._handle_cancelled_task(task_id)
                elif record.is_failed_status() or not record.task_is_alive():
                    # Task has failed
                    await self._handle_failed_task(task_id)
                elif current_status == TaskLifecycleStatus.RUNNING and record.task_is_alive():
                    # Task is running normally
                    await self._update_task_status(task_id, TaskLifecycleStatus.RUNNING)
                elif record.task_is_assigning():
                    # Task is still assigning
                    await self._update_task_status(task_id, TaskLifecycleStatus.ASSIGNING)
                else:
                    await self._update_task_status(task_id, TaskLifecycleStatus.RUNNING)

            except Exception as e:
                logger.error(f"Error processing status for task {task_id}: {e}")

    async def _handle_failed_task(self, task_id: str) -> None:
        """Handle a task that has failed."""
        try:
            await self._send_cancel_event(task_id)
            await self._update_task_status(task_id, TaskLifecycleStatus.FAILED)
            self.task_store.del_task(task_id)
            logger.info(f"Handled failed task: {task_id}")
        except Exception as e:
            logger.error(f"Error handling failed task {task_id}: {e}")

    async def _handle_cancelled_task(self, task_id: str) -> None:
        """Handle a task that was cancelled."""
        try:
            await self._update_task_status(task_id, TaskLifecycleStatus.CANCELLED)
            self.task_store.del_task(task_id)
            logger.info(f"Handled cancelled task: {task_id}")
        except Exception as e:
            logger.error(f"Error handling cancelled task {task_id}: {e}")

    async def _handle_completed_task(self, task_id: str) -> None:
        """Handle a task that completed successfully."""
        try:
            await self._update_task_status(task_id, TaskLifecycleStatus.FINISHED)
            self.task_store.del_task(task_id)
            logger.info(f"Handled completed task: {task_id}")
        except Exception as e:
            logger.error(f"Error handling completed task {task_id}: {e}")

    async def _update_task_status(self, task_id: str, status: TaskLifecycleStatus) -> None:
        """Update task status in MongoDB."""
        try:

            self.task_store.update_task_status(task_id, status)
            
            collection = self.mongo_proxy.db.tasks
            
            # First check if the task exists and if status actually needs updating
            current_task = collection.find_one({"id": task_id})
            if not current_task:
                logger.warning(f"Task not found for status update: {task_id}")
                return
            
            # Check if status is already the same
            if current_task.get("lifecycleStatus") == status.value:
                logger.debug(f"Task {task_id} already has status {status.value}, skipping update")
                return
            
            # Update only if status is different
            result = collection.update_one(
                {"id": task_id},
                {"$set": {"lifecycleStatus": status.value, "updateDateTime": int(time.time() * 1000)}}
            )
            
            if result.modified_count > 0:
                logger.debug(f"Updated task {task_id} status to {status.value}")
            else:
                logger.debug(f"Task {task_id} status update had no effect")
                
        except Exception as e:
            logger.error(f"Error updating task status for {task_id}: {e}")

    async def _send_cancel_event(self, task_id: str) -> None:
        """Send cancel event via Kafka."""
        try:
            # This would use the existing Kafka topic for task cancellation
            from skald.proxy.kafka import KafkaTopic
            
            cancel_message = {
                "taskId": task_id,
                "action": "cancel",
                "timestamp": int(time.time() * 1000)
            }
            
            import json
            self.kafka_proxy.produce(
                KafkaTopic.TASK_CANCEL,
                task_id,
                json.dumps(cancel_message)
            )
            
            logger.debug(f"Sent cancel event for task: {task_id}")
        except Exception as e:
            logger.error(f"Error sending cancel event for task {task_id}: {e}")

    def start(self) -> None:
        """Start the monitoring thread with initialization."""
        if self._running:
            logger.warning("TaskMonitor is already running")
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._work_with_init, daemon=True, name="TaskMonitor")
        self._thread.start()
        logger.info("TaskMonitor started")

    def _work_with_init(self) -> None:
        """Main monitoring loop with initialization and async support."""
        # Create new event loop for this thread
        self._event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._event_loop)
        
        try:
            # Run initialization first
            logger.info("Running task synchronization before starting monitoring...")
            self._event_loop.run_until_complete(self._initialize_task_sync())
            logger.info("Task synchronization completed, starting regular monitoring...")
            
            # Start regular monitoring loop
            while self._running:
                try:
                    self._event_loop.run_until_complete(self._monitor_tasks())
                    time.sleep(self.duration)
                except Exception as e:
                    logger.error(f"TaskMonitor error: {e}")
                    time.sleep(self.duration)
        finally:
            if self._event_loop:
                self._event_loop.close()

    def stop(self) -> None:
        """Stop the monitoring thread."""
        if not self._running:
            logger.warning("TaskMonitor is not running")
            return
            
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
            if self._thread.is_alive():
                logger.warning("TaskMonitor thread did not stop gracefully")
        logger.info("TaskMonitor stopped")

    def is_running(self) -> bool:
        """Check if the monitor is currently running."""
        return self._running

    def get_status(self) -> Dict:
        """Get monitor status information."""
        return {
            "running": self._running,
            "interval": self.duration,
            "thread_alive": self._thread.is_alive() if self._thread else False,
            "monitored_tasks": len(self.task_store.get_all_tasks())
        }

    def cleanup_old_records(self) -> None:
        """Clean up old task records."""
        try:
            self.task_store.cleanup_old_records()
        except Exception as e:
            logger.error(f"Error cleaning up old records: {e}")
