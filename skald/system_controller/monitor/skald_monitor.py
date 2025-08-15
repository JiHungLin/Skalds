"""
SkaldMonitor Module

Monitors Redis for Skald status, heartbeats, and task assignments.
Based on the reference implementation but enhanced for SystemController use.
"""

import time
import threading
from typing import Dict, List, Optional
from skald.proxy.redis import RedisProxy, RedisKey
from skald.system_controller.store.skald_store import SkaldStore
from skald.model.task import TaskWorkerSimpleMap
from skald.config.systemconfig import SystemConfig
from skald.utils.logging import logger


class SkaldMonitor:
    """
    Monitors Skald status and updates the SkaldStore.
    
    This monitor tracks:
    - Skald registration and deregistration
    - Skald heartbeats and online status
    - Skald task assignments
    - Skald modes (node/edge)
    """
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls, redis_proxy: RedisProxy, duration: int = 5):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, redis_proxy: RedisProxy, duration: int = 5):
        if not getattr(self, '_initialized', False):
            self.redis_proxy = redis_proxy
            self.duration = duration
            self.skald_store = SkaldStore()
            self._running = False
            self._thread: Optional[threading.Thread] = None
            self._initialized = True
            logger.info(f"SkaldMonitor initialized with {duration}s interval")

    def _work(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                self._monitor_skalds()
                time.sleep(self.duration)
            except Exception as e:
                logger.error(f"SkaldMonitor error: {e}")
                time.sleep(self.duration)

    def _monitor_skalds(self) -> None:
        """Monitor all Skald-related Redis keys and update store."""
        try:
            # Get all registered Skalds with their update times
            new_all_skald = self._get_all_skald_hash_with_update_time()
            
            # Update or add Skalds in store
            for skald_id, update_time in new_all_skald.items():
                if not skald_id:
                    continue
                    
                try:
                    # Get Skald mode
                    mode = self._get_skald_mode(skald_id)
                    
                    # Add or update Skald in store
                    self.skald_store.add_skald(skald_id, int(update_time), mode)
                    
                except Exception as e:
                    logger.error(f"Error updating Skald {skald_id}: {e}")

            # Remove Skalds that are no longer registered
            self._cleanup_unregistered_skalds(new_all_skald)
            
            # Remove timed-out Skalds
            self._cleanup_timeout_skalds(new_all_skald)
            
            # Update heartbeats and task assignments for active Skalds
            self._update_skald_details(new_all_skald)
            
        except Exception as e:
            logger.error(f"Error in _monitor_skalds: {e}")

    def _get_all_skald_hash_with_update_time(self) -> Dict[str, str]:
        """Get all Skald IDs with their update times from Redis."""
        try:
            return self.redis_proxy.get_all_hash(RedisKey.SKALD_LIST_HASH)
        except Exception as e:
            logger.error(f"Error getting Skald hash: {e}")
            return {}

    def _get_skald_mode(self, skald_id: str) -> str:
        """Get Skald mode (node/edge) from Redis."""
        try:
            mode_hash = self.redis_proxy.get_all_hash(RedisKey.SKALD_MODE_LIST_HASH)
            return mode_hash.get(skald_id, "node")  # Default to node
        except Exception as e:
            logger.error(f"Error getting Skald mode for {skald_id}: {e}")
            return "node"

    def _cleanup_unregistered_skalds(self, current_skalds: Dict[str, str]) -> None:
        """Remove Skalds from store that are no longer registered in Redis."""
        stored_skalds = self.skald_store.get_all_skalds()
        
        for skald_id in stored_skalds:
            if skald_id not in current_skalds:
                # Clean up Redis keys for this Skald
                self._cleanup_skald_redis_keys(skald_id)
                # Remove from store
                self.skald_store.del_skald(skald_id)
                logger.info(f"Removed unregistered Skald: {skald_id}")

    def _cleanup_timeout_skalds(self, current_skalds: Dict[str, str]) -> None:
        """Remove Skalds that have timed out."""
        current_time = int(time.time() * 1000)
        timeout_threshold = 10000  # 10 seconds
        
        timeout_skalds = []
        for skald_id, update_time_str in current_skalds.items():
            try:
                update_time = int(update_time_str)
                if (current_time - update_time) > timeout_threshold:
                    timeout_skalds.append(skald_id)
            except (ValueError, TypeError):
                logger.warning(f"Invalid update time for Skald {skald_id}: {update_time_str}")
                timeout_skalds.append(skald_id)

        for skald_id in timeout_skalds:
            # Clean up Redis keys
            self._cleanup_skald_redis_keys(skald_id)
            # Remove from Redis hash
            self.redis_proxy.delete_hash(RedisKey.SKALD_LIST_HASH, skald_id)
            # Remove from store
            self.skald_store.del_skald(skald_id)
            # Remove from current_skalds to prevent further processing
            current_skalds.pop(skald_id, None)
            logger.info(f"Removed timed-out Skald: {skald_id}")

    def _cleanup_skald_redis_keys(self, skald_id: str) -> None:
        """Clean up all Redis keys associated with a Skald."""
        try:
            # Get all keys matching the pattern
            pattern = f"skald:{skald_id}:*"
            keys = self.redis_proxy.get_sub_keys(f"skald:{skald_id}:")
            
            # Delete each key
            for key in keys:
                self.redis_proxy.delete_key(key)
                
            logger.debug(f"Cleaned up Redis keys for Skald: {skald_id}")
        except Exception as e:
            logger.error(f"Error cleaning up Redis keys for Skald {skald_id}: {e}")

    def _update_skald_details(self, active_skalds: Dict[str, str]) -> None:
        """Update heartbeats and task assignments for active Skalds."""
        for skald_id in active_skalds:
            try:
                # Update heartbeat
                heartbeat = self._get_skald_heartbeat(skald_id)
                if heartbeat is not None:
                    self.skald_store.update_skald_heartbeat(skald_id, heartbeat)

                # Update task assignments
                all_tasks = self._get_skald_all_tasks(skald_id)
                if all_tasks is not None:
                    self.skald_store.update_skald_tasks(skald_id, all_tasks)

                # Update supported tasks
                supported_tasks = self._get_skald_supported_tasks(skald_id)
                if supported_tasks is not None:
                    self.skald_store.update_skald_supported_tasks(skald_id, supported_tasks)
                    
            except Exception as e:
                logger.error(f"Error updating details for Skald {skald_id}: {e}")

    def _get_skald_heartbeat(self, skald_id: str) -> Optional[int]:
        """Get heartbeat value for a Skald."""
        try:
            heartbeat_key = RedisKey.skald_heartbeat(skald_id)
            heartbeat_str = self.redis_proxy.get_message(heartbeat_key)
            
            if heartbeat_str is not None:
                if isinstance(heartbeat_str, bytes):
                    heartbeat_str = heartbeat_str.decode()
                return int(heartbeat_str)
            return None
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid heartbeat for Skald {skald_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting heartbeat for Skald {skald_id}: {e}")
            return None

    def _get_skald_all_tasks(self, skald_id: str) -> Optional[List[TaskWorkerSimpleMap]]:
        """Get all tasks assigned to a Skald."""
        try:
            all_task_key = RedisKey.skald_all_task(skald_id)
            task_data = self.redis_proxy.get_message(all_task_key)
            
            if task_data is not None:
                if isinstance(task_data, bytes):
                    task_data = task_data.decode()
                
                # Parse task data (assuming JSON format)
                import json
                task_list_data = json.loads(task_data)
                # Convert to TaskWorkerSimpleMap objects
                tasks = []
                if isinstance(task_list_data, dict) and 'tasks' in task_list_data:
                    for task_info in task_list_data['tasks']:
                        if isinstance(task_info, dict) and 'id' in task_info and 'class_name' in task_info:
                            tasks.append(TaskWorkerSimpleMap(
                                id=task_info['id'],
                                className=task_info['class_name']
                            ))
                
                return tasks
            return []
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Invalid task data for Skald {skald_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting tasks for Skald {skald_id}: {e}")
            return []

    def _get_skald_supported_tasks(self, skald_id: str) -> Optional[List[str]]:
        """Get supported task class names for a Skald."""
        try:
            supported_tasks_key = RedisKey.skald_allow_task_class_name(skald_id)
            supported_tasks = self.redis_proxy.get_list(supported_tasks_key)
            
            if supported_tasks is not None:
                return supported_tasks
            return []
        except Exception as e:
            logger.error(f"Error getting supported tasks for Skald {skald_id}: {e}")
            return []

    def start(self) -> None:
        """Start the monitoring thread."""
        if self._running:
            logger.warning("SkaldMonitor is already running")
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._work, daemon=True, name="SkaldMonitor")
        self._thread.start()
        logger.info("SkaldMonitor started")

    def stop(self) -> None:
        """Stop the monitoring thread."""
        if not self._running:
            logger.warning("SkaldMonitor is not running")
            return
            
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
            if self._thread.is_alive():
                logger.warning("SkaldMonitor thread did not stop gracefully")
        logger.info("SkaldMonitor stopped")

    def is_running(self) -> bool:
        """Check if the monitor is currently running."""
        return self._running

    def get_status(self) -> Dict:
        """Get monitor status information."""
        return {
            "running": self._running,
            "interval": self.duration,
            "thread_alive": self._thread.is_alive() if self._thread else False,
            "monitored_skalds": len(self.skald_store.get_all_skalds())
        }