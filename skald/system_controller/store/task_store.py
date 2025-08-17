"""
TaskStore Module

In-memory storage for task heartbeat monitoring and status tracking.
Based on the reference implementation but enhanced for SystemController use.
"""

from typing import Dict, List, Optional
import threading
import time
from skald.utils.logging import logger


class TaskHeartbeatRecord:
    """
    Store Task Heartbeat Record with enhanced functionality.
    
    Tracks heartbeat history to determine task health and status.
    """
    
    def __init__(self, task_id: str, heartbeat: int = 0):
        self.task_id = task_id
        self.heartbeat_list = [heartbeat]
        self.error_message: Optional[str] = None
        self.exception_message: Optional[str] = None
        self.last_update = int(time.time() * 1000)
        self._max_record_length = 5
        self._lock = threading.RLock()
        
        # Add explicit status tracking
        self.current_status: Optional[str] = None  # Explicit status from MongoDB
        self.last_status_update = int(time.time() * 1000)

    def model_dump(self) -> dict:
        """Dump the model data as a dictionary."""
        with self._lock:
            return {
                "task_id": self.task_id,
                "heartbeat_list": self.heartbeat_list,
                "error_message": self.error_message,
                "exception_message": self.exception_message,
                "last_update": self.last_update,
                "current_status": self.current_status
            }

    def append_heartbeat(self, heartbeat: int) -> None:
        """Add a new heartbeat value to the record."""
        with self._lock:
            self.heartbeat_list.append(heartbeat)
            if len(self.heartbeat_list) > self._max_record_length:
                self.heartbeat_list.pop(0)
            self.last_update = int(time.time() * 1000)

    def set_error(self, error_message: str) -> None:
        """Set error message for the task."""
        with self._lock:
            self.error_message = error_message
            self.last_update = int(time.time() * 1000)

    def set_exception(self, exception_message: str) -> None:
        """Set exception message for the task."""
        with self._lock:
            self.exception_message = exception_message
            self.last_update = int(time.time() * 1000)

    def clear_error(self) -> None:
        """Clear error message."""
        with self._lock:
            self.error_message = None

    def clear_exception(self) -> None:
        """Clear exception message."""
        with self._lock:
            self.exception_message = None

    def task_is_assigning(self) -> bool:
        """Check if task is still in assigning phase (not enough heartbeat samples)."""
        with self._lock:
            return len(self.heartbeat_list) < self._max_record_length

    def task_is_alive(self) -> bool:
        """
        Check if task is alive based on heartbeat variation.
        
        Returns:
            bool: True if heartbeat shows variation (task is active)
        """
        with self._lock:
            print(self.task_id, "heartbeat_list:", self.heartbeat_list)
            if len(self.heartbeat_list) <= 2:
                return True  # Not enough data, assume alive
            
            # Check for heartbeat variation
            unique_heartbeats = len(set(self.heartbeat_list))
            return unique_heartbeats > 2

    def get_latest_heartbeat(self) -> int:
        """Get the most recent heartbeat value."""
        with self._lock:
            return self.heartbeat_list[-1] if self.heartbeat_list else 0

    def is_failed_status(self) -> bool:
        """Check if task has failed status (heartbeat -1)."""
        with self._lock:
            return self.get_latest_heartbeat() == -1

    def is_canceled_status(self) -> bool:
        """Check if task has canceled status (heartbeat -2)."""
        with self._lock:
            return self.get_latest_heartbeat() == -2

    def is_completed_status(self) -> bool:
        """Check if task has completed status (heartbeat 200)."""
        with self._lock:
            return self.get_latest_heartbeat() == 200

    def get_status(self) -> str:
        """
        Determine task status based on heartbeat and other indicators.
        
        Returns:
            str: Task status (Running, Failed, Canceled, Completed, Assigning)
        """
        with self._lock:
            latest_heartbeat = self.get_latest_heartbeat()
            
            if latest_heartbeat == -1:
                return "Failed"
            elif latest_heartbeat == -2:
                return "Canceled"
            elif latest_heartbeat == 200:
                return "Completed"
            elif self.task_is_assigning():
                return "Assigning"
            elif self.task_is_alive():
                return "Running"
            else:
                return "Failed"  # No heartbeat variation, consider failed

    def set_status(self, status: str) -> None:
        """Set the current status of the task."""
        with self._lock:
            self.current_status = status

    def to_dict(self) -> Dict:
        """Convert record to dictionary for API responses."""
        with self._lock:
            return {
                "taskId": self.task_id,
                "heartbeat": self.get_latest_heartbeat(),
                "lifecycleStatus": self.get_status(),
                "error": self.error_message,
                "exception": self.exception_message,
                "lastUpdate": self.last_update,
                "heartbeatHistory": self.heartbeat_list.copy(),
                "isAlive": self.task_is_alive(),
                "isAssigning": self.task_is_assigning()
            }


