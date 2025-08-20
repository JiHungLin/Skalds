"""
TaskRepository Module

Provides CRUD operations for Task objects using MongoDB.
"""

from datetime import datetime
import pymongo
import pymongo.errors
from typing import Optional
from skalds.model.task import Task
from skalds.utils.logging import logger
from skalds.proxy.mongo import MongoProxy
from skalds.worker.factory import TaskWorkerFactory

class TaskRepository:
    """
    Repository for managing Task objects in MongoDB.
    """

    def __init__(self, mongo_proxy: Optional[MongoProxy] = None) -> None:
        """
        Initialize the TaskRepository.

        Args:
            mongo_proxy (MongoProxy): The MongoProxy instance to use.
        """
        if not mongo_proxy:
            logger.error("MongoProxy is not defined")
            raise ValueError("MongoProxy is not defined")
        self.mongo_proxy = mongo_proxy
        try:
            self.mongo_proxy.db.tasks.create_index("id", unique=True)
        except pymongo.errors.OperationFailure as e:
            logger.error(f"Failed to create index on 'id': {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating index on 'id': {e}")
        logger.info("TaskRepository initialized.")

    def get_task_by_task_id(self, id: str, strict_mode: bool = True) -> Optional[Task]:
        """
        Retrieve a Task by its ID.

        Args:
            id (str): The task ID.

        Returns:
            Task or None: The Task object if found, else None.
        """
        try:
            task = self.mongo_proxy.db.tasks.find_one({"id": id}, max_time_ms=3000)
            if not task:
                logger.info(f"Task with id: {id} not found")
                return None
            logger.info(f"Found task by id: {id}, task: {task}")
            class_name = task.get("className", None)
            attachments = task.get("attachments", None)
            if strict_mode:
                attachments = TaskWorkerFactory.create_attachment_with_class_name_and_dict(
                    class_name,
                    attachments
                )
                task["attachments"] = attachments
                return Task.model_validate(task)
            else:
                task["attachments"] = None
                return_data = Task.model_validate(task)
                return_data.attachments = attachments
                return return_data
        except pymongo.errors.ExecutionTimeout as e:
            logger.error(f"MongoDB execution timeout: {e}")
            raise TimeoutError(f"Timeout getting task by id: {id}")
        except pymongo.errors.ServerSelectionTimeoutError as e:
            logger.error(f"MongoDB server selection timeout: {e}")
            raise TimeoutError(f"Timeout getting task by id: {id}")
        except Exception as e:
            logger.error(f"Error getting task by id: {id}, error: {e}")
            raise

    def update_executor(self, id: str, executor: str) -> Optional[Task]:
        """
        Update the executor field of a Task.

        Args:
            id (str): The task ID.
            executor (str): The new executor value.

        Returns:
            Task or None: The updated Task object if modified, else None.
        """
        try:
            result = self.mongo_proxy.db.tasks.update_one(
                {"id": id},
                {"$set": {"executor": executor, "updateDateTime": int(datetime.now().timestamp() * 1000)}}
            )
            if result.modified_count > 0:
                logger.info(f"Task with id: {id} updated executor to {executor}")
                return self.get_task_by_task_id(id)
            else:
                logger.warning(f"No task found with id: {id} or executor already set to {executor}")
                return None
        except pymongo.errors.ExecutionTimeout as e:
            logger.error(f"MongoDB execution timeout: {e}")
            raise TimeoutError(f"Timeout updating executor for task id: {id}")
        except pymongo.errors.ServerSelectionTimeoutError as e:
            logger.error(f"MongoDB server selection timeout: {e}")
            raise TimeoutError(f"Timeout updating executor for task id: {id}")
        except Exception as e:
            logger.error(f"Error updating executor for task id: {id}, error: {e}")
            raise

    def create_task(self, task: Task) -> Task:
        """
        Create a new Task in the database.

        Args:
            task (Task): The Task object to create.

        Returns:
            Task: The created Task object.
        """
        try:
            result = self.mongo_proxy.db.tasks.insert_one(task.model_dump(by_alias=True), bypass_document_validation=False)
            if result.acknowledged:
                logger.info(f"Task created with id: {task.id}")
                return task
            else:
                logger.error(f"Failed to create task with id: {task.id}")
                return task
        except pymongo.errors.ExecutionTimeout as e:
            logger.error(f"MongoDB execution timeout: {e}")
            raise TimeoutError("Timeout creating task")
        except pymongo.errors.ServerSelectionTimeoutError as e:
            logger.error(f"MongoDB server selection timeout: {e}")
            raise TimeoutError("Timeout creating task")
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            raise

# End of file