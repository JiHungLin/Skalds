from enum import Enum
from typing import Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, field_validator, ConfigDict

class ModeEnum(str, Enum):
    ACTIVE = "Active"
    PASSIVE = "Passive"

    @classmethod
    def list(cls):
        return [c.value for c in cls]

class TaskLifecycleStatus(str, Enum):
    Created = "Created"
    Assigning = "Assigning"
    Running = "Running"
    Paused = "Paused"
    Finished = "Finished"
    Failed = "Failed"
    Cancelled = "Cancelled"

    @classmethod
    def list(cls):
        return [c.value for c in cls]


class Task(BaseModel):
    id: str
    class_name: str = Field(..., alias="className")
    source: str
    name: Optional[str] = None
    description: Optional[str] = None
    executor: Optional[str] = None
    mode: ModeEnum = ModeEnum.PASSIVE
    create_date_time: datetime = Field(default_factory=lambda: datetime.now(), alias="createDateTime")
    update_date_time: datetime = Field(default_factory=lambda: datetime.now(), alias="updateDateTime")
    deadline_date_time: datetime = Field(default_factory=lambda: datetime.now() + timedelta(days=7), alias="deadlineDateTime")
    lifecycle_status: TaskLifecycleStatus = Field(default=TaskLifecycleStatus.Created, alias="lifecycleStatus")
    priority: int = Field(0, ge=0, le=10, description="Priority from 0 (lowest) to 10 (highest)")
    attachments: Optional[Any] = None # This must use Pydantic's BaseModel base

    model_config = ConfigDict(
        populate_by_name=True,
    )


    @field_validator("attachments", mode="before")
    def validate_attachments(cls, v):
        if v is None:
            return v
        if not isinstance(v, BaseModel):
            raise ValueError("attachments must be a Pydantic BaseModel instance")
        return v

# Inner Support Model
class TaskWorkerSimpleMap(BaseModel):
    id: str = Field(...)
    class_name: str = Field(..., alias="className")
    model_config = ConfigDict(
        populate_by_name=True,
    )


class TaskWorkerSimpleMapList(BaseModel):
    tasks: list[TaskWorkerSimpleMap] = Field(...)
    existed_task_ids: list[str] = Field(..., alias="existedTaskIds")
    timestamp: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000), alias="timestamp")

    model_config = ConfigDict(
        populate_by_name=True,
    )

    def update_timestamp(self):
        self.timestamp = int(datetime.now().timestamp()*1000)


    def push(self, task_id: str, class_name: str):
        if not any(task.id == task_id for task in self.tasks):
            self.tasks.append(TaskWorkerSimpleMap(id=task_id, class_name=class_name))
            self.existed_task_ids.append(task_id)

    def pop_by_task_id(self, task_id: str):
        self.tasks = [task for task in self.tasks if task.id != task_id]
        self.existed_task_ids.remove(task_id)

    def clear(self):
        self.tasks = []
        self.existed_task_ids = []
        self.update_timestamp()

    def keep_specify_tasks(self, task_ids: list[str]):
        self.tasks = [task for task in self.tasks if task.id in task_ids]
        self.existed_task_ids = [task_id for task_id in self.existed_task_ids if task_id in task_ids]
        self.update_timestamp()

    