"""
API Models Module

Pydantic models for FastAPI request/response validation.
Based on the dashboard technical specification.
"""

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict
from skald.model.task import TaskLifecycleStatus


# Task Models
class TaskResponse(BaseModel):
    """Task response model for API endpoints."""
    model_config = ConfigDict(populate_by_name=True)
    
    id: str
    className: str = Field(alias="className")
    lifecycleStatus: str = Field(alias="lifecycleStatus")
    executor: Optional[str] = None
    createDateTime: int = Field(alias="createDateTime")
    updateDateTime: int = Field(alias="updateDateTime")
    attachments: Dict[str, Any] = {}
    heartbeat: int = 0
    error: Optional[str] = None
    exception: Optional[str] = None
    priority: int = 0


class GetTasksRequest(BaseModel):
    """Request model for getting tasks with filters."""
    page: int = Field(1, ge=1, description="Page number (1-based)")
    pageSize: int = Field(20, ge=1, le=100, description="Number of items per page")
    status: Optional[str] = Field(None, description="Filter by task status")
    className: Optional[str] = Field(None, description="Filter by task type/className")
    executor: Optional[str] = Field(None, description="Filter by executor Skald ID")


class GetTasksResponse(BaseModel):
    """Response model for paginated task list."""
    items: List[TaskResponse]
    total: int
    page: int
    pageSize: int


class UpdateTaskStatusRequest(BaseModel):
    """Request model for updating task lifecycleStatus."""
    lifecycle_status: str = Field(..., description="New task lifecycleStatus (Created or Cancelled)", alias="lifecycleStatus")

    def model_post_init(self, __context: Any) -> None:
        """Validate that lifecycleStatus is one of the allowed values."""
        allowed_statuses = [TaskLifecycleStatus.CREATED.value, TaskLifecycleStatus.CANCELLED.value]
        if self.lifecycle_status not in allowed_statuses:
            raise ValueError(f"LifecycleStatus must be one of: {allowed_statuses}")

    model_config = ConfigDict(
        populate_by_name=True,
    )

class UpdateTaskAttachmentsRequest(BaseModel):
    """Request model for updating task attachments."""
    attachments: Dict[str, Any] = Field(..., description="Task attachments data")


# Skald Models
class SkaldResponse(BaseModel):
    """Skald response model for API endpoints."""
    id: str
    type: str = Field(description="Skald type: node or edge")
    status: str = Field(description="Skald status: online or offline")
    lastHeartbeat: str = Field(description="Last heartbeat timestamp")
    supportedTasks: List[str] = Field(default_factory=list, description="Supported task types")
    currentTasks: List[str] = Field(default_factory=list, description="Currently assigned task IDs")
    heartbeat: int = Field(default=0, description="Current heartbeat value")
    taskCount: int = Field(default=0, description="Number of assigned tasks")


class GetSkaldsResponse(BaseModel):
    """Response model for Skald list."""
    items: List[SkaldResponse]
    total: int


# Dashboard Summary Models
class DashboardSummary(BaseModel):
    """Dashboard summary statistics."""
    totalSkalds: int = 0
    onlineSkalds: int = 0
    totalTasks: int = 0
    runningTasks: int = 0
    finishedTasks: int = 0
    failedTasks: int = 0
    assigningTasks: int = 0
    cancelledTasks: int = 0
    nodeSkalds: int = 0
    edgeSkalds: int = 0


# SSE Event Models
class SkaldEvent(BaseModel):
    """SSE event model for Skald updates."""
    type: str = Field(description="Event type: skald_status, skald_heartbeat")
    skaldId: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: int = Field(description="Event timestamp in milliseconds")


class TaskEvent(BaseModel):
    """SSE event model for Task updates."""
    type: str = Field(description="Event type: task_heartbeat, task_error, task_exception")
    taskId: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: int = Field(description="Event timestamp in milliseconds")


# Error Models
class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    code: Optional[str] = Field(None, description="Error code")


class ValidationErrorResponse(BaseModel):
    """Validation error response model."""
    error: str = "Validation Error"
    detail: List[Dict[str, Any]] = Field(description="Validation error details")


# System Status Models
class ComponentStatus(BaseModel):
    """Status of a system component."""
    name: str
    running: bool
    details: Dict[str, Any] = Field(default_factory=dict)


class SystemStatus(BaseModel):
    """Overall system status."""
    mode: str = Field(description="SystemController mode")
    components: List[ComponentStatus] = Field(default_factory=list)
    uptime: int = Field(description="Uptime in seconds")
    version: str = Field(default="1.0.0")


# Health Check Models
class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str = Field(default="healthy")
    timestamp: int = Field(description="Health check timestamp")
    services: Dict[str, str] = Field(default_factory=dict, description="Service health status")


# Pagination Helper
class PaginationParams(BaseModel):
    """Common pagination parameters."""
    page: int = Field(1, ge=1, description="Page number (1-based)")
    pageSize: int = Field(20, ge=1, le=100, description="Number of items per page")

    @property
    def skip(self) -> int:
        """Calculate skip value for database queries."""
        return (self.page - 1) * self.pageSize

    @property
    def limit(self) -> int:
        """Get limit value for database queries."""
        return self.pageSize


# Generic Response Models
class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str = "Operation finished successfully"
    data: Optional[Dict[str, Any]] = None


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str


# Filter Models
class TaskFilter(BaseModel):
    """Task filtering options."""
    status: Optional[List[str]] = None
    type: Optional[List[str]] = None
    executor: Optional[List[str]] = None
    priority_min: Optional[int] = None
    priority_max: Optional[int] = None
    created_after: Optional[str] = None
    created_before: Optional[str] = None


class SkaldFilter(BaseModel):
    """Skald filtering options."""
    type: Optional[List[str]] = None  # node, edge
    status: Optional[List[str]] = None  # online, offline
    has_tasks: Optional[bool] = None