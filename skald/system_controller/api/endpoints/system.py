"""
System API Endpoints

FastAPI endpoints for system status, health checks, and dashboard summary.
"""

import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from skald.system_controller.api.models import (
    DashboardSummary, SystemStatus, ComponentStatus,
    HealthCheckResponse, SuccessResponse
)
from skald.system_controller.store.skald_store import SkaldStore
from skald.system_controller.store.task_store import TaskStore
from skald.system_controller.service.summary_service import SummaryService
from skald.proxy.mongo import MongoProxy
from skald.config.systemconfig import SystemConfig
from skald.utils.logging import logger

router = APIRouter(prefix="/api/system", tags=["system"])
class SystemDependencies:
    mongo_proxy = None

# Dependencies
# These will be set by the application at startup
shared_skald_store: SkaldStore = None
shared_task_store: TaskStore = None

def get_skald_store() -> SkaldStore:
    return shared_skald_store

def get_task_store() -> TaskStore:
    return shared_task_store

def get_mongo_proxy() -> Optional[MongoProxy]:
    """Get MongoDB proxy from SystemController instance."""
    return SystemDependencies.mongo_proxy

def get_summary_service(
    mongo_proxy: Optional[MongoProxy] = Depends(get_mongo_proxy),
    task_store: TaskStore = Depends(get_task_store),
    skald_store: SkaldStore = Depends(get_skald_store)
) -> Optional[SummaryService]:
    """Get summary service instance."""
    if mongo_proxy is None:
        logger.warning("MongoDB proxy not available, summary service will be limited")
        return None
    return SummaryService(mongo_proxy, task_store, skald_store)


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
    summary_service: Optional[SummaryService] = Depends(get_summary_service),
    skald_store: SkaldStore = Depends(get_skald_store),
    task_store: TaskStore = Depends(get_task_store)
):
    """
    Get summary statistics for the dashboard.
    """
    try:
        if summary_service:
            # Use the comprehensive summary service
            summary = summary_service.get_dashboard_summary()
            
            return DashboardSummary(
                totalSkalds=summary["totalSkalds"],
                onlineSkalds=summary["onlineSkalds"],
                totalTasks=summary["totalTasks"],
                runningTasks=summary["runningTasks"],
                finishedTasks=summary["finishedTasks"],
                failedTasks=summary["failedTasks"],
                assigningTasks=summary["assigningTasks"],
                cancelledTasks=summary["cancelledTasks"],
                nodeSkalds=summary["nodeSkalds"],
                edgeSkalds=summary["edgeSkalds"]
            )
        else:
            # Fallback to store-only data when MongoDB is not available
            logger.warning("Using fallback summary (MongoDB not available)")
            skald_summary = skald_store.get_summary()
            task_summary = task_store.get_summary()
            
            return DashboardSummary(
                totalSkalds=skald_summary["totalSkalds"],
                onlineSkalds=skald_summary["onlineSkalds"],
                totalTasks=task_summary["totalTasks"],
                runningTasks=task_summary["runningTasks"],
                finishedTasks=0,  # Cannot get from store
                failedTasks=0,     # Cannot get from store
                assigningTasks=task_summary["assigningTasks"],
                cancelledTasks=0,   # Cannot get from store
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
    summary_service: Optional[SummaryService] = Depends(get_summary_service),
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
        
        # Task metrics - use summary service if available
        if summary_service:
            task_summary = summary_service.get_task_summary()
            task_metrics = {
                "monitored": len(task_store.get_all_tasks()),  # Currently monitored
                "running": task_summary["runningTasks"],
                "failed": task_summary["failedTasks"],
                "finished": task_summary["finishedTasks"],
                "cancelled": task_summary["cancelledTasks"],
                "assigning": task_summary["assigningTasks"],
                "total": task_summary["totalTasks"]
            }
        else:
            # Fallback to store-only data
            all_tasks = task_store.get_all_tasks()
            running_tasks = task_store.get_running_tasks()
            failed_tasks = task_store.get_failed_tasks()
            task_metrics = {
                "monitored": len(all_tasks),
                "running": len(running_tasks),
                "failed": len(failed_tasks),
                "finished": 0,  # Cannot get from store
                "cancelled": 0,   # Cannot get from store
                "assigning": len(task_store.get_assigning_tasks()),
                "total": len(all_tasks)  # Only currently monitored
            }
        
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
                **task_metrics,
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
        
        logger.info("System cleanup finished")
        
        return SuccessResponse(
            message="System cleanup finished successfully",
            data={
                "timestamp": int(time.time() * 1000),
                "operations": ["task_store_cleanup"]
            }
        )
        
    except Exception as e:
        logger.error(f"Error during system cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/task-distribution")
async def get_task_distribution(
    summary_service: Optional[SummaryService] = Depends(get_summary_service)
):
    """
    Get task status distribution for analytics.
    """
    try:
        if not summary_service:
            raise HTTPException(status_code=503, detail="Analytics service not available (MongoDB required)")
        
        distribution = summary_service.get_task_status_distribution()
        return {
            "distribution": distribution,
            "timestamp": int(time.time() * 1000)
        }
        
    except Exception as e:
        logger.error(f"Error getting task distribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/recent-activity")
async def get_recent_activity(
    hours: int = 24,
    summary_service: Optional[SummaryService] = Depends(get_summary_service)
):
    """
    Get recent task activity within specified hours.
    """
    try:
        if not summary_service:
            raise HTTPException(status_code=503, detail="Analytics service not available (MongoDB required)")
        
        if hours < 1 or hours > 168:  # Max 1 week
            raise HTTPException(status_code=400, detail="Hours must be between 1 and 168")
        
        activity = summary_service.get_recent_task_activity(hours)
        return activity
        
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
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