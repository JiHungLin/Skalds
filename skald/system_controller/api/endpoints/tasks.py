"""
Tasks API Endpoints

FastAPI endpoints for task management operations.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from skald.system_controller.api.models import (
    TaskResponse, GetTasksRequest, GetTasksResponse,
    UpdateTaskStatusRequest, UpdateTaskAttachmentsRequest,
    ErrorResponse, SuccessResponse, PaginationParams
)
from skald.system_controller.store.task_store import TaskStore
from skald.repository.repository import TaskRepository
from skald.model.task import TaskLifecycleStatus
from skald.proxy.mongo import MongoProxy
from skald.utils.logging import logger
import time

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

# Dependency to get TaskStore instance
def get_task_store() -> TaskStore:
    return TaskStore()

# Dependency to get TaskRepository (would be injected in real implementation)
def get_task_repository() -> TaskRepository:
    # This would be properly injected in the main application
    from skald.system_controller.main import SystemController
    return SystemController._instance.task_repository if SystemController._instance else None


@router.get("/", response_model=GetTasksResponse)
async def get_tasks(
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(20, ge=1, le=100, description="Items per page"),
    lifecycleStatus: Optional[str] = Query(None, description="Filter by lifecycle status (partial match allowed)"),
    className: Optional[str] = Query(None, description="Filter by task type (partial match allowed)"),
    executor: Optional[str] = Query(None, description="Filter by executor"),
    id: Optional[str] = Query(None, description="Filter by Task ID (partial match allowed)"),
    task_repository: TaskRepository = Depends(get_task_repository)
):
    """
    Get paginated list of tasks with optional filters (supports partial match for id, className, lifecycleStatus).
    """
    try:
        if not task_repository:
            raise HTTPException(status_code=503, detail="Task repository not available")
        
        # Build MongoDB query with partial match
        query = {}
        if lifecycleStatus:
            query["lifecycleStatus"] = {"$regex": lifecycleStatus, "$options": "i"}
        if className:
            query["className"] = {"$regex": className, "$options": "i"}
        if executor:
            query["executor"] = executor
        if id:
            query["id"] = {"$regex": id, "$options": "i"}
        
        # Calculate pagination
        skip = (page - 1) * pageSize
        
        # Get tasks from MongoDB
        collection = task_repository.mongo_proxy.db.tasks
        
        # Get total count
        total = collection.count_documents(query)

        # Get paginated results
        cursor = collection.find(query).skip(skip).limit(pageSize).sort("createDateTime", -1)
        tasks = []
        
        for doc in cursor:
            task_response = TaskResponse(
                id=doc["id"],
                className=doc.get("className", ""),
                lifecycleStatus=doc.get("lifecycleStatus", TaskLifecycleStatus.CREATED.value),
                executor=doc.get("executor"),
                createDateTime=doc.get("createDateTime", 0),
                updateDateTime=doc.get("updateDateTime", 0),
                attachments=doc.get("attachments", {}),
                priority=doc.get("priority", 0),
                heartbeat=0,
                error=None,
                exception=None
            )
            
            # Try to get real-time data from TaskStore
            task_store = get_task_store()
            task_record = task_store.get_task_record(doc["id"])
            if task_record:
                task_response.heartbeat = task_record.get_latest_heartbeat()
                task_response.error = task_record.error_message
                task_response.exception = task_record.exception_message
                realtime_status = task_record.get_status()
                if realtime_status != task_response.lifecycleStatus:
                    task_response.lifecycleStatus = realtime_status
            
            tasks.append(task_response)
        
        return GetTasksResponse(
            items=tasks,
            total=total,
            page=page,
            pageSize=pageSize
        )
        
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/classnames", response_model=List[str])
async def get_task_classnames(
    task_repository: TaskRepository = Depends(get_task_repository)
):
    """
    Get all unique Task class names in the system.
    """
    try:
        if not task_repository:
            raise HTTPException(status_code=503, detail="Task repository not available")
        collection = task_repository.mongo_proxy.db.tasks
        classnames = collection.distinct("className")
        # Remove empty or null class names
        classnames = [c for c in classnames if c]
        return sorted(classnames)
    except Exception as e:
        logger.error(f"Error getting task classnames: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    task_repository: TaskRepository = Depends(get_task_repository)
):
    """
    Get a specific task by ID.
    """
    try:
        if not task_repository:
            raise HTTPException(status_code=503, detail="Task repository not available")
        
        # Get task from MongoDB
        task = task_repository.get_task_by_task_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Convert to response model
        task_response = TaskResponse(
            id=task.id,
            className=task.class_name,
            lifecycleStatus=task.lifecycle_status,
            executor=task.executor,
            createDateTime=task.create_date_time,
            updateDateTime=task.update_date_time,
            attachments=task.attachments.model_dump() if task.attachments else {},
            priority=task.priority,
            heartbeat=0,
            error=None,
            exception=None
        )
        
        # Get real-time data from TaskStore
        task_store = get_task_store()
        task_record = task_store.get_task_record(task_id)
        if task_record:
            task_response.heartbeat = task_record.get_latest_heartbeat()
            task_response.error = task_record.error_message
            task_response.exception = task_record.exception_message
            # Update status from real-time data if more current
            realtime_status = task_record.get_status()
            if realtime_status != task_response.status:
                task_response.status = realtime_status
        
        return task_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{task_id}/status", response_model=SuccessResponse)
async def update_task_status(
    task_id: str,
    request: UpdateTaskStatusRequest,
    task_repository: TaskRepository = Depends(get_task_repository)
):
    """
    Update task status. Only allows changing to Created or Canceled.
    """
    try:
        if not task_repository:
            raise HTTPException(status_code=503, detail="Task repository not available")
        
        # Validate status
        request.validate_status()
        
        # Check if task exists
        task = task_repository.get_task_by_task_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Update task status in MongoDB
        collection = task_repository.mongo_proxy.db.tasks
        result = collection.update_one(  # Remove await
            {"id": task_id},
            {
                "$set": {
                    "lifecycleStatus": request.status,
                    "updateDateTime": int(time.time() * 1000)
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Task status not updated")
        
        logger.info(f"Updated task {task_id} status to {request.status}")
        
        return SuccessResponse(
            message=f"Task status updated to {request.status}",
            data={"taskId": task_id, "status": request.status}
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating task status for {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{task_id}/attachments", response_model=SuccessResponse)
async def update_task_attachments(
    task_id: str,
    request: UpdateTaskAttachmentsRequest,
    task_repository: TaskRepository = Depends(get_task_repository)
):
    """
    Update task attachments.
    """
    try:
        if not task_repository:
            raise HTTPException(status_code=503, detail="Task repository not available")
        
        # Check if task exists
        task = task_repository.get_task_by_task_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Update task attachments in MongoDB
        collection = task_repository.mongo_proxy.db.tasks
        result = collection.update_one(  # Remove await
            {"id": task_id},
            {
                "$set": {
                    "attachments": request.attachments,
                    "updateDateTime": int(time.time() * 1000)
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Task attachments not updated")
        
        logger.info(f"Updated task {task_id} attachments")
        
        return SuccessResponse(
            message="Task attachments updated successfully",
            data={"taskId": task_id, "attachments": request.attachments}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task attachments for {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{task_id}", response_model=SuccessResponse)
async def delete_task(
    task_id: str,
    task_repository: TaskRepository = Depends(get_task_repository)
):
    """
    Delete a task (sets status to Canceled).
    """
    try:
        if not task_repository:
            raise HTTPException(status_code=503, detail="Task repository not available")
        
        # Check if task exists
        task = task_repository.get_task_by_task_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Update task status to Canceled instead of actual deletion
        collection = task_repository.mongo_proxy.db.tasks
        result = collection.update_one(  # Remove await
            {"id": task_id},
            {
                "$set": {
                    "lifecycleStatus": TaskLifecycleStatus.CANCELLED.value,
                    "updateDateTime": int(time.time() * 1000)
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Task not canceled")
        
        logger.info(f"Canceled task {task_id}")
        
        return SuccessResponse(
            message="Task canceled successfully",
            data={"taskId": task_id, "status": TaskLifecycleStatus.CANCELLED.value}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error canceling task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}/heartbeat")
async def get_task_heartbeat(task_id: str):
    """
    Get real-time heartbeat information for a task.
    """
    try:
        task_store = get_task_store()
        task_record = task_store.get_task_record(task_id)
        
        if not task_record:
            raise HTTPException(status_code=404, detail="Task not found in monitoring")
        
        return {
            "taskId": task_id,
            "heartbeat": task_record.get_latest_heartbeat(),
            "status": task_record.get_status(),
            "isAlive": task_record.task_is_alive(),
            "isAssigning": task_record.task_is_assigning(),
            "error": task_record.error_message,
            "exception": task_record.exception_message,
            "lastUpdate": task_record.last_update,
            "heartbeatHistory": task_record.heartbeat_list
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task heartbeat for {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))