class TaskStore:
    """
    Thread-safe in-memory store for running task heartbeat records.
    
    This store maintains heartbeat information for tasks that are currently
    being monitored (Assigning or Running status).
    """
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not getattr(self, '_initialized', False):
            self.running_task_heartbeat_records: Dict[str, TaskHeartbeatRecord] = {}
            self._store_lock = threading.RLock()
            self._initialized = True
            logger.info("TaskStore initialized")

    def add_task(self, task_id: str, heartbeat: int = 0) -> None:
        """
        Add a task to monitoring if not already present.
        
        Args:
            task_id: Unique identifier for the task
            heartbeat: Initial heartbeat value
        """
        print("storeID: ", id(self))
        with self._store_lock:
            if task_id not in self.running_task_heartbeat_records:
                self.running_task_heartbeat_records[task_id] = TaskHeartbeatRecord(task_id, heartbeat)
                logger.debug(f"Added task to monitoring: {task_id}")

    def update_task_heartbeat(self, task_id: str, heartbeat: int) -> None:
        """Update heartbeat for a monitored task."""
        with self._store_lock:
            if task_id in self.running_task_heartbeat_records:
                self.running_task_heartbeat_records[task_id].append_heartbeat(heartbeat)

    def update_task_status(self, task_id: str, status: str) -> None:
        """Update status for a monitored task."""
        with self._store_lock:
            if task_id in self.running_task_heartbeat_records:
                self.running_task_heartbeat_records[task_id].set_status(status)

    def set_task_error(self, task_id: str, error_message: str) -> None:
        """Set error message for a task."""
        with self._store_lock:
            if task_id in self.running_task_heartbeat_records:
                self.running_task_heartbeat_records[task_id].set_error(error_message)

    def set_task_exception(self, task_id: str, exception_message: str) -> None:
        """Set exception message for a task."""
        with self._store_lock:
            if task_id in self.running_task_heartbeat_records:
                self.running_task_heartbeat_records[task_id].set_exception(exception_message)

    def clear_task_error(self, task_id: str) -> None:
        """Clear error message for a task."""
        with self._store_lock:
            if task_id in self.running_task_heartbeat_records:
                self.running_task_heartbeat_records[task_id].clear_error()

    def clear_task_exception(self, task_id: str) -> None:
        """Clear exception message for a task."""
        with self._store_lock:
            if task_id in self.running_task_heartbeat_records:
                self.running_task_heartbeat_records[task_id].clear_exception()

    def get_task_record(self, task_id: str) -> Optional[TaskHeartbeatRecord]:
        """Get heartbeat record for a specific task."""
        with self._store_lock:
            return self.running_task_heartbeat_records.get(task_id)

    def get_all_tasks(self) -> Dict[str, TaskHeartbeatRecord]:
        """Get all monitored task records."""
        with self._store_lock:
            return self.running_task_heartbeat_records.copy()

    def get_failed_tasks(self) -> List[str]:
        """Get list of task IDs that have failed."""
        with self._store_lock:
            return [
                task_id for task_id, record in self.running_task_heartbeat_records.items()
                if not record.task_is_alive() or record.is_failed_status()
            ]

    def get_completed_tasks(self) -> List[str]:
        """Get list of task IDs that have completed."""
        with self._store_lock:
            return [
                task_id for task_id, record in self.running_task_heartbeat_records.items()
                if record.is_completed_status()
            ]

    def get_canceled_tasks(self) -> List[str]:
        """Get list of task IDs that have been canceled."""
        with self._store_lock:
            return [
                task_id for task_id, record in self.running_task_heartbeat_records.items()
                if record.is_canceled_status()
            ]

    def get_running_tasks(self) -> List[str]:
        """Get list of task IDs that are currently running."""
        with self._store_lock:
            return [
                task_id for task_id, record in self.running_task_heartbeat_records.items()
                if record.get_status() == "Running"
            ]

    def get_assigning_tasks(self) -> List[str]:
        """Get list of task IDs that are in assigning phase."""
        with self._store_lock:
            return [
                task_id for task_id, record in self.running_task_heartbeat_records.items()
                if record.task_is_assigning()
            ]

    def del_task(self, task_id: str) -> None:
        """Remove a task from monitoring."""
        with self._store_lock:
            if task_id in self.running_task_heartbeat_records:
                del self.running_task_heartbeat_records[task_id]
                logger.debug(f"Removed task from monitoring: {task_id}")

    def clear(self) -> None:
        """Clear all monitored tasks."""
        with self._store_lock:
            self.running_task_heartbeat_records.clear()
            logger.info("TaskStore cleared")

    def get_summary(self) -> Dict:
        """Get summary statistics for dashboard."""
        with self._store_lock:
            total_tasks = len(self.running_task_heartbeat_records)
            running_tasks = len(self.get_running_tasks())
            failed_tasks = len(self.get_failed_tasks())
            completed_tasks = len(self.get_completed_tasks())
            canceled_tasks = len(self.get_canceled_tasks())
            assigning_tasks = len(self.get_assigning_tasks())
            
            return {
                "totalTasks": total_tasks,
                "runningTasks": running_tasks,
                "failedTasks": failed_tasks,
                "completedTasks": completed_tasks,
                "canceledTasks": canceled_tasks,
                "assigningTasks": assigning_tasks
            }

    def to_api_format(self) -> List[Dict]:
        """Convert all task records to API response format."""
        with self._store_lock:
            return [record.to_dict() for record in self.running_task_heartbeat_records.values()]

    def cleanup_old_records(self, max_age_ms: int = 3600000) -> None:
        """
        Remove old task records that haven't been updated recently.
        
        Args:
            max_age_ms: Maximum age in milliseconds before cleanup
        """
        current_time = int(time.time() * 1000)
        to_remove = []
        
        with self._store_lock:
            for task_id, record in self.running_task_heartbeat_records.items():
                if (current_time - record.last_update) > max_age_ms:
                    to_remove.append(task_id)
            
            for task_id in to_remove:
                del self.running_task_heartbeat_records[task_id]
                logger.debug(f"Cleaned up old task record: {task_id}")
            
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} old task records")