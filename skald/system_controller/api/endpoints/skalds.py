"""
Skalds API Endpoints

FastAPI endpoints for Skald management and monitoring.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from skald.system_controller.api.models import (
    SkaldResponse, GetSkaldsResponse,
    ErrorResponse, SuccessResponse
)
from skald.system_controller.store.skald_store import SkaldStore
from skald.utils.logging import logger

router = APIRouter(prefix="/api/skalds", tags=["skalds"])

# Dependency to get SkaldStore instance
def get_skald_store() -> SkaldStore:
    return SkaldStore()


@router.get("/", response_model=GetSkaldsResponse)
async def get_skalds(
    type: Optional[str] = Query(None, description="Filter by Skald type (node/edge)"),
    status: Optional[str] = Query(None, description="Filter by status (online/offline)"),
    skald_store: SkaldStore = Depends(get_skald_store)
):
    """
    Get list of all Skalds with optional filters.
    """
    try:
        all_skalds = skald_store.get_all_skalds()
        
        # Apply filters
        filtered_skalds = []
        for skald_id, skald_data in all_skalds.items():
            # Type filter
            if type and skald_data.mode != type:
                continue
            
            # Status filter
            skald_status = "online" if skald_data.is_online() else "offline"
            if status and skald_status != status:
                continue
            
            # Convert to response format
            skald_response = SkaldResponse(
                id=skald_data.id,
                type=skald_data.mode,
                status=skald_status,
                lastHeartbeat=str(skald_data.update_time),
                supportedTasks=skald_data.supported_tasks,
                currentTasks=[task.id for task in skald_data.all_tasks],
                heartbeat=skald_data.heartbeat,
                taskCount=skald_data.get_task_count()
            )
            
            filtered_skalds.append(skald_response)
        
        # Sort by ID for consistent ordering
        filtered_skalds.sort(key=lambda x: x.id)
        
        return GetSkaldsResponse(
            items=filtered_skalds,
            total=len(filtered_skalds)
        )
        
    except Exception as e:
        logger.error(f"Error getting Skalds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{skald_id}", response_model=SkaldResponse)
async def get_skald(
    skald_id: str,
    skald_store: SkaldStore = Depends(get_skald_store)
):
    """
    Get a specific Skald by ID.
    """
    try:
        skald_data = skald_store.get_skald(skald_id)
        
        if not skald_data:
            raise HTTPException(status_code=404, detail="Skald not found")
        
        skald_status = "online" if skald_data.is_online() else "offline"
        
        return SkaldResponse(
            id=skald_data.id,
            type=skald_data.mode,
            status=skald_status,
            lastHeartbeat=str(skald_data.update_time),
            supportedTasks=skald_data.supported_tasks,
            currentTasks=[task.id for task in skald_data.all_tasks],
            heartbeat=skald_data.heartbeat,
            taskCount=skald_data.get_task_count()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Skald {skald_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{skald_id}/tasks")
async def get_skald_tasks(
    skald_id: str,
    skald_store: SkaldStore = Depends(get_skald_store)
):
    """
    Get all tasks assigned to a specific Skald.
    """
    try:
        skald_data = skald_store.get_skald(skald_id)
        
        if not skald_data:
            raise HTTPException(status_code=404, detail="Skald not found")
        
        tasks = []
        for task in skald_data.all_tasks:
            tasks.append({
                "id": task.id,
                "className": task.class_name,
                "assignedAt": skald_data.update_time
            })
        
        return {
            "skaldId": skald_id,
            "tasks": tasks,
            "totalTasks": len(tasks)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tasks for Skald {skald_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{skald_id}/status")
async def get_skald_status(
    skald_id: str,
    skald_store: SkaldStore = Depends(get_skald_store)
):
    """
    Get detailed status information for a Skald.
    """
    try:
        skald_data = skald_store.get_skald(skald_id)
        
        if not skald_data:
            raise HTTPException(status_code=404, detail="Skald not found")
        
        is_online = skald_data.is_online()
        
        return {
            "skaldId": skald_id,
            "status": "online" if is_online else "offline",
            "type": skald_data.mode,
            "heartbeat": skald_data.heartbeat,
            "lastUpdate": skald_data.update_time,
            "taskCount": skald_data.get_task_count(),
            "isOnline": is_online,
            "uptime": None,  # TODO: Calculate uptime
            "details": {
                "canAcceptTasks": skald_data.mode == "node" and is_online,
                "lastHeartbeatAge": abs(int(time.time() * 1000) - skald_data.update_time),
                "tasks": [
                    {
                        "id": task.id,
                        "className": task.class_name
                    } for task in skald_data.all_tasks
                ]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Skald status for {skald_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{skald_id}/heartbeat")
async def get_skald_heartbeat(
    skald_id: str,
    skald_store: SkaldStore = Depends(get_skald_store)
):
    """
    Get real-time heartbeat information for a Skald.
    """
    try:
        skald_data = skald_store.get_skald(skald_id)
        
        if not skald_data:
            raise HTTPException(status_code=404, detail="Skald not found")
        
        import time
        current_time = int(time.time() * 1000)
        heartbeat_age = current_time - skald_data.update_time
        
        return {
            "skaldId": skald_id,
            "heartbeat": skald_data.heartbeat,
            "lastUpdate": skald_data.update_time,
            "heartbeatAge": heartbeat_age,
            "isOnline": skald_data.is_online(),
            "timestamp": current_time
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Skald heartbeat for {skald_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/statistics")
async def get_skalds_summary(
    skald_store: SkaldStore = Depends(get_skald_store)
):
    """
    Get summary statistics for all Skalds.
    """
    try:
        summary = skald_store.get_summary()
        
        # Add additional computed statistics
        all_skalds = skald_store.get_all_skalds()
        online_skalds = skald_store.get_online_skalds()
        node_skalds = skald_store.get_node_skalds()
        
        return {
            "totalSkalds": summary["totalSkalds"],
            "onlineSkalds": summary["onlineSkalds"],
            "offlineSkalds": summary["totalSkalds"] - summary["onlineSkalds"],
            "nodeSkalds": summary["nodeSkalds"],
            "edgeSkalds": summary["edgeSkalds"],
            "availableNodes": len(node_skalds),
            "totalRunningTasks": summary["totalRunningTasks"],
            "averageTasksPerSkald": (
                summary["totalRunningTasks"] / summary["onlineSkalds"] 
                if summary["onlineSkalds"] > 0 else 0
            ),
            "details": {
                "onlineNodes": len([s for s in online_skalds.values() if s.mode == "node"]),
                "onlineEdges": len([s for s in online_skalds.values() if s.mode == "edge"]),
                "busyNodes": len([s for s in node_skalds.values() if s.get_task_count() > 0]),
                "idleNodes": len([s for s in node_skalds.values() if s.get_task_count() == 0])
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting Skalds summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{skald_id}/ping", response_model=SuccessResponse)
async def ping_skald(
    skald_id: str,
    skald_store: SkaldStore = Depends(get_skald_store)
):
    """
    Ping a Skald to check if it's responsive (placeholder for future implementation).
    """
    try:
        skald_data = skald_store.get_skald(skald_id)
        
        if not skald_data:
            raise HTTPException(status_code=404, detail="Skald not found")
        
        # TODO: Implement actual ping mechanism via Redis/Kafka
        is_online = skald_data.is_online()
        
        return SuccessResponse(
            success=is_online,
            message=f"Skald {skald_id} is {'online' if is_online else 'offline'}",
            data={
                "skaldId": skald_id,
                "online": is_online,
                "lastHeartbeat": skald_data.update_time
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pinging Skald {skald_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))