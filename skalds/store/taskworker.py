"""
TaskWorkerStore Module

Manages the registration and lifecycle of task worker processes.
"""

import os
import multiprocessing as mp
from signal import SIGTERM
from typing import Dict, Any, List
from skalds.utils.logging import logger

class TaskWorkerStore:
    """
    Store and manage task worker process IDs by task ID.
    Provides methods to register, remove, and terminate task workers.
    """
    TaskWorkerUidDic: Dict[str, int] = {}

    @classmethod
    def remove_task(cls, task_id: str) -> None:
        """
        Remove a task worker from the store by task ID.

        Args:
            task_id: The ID of the task to remove.
        """
        if task_id in cls.TaskWorkerUidDic:
            pid = cls.TaskWorkerUidDic.pop(task_id)
            logger.info(f"Removed taskworker: {task_id} (pid: {pid})")
        else:
            logger.warning(f"Tried to remove non-existent taskworker: {task_id}")

    @classmethod
    def all_task_worker_task_id(cls) -> List[Any]:
        """
        Get a list of all registered task worker IDs.

        Returns:
            List of task IDs.
        """
        return list(cls.TaskWorkerUidDic.keys())
    
    

    @classmethod
    def terminate_task_by_task_id(cls, task_id: str) -> None:
        """
        Terminate a task worker process by task ID.

        Args:
            task_id: The ID of the task to terminate.
        """
        pid = cls.TaskWorkerUidDic.get(task_id)
        if not pid:
            logger.error(f"TaskWorkerStore: {task_id} not found.")
            return
        try:
            os.kill(pid, SIGTERM)
            os.waitpid(pid, 0)
            logger.info(f"Terminated taskworker: {task_id} (pid: {pid})")
        except Exception as e:
            logger.warning(f"TaskWorkerStore: {pid}<{task_id}> not found in OS. Removing from store. Exception: {e}")
        finally:
            removed = cls.TaskWorkerUidDic.pop(task_id, None)
            if removed is not None:
                logger.info(f"Removed taskworker: {task_id} (pid: {removed})")
            else:
                logger.warning(f"Taskworker {task_id} was not in store during cleanup.")

    @classmethod
    def terminate_all_task(cls) -> None:
        """
        Terminate all registered task worker processes and clear the store.
        """
        logger.info("Terminating all taskworkers...")
        for task_id, pid in list(cls.TaskWorkerUidDic.items()):
            logger.info(f"Terminating taskworker: {task_id} (pid: {pid})")
            try:
                os.kill(pid, SIGTERM)
                os.waitpid(pid, 0)
                logger.info(f"Terminated taskworker: {task_id} (pid: {pid})")
            except Exception as e:
                logger.warning(f"TaskWorkerStore: {pid}<{task_id}> not found in OS. Exception: {e}")
        cls.TaskWorkerUidDic.clear()
        logger.info("Cleared all taskworkers.")

    @classmethod
    def register_task_and_start(cls, task_id: str, process: mp.Process) -> None:
        """
        Register a new task worker process and start it.

        Args:
            task_id: The ID of the task to register.
            process: The process object (must have .start() and .pid).
        """
        process.start()
        cls.TaskWorkerUidDic[task_id] = process.pid
        logger.info(f"Registered and started taskworker: {task_id} (pid: {process.pid}) [{process}]")


