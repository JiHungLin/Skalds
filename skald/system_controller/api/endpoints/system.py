"""
System API Endpoints

FastAPI endpoints for system status, health checks, and dashboard summary.
"""

import time
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from skald.system_controller.api.models import (
    DashboardSummary, SystemStatus, ComponentStatus,
    HealthCheckResponse, SuccessResponse
)
from skald.system_controller.store.skald_store import SkaldStore
from skald.system_controller.store.task_store import TaskStore
from skald.config.systemconfig import SystemConfig
from skald.utils.logging import logger

router = APIRouter(prefix="/api/system", tags=["system"])

# Dependencies
def get_skald_store() -> SkaldStore:
    return SkaldStore()

def get_task_store() -> TaskStore:
    return TaskStore()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint for monitoring system status.
    """
    try:
        # Check basic system components
        services = {}
        
        # Check stores
        try:
            skald_store = get_skald_store()
            services["skald_store"] = "healthy"
        except Exception as e:
            services["skald_store"] = f"unhealthy: {str(e)}"
        
        try:
            task_store = get_task_store()
            services["task_store"] = "healthy"
        except Exception as e:
            services["task_store"] = f"unhealthy: {str(e)}"
        
        # Overall status
        overall_status = "healthy" if all(
            status == "healthy" for status in services.values()
        ) else "degraded"
        
        return HealthCheckResponse(
            status=overall_status,
            timestamp=int(time.time() * 1000),
            services=services
        )
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            timestamp=int(time.time() * 1000),
            services={"error": str(e)}
        )


@router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """
    Get detailed system status including all components.
    """
    try:
        components = []
        
        # Check SystemController components
        # Note: In a real implementation, these would be injected dependencies
        from skald.system_controller.main import SystemController
        system_controller = SystemController._instance if hasattr(SystemController, '_instance') else None
        
        if system_controller:
            # Monitor components
            if hasattr(system_controller, 'skald_monitor') and system_controller.skald_monitor:
                components.append(ComponentStatus(
                    name="SkaldMonitor",
                    running=system_controller.skald_monitor.is_running(),
                    details=system_controller.skald_monitor.get_status()
                ))
            
            if hasattr(system_controller, 'task_monitor') and system_controller.task_monitor:
                components.append(ComponentStatus(
                    name="TaskMonitor",
                    running=system_controller.task_monitor.is_running(),
                    details=system_controller.task_monitor.get_status()
                ))
            
            if hasattr(system_controller, 'dispatcher') and system_controller.dispatcher:
                components.append(ComponentStatus(
                    name="Dispatcher",
                    running=system_controller.dispatcher.is_running(),
                    details=system_controller.dispatcher.get_status()
                ))
        
        # Store components
        skald_store = get_skald_store()
        components.append(ComponentStatus(
            name="SkaldStore",
            running=True,
            details={
                "totalSkalds": len(skald_store.get_all_skalds()),
                "onlineSkalds": len(skald_store.get_online_skalds())
            }
        ))
        
        task_store = get_task_store()
        components.append(ComponentStatus(
            name="TaskStore",
            running=True,
            details={
                "monitoredTasks": len(task_store.get_all_tasks()),
                "runningTasks": len(task_store.get_running_tasks()),
                "failedTasks": len(task_store.get_failed_tasks())
            }
        ))
        
        # Calculate uptime (placeholder)
        uptime = int(time.time()) - int(time.time())  # TODO: Track actual start time
        
        return SystemStatus(
            mode=SystemConfig.SYSTEM_CONTROLLER_MODE.value,
            components=components,
            uptime=uptime,
            version="1.0.0"
        )
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    skald_store: SkaldStore = Depends(get_skald_store),
    task_store: TaskStore = Depends(get_task_store)
):
    """
    Get summary statistics for the dashboard.
    """
    try:
        # Get Skald statistics
        skald_summary = skald_store.get_summary()
        
        # Get Task statistics
        task_summary = task_store.get_summary()
        
        return DashboardSummary(
            totalSkalds=skald_summary["totalSkalds"],
            onlineSkalds=skald_summary["onlineSkalds"],
            totalTasks=task_summary["totalTasks"],
            runningTasks=task_summary["runningTasks"],
            completedTasks=task_summary["completedTasks"],
            failedTasks=task_summary["failedTasks"],
            assigningTasks=task_summary["assigningTasks"],
            canceledTasks=task_summary["canceledTasks"],
            nodeSkalds=skald_summary["nodeSkalds"],
            edgeSkalds=skald_summary["edgeSkalds"]
        )
        
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_system_config():
    """
    Get current system configuration (non-sensitive values only).
    """
    try:
        return {
            "mode": SystemConfig.SYSTEM_CONTROLLER_MODE.value,
            "host": SystemConfig.SYSTEM_CONTROLLER_HOST,
            "port": SystemConfig.SYSTEM_CONTROLLER_PORT,
            "monitoring": {
                "skaldInterval": SystemConfig.MONITOR_SKALD_INTERVAL,
                "taskInterval": SystemConfig.MONITOR_TASK_INTERVAL,
                "heartbeatTimeout": SystemConfig.MONITOR_HEARTBEAT_TIMEOUT
            },
            "dispatcher": {
                "interval": SystemConfig.DISPATCHER_INTERVAL,
                "strategy": SystemConfig.DISPATCHER_STRATEGY.value
            },
            "environment": SystemConfig.SKALD_ENV.value,
            "logLevel": SystemConfig.LOG_LEVEL.value
        }
        
    except Exception as e:
        logger.error(f"Error getting system config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_system_metrics(
    skald_store: SkaldStore = Depends(get_skald_store),
    task_store: TaskStore = Depends(get_task_store)
):
    """
    Get detailed system metrics for monitoring and alerting.
    """
    try:
        current_time = int(time.time() * 1000)
        
        # Skald metrics
        all_skalds = skald_store.get_all_skalds()
        online_skalds = skald_store.get_online_skalds()
        node_skalds = skald_store.get_node_skalds()
        
        # Task metrics
        all_tasks = task_store.get_all_tasks()
        running_tasks = task_store.get_running_tasks()
        failed_tasks = task_store.get_failed_tasks()
        
        # Calculate additional metrics
        total_skald_tasks = sum(skald.get_task_count() for skald in all_skalds.values())
        avg_tasks_per_skald = total_skald_tasks / len(online_skalds) if online_skalds else 0
        
        # Task distribution
        task_distribution = {}
        for skald_id, skald_data in node_skalds.items():
            task_count = skald_data.get_task_count()
            task_distribution[skald_id] = task_count
        
        return {
            "timestamp": current_time,
            "skalds": {
                "total": len(all_skalds),
                "online": len(online_skalds),
                "offline": len(all_skalds) - len(online_skalds),
                "nodes": len([s for s in all_skalds.values() if s.mode == "node"]),
                "edges": len([s for s in all_skalds.values() if s.mode == "edge"]),
                "availableNodes": len(node_skalds),
                "busyNodes": len([s for s in node_skalds.values() if s.get_task_count() > 0]),
                "idleNodes": len([s for s in node_skalds.values() if s.get_task_count() == 0])
            },
            "tasks": {
                "monitored": len(all_tasks),
                "running": len(running_tasks),
                "failed": len(failed_tasks),
                "completed": len(task_store.get_completed_tasks()),
                "canceled": len(task_store.get_canceled_tasks()),
                "assigning": len(task_store.get_assigning_tasks()),
                "totalAssigned": total_skald_tasks
            },
            "performance": {
                "averageTasksPerSkald": round(avg_tasks_per_skald, 2),
                "taskDistribution": task_distribution,
                "systemLoad": {
                    "skaldUtilization": round(len(online_skalds) / max(len(all_skalds), 1) * 100, 2),
                    "nodeUtilization": round(len([s for s in node_skalds.values() if s.get_task_count() > 0]) / max(len(node_skalds), 1) * 100, 2)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup", response_model=SuccessResponse)
async def cleanup_system(
    task_store: TaskStore = Depends(get_task_store)
):
    """
    Perform system cleanup operations.
    """
    try:
        # Cleanup old task records
        task_store.cleanup_old_records()
        
        logger.info("System cleanup completed")
        
        return SuccessResponse(
            message="System cleanup completed successfully",
            data={
                "timestamp": int(time.time() * 1000),
                "operations": ["task_store_cleanup"]
            }
        )
        
    except Exception as e:
        logger.error(f"Error during system cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/version")
async def get_version():
    """
    Get system version information.
    """
    return {
        "version": "1.0.0",
        "buildDate": "2024-01-01",
        "gitCommit": "unknown",
        "pythonVersion": "3.8+",
        "dependencies": {
            "fastapi": "0.100+",
            "pydantic": "2.0+",
            "pymongo": "4.0+",
            "redis": "4.0+",
            "kafka-python": "2.0+"
        }
    }