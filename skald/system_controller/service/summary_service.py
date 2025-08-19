"""
Summary Service Module

Provides comprehensive task and system summary statistics by combining
in-memory TaskStore data with historical MongoDB data.
"""

from typing import Dict, List, Optional
from skald.proxy.mongo import MongoProxy
from skald.system_controller.store.task_store import TaskStore
from skald.system_controller.store.skald_store import SkaldStore
from skald.model.task import TaskLifecycleStatus
from skald.utils.logging import logger


class SummaryService:
    """
    Service for generating comprehensive system summaries.
    
    Combines real-time data from stores with historical data from MongoDB
    to provide accurate task statistics for the dashboard.
    """
    
    def __init__(self, mongo_proxy: MongoProxy, task_store: TaskStore, skald_store: SkaldStore):
        # Always use the shared instances for stores
        from skald.system_controller.api.endpoints import system as system_endpoints
        self.mongo_proxy = mongo_proxy
        self.task_store = system_endpoints.shared_task_store if system_endpoints.shared_task_store else task_store
        self.skald_store = system_endpoints.shared_skald_store if system_endpoints.shared_skald_store else skald_store
        logger.info("SummaryService initialized")
    
    def get_task_summary(self) -> Dict:
        """
        Get comprehensive task summary combining store and MongoDB data.
        
        Returns:
            Dict: Task summary with accurate counts for all statuses
        """
        try:
            # Get current running/assigning tasks from store
            store_summary = self.task_store.get_summary()
            
            # Get historical task counts from MongoDB
            mongo_counts = self._get_mongo_task_counts()
            
            # Combine the data
            return {
                "totalTasks": mongo_counts["total"],
                "runningTasks": store_summary["runningTasks"],
                "assigningTasks": store_summary["assigningTasks"],
                "failedTasks": mongo_counts["failed"],
                "finishedTasks": mongo_counts["finished"],
                "cancelledTasks": mongo_counts["cancelled"],
                "createdTasks": mongo_counts["created"],
                "pausedTasks": mongo_counts["paused"]
            }
            
        except Exception as e:
            logger.error(f"Error getting task summary: {e}")
            # Fallback to store-only data
            return self.task_store.get_summary()
    
    def get_dashboard_summary(self) -> Dict:
        """
        Get complete dashboard summary including Skald and Task statistics.
        
        Returns:
            Dict: Complete dashboard summary
        """
        try:
            # Get Skald summary
            skald_summary = self.skald_store.get_summary()
            
            # Get comprehensive task summary
            task_summary = self.get_task_summary()
            
            return {
                # Skald statistics
                "totalSkalds": skald_summary["totalSkalds"],
                "onlineSkalds": skald_summary["onlineSkalds"],
                "nodeSkalds": skald_summary["nodeSkalds"],
                "edgeSkalds": skald_summary["edgeSkalds"],
                
                # Task statistics
                "totalTasks": task_summary["totalTasks"],
                "runningTasks": task_summary["runningTasks"],
                "assigningTasks": task_summary["assigningTasks"],
                "failedTasks": task_summary["failedTasks"],
                "finishedTasks": task_summary["finishedTasks"],
                "cancelledTasks": task_summary["cancelledTasks"],
                "createdTasks": task_summary["createdTasks"],
                "pausedTasks": task_summary["pausedTasks"]
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard summary: {e}")
            raise
    
    def _get_mongo_task_counts(self) -> Dict:
        """
        Get task counts from MongoDB for all lifecycle statuses.
        
        Returns:
            Dict: Task counts by status
        """
        try:
            collection = self.mongo_proxy.db.tasks
            
            # Use aggregation pipeline to count by status
            pipeline = [
                {
                    "$group": {
                        "_id": "$lifecycleStatus",
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            results = list(collection.aggregate(pipeline))
            
            # Initialize counts
            counts = {
                "total": 0,
                "created": 0,
                "assigning": 0,
                "running": 0,
                "paused": 0,
                "finished": 0,
                "failed": 0,
                "cancelled": 0
            }
            
            # Map MongoDB results to our counts
            status_mapping = {
                TaskLifecycleStatus.CREATED.value: "created",
                TaskLifecycleStatus.ASSIGNING.value: "assigning",
                TaskLifecycleStatus.RUNNING.value: "running",
                TaskLifecycleStatus.PAUSED.value: "paused",
                TaskLifecycleStatus.FINISHED.value: "finished",
                TaskLifecycleStatus.FAILED.value: "failed",
                TaskLifecycleStatus.CANCELLED.value: "cancelled"
            }
            
            for result in results:
                status = result["_id"]
                count = result["count"]
                counts["total"] += count
                
                if status in status_mapping:
                    counts[status_mapping[status]] = count
                else:
                    logger.warning(f"Unknown task status in MongoDB: {status}")
            
            logger.debug(f"MongoDB task counts: {counts}")
            return counts
            
        except Exception as e:
            logger.error(f"Error getting MongoDB task counts: {e}")
            return {
                "total": 0,
                "created": 0,
                "assigning": 0,
                "running": 0,
                "paused": 0,
                "finished": 0,
                "failed": 0,
                "cancelled": 0
            }
    
    def get_task_status_distribution(self) -> List[Dict]:
        """
        Get detailed task status distribution for analytics.
        
        Returns:
            List[Dict]: List of status distributions with counts and percentages
        """
        try:
            counts = self._get_mongo_task_counts()
            total = counts["total"]
            
            if total == 0:
                return []
            
            distribution = []
            status_labels = {
                "created": "Created",
                "assigning": "Assigning", 
                "running": "Running",
                "paused": "Paused",
                "finished": "Finished",
                "failed": "Failed",
                "cancelled": "Cancelled"
            }
            
            for status_key, label in status_labels.items():
                count = counts[status_key]
                if count > 0:
                    distribution.append({
                        "status": label,
                        "count": count,
                        "percentage": round((count / total) * 100, 2)
                    })
            
            return sorted(distribution, key=lambda x: x["count"], reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting task status distribution: {e}")
            return []
    
    def get_recent_task_activity(self, hours: int = 24) -> Dict:
        """
        Get recent task activity within specified hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dict: Recent activity statistics
        """
        try:
            import time
            cutoff_time = int((time.time() - (hours * 3600)) * 1000)
            
            collection = self.mongo_proxy.db.tasks
            
            # Count tasks created in the time period
            created_count = collection.count_documents({
                "createDateTime": {"$gte": cutoff_time}
            })
            
            # Count tasks updated in the time period
            updated_count = collection.count_documents({
                "updateDateTime": {"$gte": cutoff_time}
            })
            
            # Count finished tasks in the time period
            finished_count = collection.count_documents({
                "lifecycleStatus": TaskLifecycleStatus.FINISHED.value,
                "updateDateTime": {"$gte": cutoff_time}
            })
            
            # Count failed tasks in the time period
            failed_count = collection.count_documents({
                "lifecycleStatus": TaskLifecycleStatus.FAILED.value,
                "updateDateTime": {"$gte": cutoff_time}
            })
            
            return {
                "timeframe": f"Last {hours} hours",
                "tasksCreated": created_count,
                "tasksUpdated": updated_count,
                "tasksFinished": finished_count,
                "tasksFailed": failed_count,
                "successRate": round((finished_count / max(finished_count + failed_count, 1)) * 100, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting recent task activity: {e}")
            return {
                "timeframe": f"Last {hours} hours",
                "tasksCreated": 0,
                "tasksUpdated": 0,
                "tasksFinished": 0,
                "tasksFailed": 0,
                "successRate": 0.0
            }