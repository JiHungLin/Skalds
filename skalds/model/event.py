from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime


class TaskEvent(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    initiator: Optional[str] = None
    recipient: Optional[str] = None
    create_date_time: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000), alias="createDateTime")
    update_date_time: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000), alias="updateDateTime")
    task_ids: list = Field(..., alias="taskIds")

    model_config = ConfigDict(
        populate_by_name=True,
    )

class UpdateTaskWorkerEvent(BaseModel):
    attachments: Optional[Any] = None # This must use Pydantic's BaseModel base

    @field_validator("attachments", mode="before")
    def validate_attachments(cls, v):
        if v is None:
            return v
        if not isinstance(v, BaseModel):
            raise ValueError("attachments must be a Pydantic BaseModel instance")
        return v


    model_config = ConfigDict(
        populate_by_name=True,
    )