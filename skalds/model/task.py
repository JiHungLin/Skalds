"""Task model definitions for Skalds.

This module defines the core data models for tasks and task workers,
including enums for task modes and lifecycle statuses, as well as
Pydantic models for task and task worker representations.

Author: Skalds Project Contributors
"""

from enum import Enum
from typing import Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, field_validator, ConfigDict

class ModeEnum(str, Enum):
    """Enumeration for task execution modes."""
    ACTIVE = "Active"
    PASSIVE = "Passive"

    @classmethod
    def list(cls) -> list[str]:
        """Return a list of all mode values."""
        return [c.value for c in cls]

class TaskLifecycleStatus(str, Enum):
    """Enumeration for task lifecycle statuses."""
    CREATED = "Created"
    ASSIGNING = "Assigning"
    RUNNING = "Running"
    PAUSED = "Paused"
    FINISHED = "Finished"
    FAILED = "Failed"
    CANCELLED = "Cancelled"

    @classmethod
    def list(cls) -> list[str]:
        """Return a list of all lifecycle status values."""
        return [c.value for c in cls]

class Task(BaseModel):
    """
    Represents a task in the Skalds system.

    Attributes:
        id: Unique identifier for the task.
        class_name: The class name of the task worker (alias: className).
        source: The source of the task (e.g., YAML, MongoDB).
        name: Optional human-readable name for the task.
        description: Optional description of the task.
        executor: Optional identifier for the executor (e.g., skalds ID).
        dependencies: Optional list of task IDs this task depends on.
        mode: The execution mode of the task (Active/Passive).
        create_date_time: Creation timestamp in milliseconds (alias: createDateTime).
        update_date_time: Last update timestamp in milliseconds (alias: updateDateTime).
        deadline_date_time: Deadline timestamp in milliseconds (alias: deadlineDateTime).
        lifecycle_status: The current lifecycle status (alias: lifecycleStatus).
        priority: Priority from 0 (lowest) to 10 (highest).
        attachments: Optional Pydantic BaseModel instance for task-specific data.
    """
    id: str
    class_name: str = Field(..., alias="className")
    source: str
    name: Optional[str] = None
    description: Optional[str] = None
    executor: Optional[str] = None
    dependencies: Optional[List[str]] = None
    mode: ModeEnum = Field(ModeEnum.PASSIVE.value, description="Task mode, either Active or Passive")
    create_date_time: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000), alias="createDateTime")
    update_date_time: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000), alias="updateDateTime")
    deadline_date_time: int = Field(default_factory=lambda: int((datetime.now() + timedelta(days=7)).timestamp() * 1000), alias="deadlineDateTime")
    lifecycle_status: TaskLifecycleStatus = Field(default=TaskLifecycleStatus.CREATED.value, alias="lifecycleStatus")
    priority: int = Field(0, ge=0, le=10, description="Priority from 0 (lowest) to 10 (highest)")
    attachments: Optional[Any] = None  # Should be a Pydantic BaseModel instance

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True
    )

    @field_validator("attachments", mode="before")
    @classmethod
    def validate_attachments(cls, v: Any) -> Any:
        """Ensure attachments is a Pydantic BaseModel instance or None."""
        if v is None:
            return v
        if not isinstance(v, BaseModel):
            raise ValueError("attachments must be a Pydantic BaseModel instance")
        return v

class TaskWorkerSimpleMap(BaseModel):
    """
    Simple mapping of a task worker for lightweight storage or transfer.

    Attributes:
        id: Unique identifier for the task.
        class_name: The class name of the task worker (alias: className).
    """
    id: str
    class_name: str = Field(..., alias="className")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True
    )

class TaskWorkerSimpleMapList(BaseModel):
    """
    List of simple task worker mappings, with tracking for existing task IDs and a timestamp.

    Attributes:
        tasks: List of TaskWorkerSimpleMap objects.
        existed_task_ids: List of task IDs currently present (alias: existedTaskIds).
        timestamp: Last update timestamp in milliseconds.
    """
    tasks: List[TaskWorkerSimpleMap] = Field(default_factory=list)
    existed_task_ids: List[str] = Field(default_factory=list, alias="existedTaskIds")
    timestamp: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000), alias="timestamp")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True
    )

    def update_timestamp(self) -> None:
        """Update the timestamp to the current time in milliseconds."""
        self.timestamp = int(datetime.now().timestamp() * 1000)

    def push(self, task_id: str, class_name: str) -> None:
        """
        Add a new task worker mapping if not already present.

        Args:
            task_id: The ID of the task.
            class_name: The class name of the task worker.
        """
        if not any(task.id == task_id for task in self.tasks):
            self.tasks.append(TaskWorkerSimpleMap(id=task_id, class_name=class_name))
            self.existed_task_ids.append(task_id)
            self.update_timestamp()

    def pop_by_task_id(self, task_id: str) -> None:
        """
        Remove a task worker mapping by task ID.

        Args:
            task_id: The ID of the task to remove.
        """
        self.tasks = [task for task in self.tasks if task.id != task_id]
        if task_id in self.existed_task_ids:
            self.existed_task_ids.remove(task_id)
        self.update_timestamp()

    def clear(self) -> None:
        """Clear all task worker mappings and reset the timestamp."""
        self.tasks = []
        self.existed_task_ids = []
        self.update_timestamp()

    def keep_specify_tasks(self, task_ids: List[str]) -> None:
        """
        Keep only the specified task IDs in the mapping.

        Args:
            task_ids: List of task IDs to retain.
        """
        self.tasks = [task for task in self.tasks if task.id in task_ids]
        self.existed_task_ids = [task_id for task_id in self.existed_task_ids if task_id in task_ids]
        self.update_timestamp()