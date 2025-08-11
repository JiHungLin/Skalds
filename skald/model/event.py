from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


class TaskEvent(BaseModel):
    id: Optional[str] = Field(...)
    title: Optional[str] = Field(...)
    initiator: Optional[str] = Field(...)
    recipient: Optional[str] = Field(...)
    create_date_time: int = Field(..., alias="createDateTime")
    update_date_time: int = Field(..., alias="updateDateTime")
    task_ids: list = Field(default_factory=list, alias="taskIds")

    model_config = ConfigDict(
        populate_by_name=True,
    )

class UpdateTaskWorkerEvent(BaseModel):
    id: Optional[str] = None
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