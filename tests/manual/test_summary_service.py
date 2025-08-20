#!/usr/bin/env python3
"""
Test script for the new SummaryService implementation.

This script tests the SummaryService to ensure it correctly combines
TaskStore and MongoDB data for accurate task summaries.
"""

import sys
import os
import asyncio
import time
from typing import Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from skalds.proxy.mongo import MongoProxy, MongoConfig
from skalds.system_controller.store.task_store import TaskStore
from skalds.system_controller.store.skald_store import SkaldStore
from skalds.system_controller.service.summary_service import SummaryService
from skalds.model.task import Task, TaskLifecycleStatus
from skalds.utils.logging import logger


class SummaryServiceTester:
    """Test class for SummaryService functionality."""
    
    def __init__(self):
        self.mongo_proxy = None
        self.task_store = TaskStore()
        self.skald_store = SkaldStore()
        self.summary_service = None
        
    def setup_mongo(self) -> bool:
        """Setup MongoDB connection."""
        try:
            # Use default MongoDB configuration
            mongo_config = MongoConfig(
                host="localhost:27017",
                db_name="skald_test"
            )
            self.mongo_proxy = MongoProxy(mongo_config)
            self.mongo_proxy.init_db_index()
            
            self.summary_service = SummaryService(
                self.mongo_proxy, 
                self.task_store, 
                self.skald_store
            )
            
            logger.info("MongoDB connection established")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup MongoDB: {e}")
            return False
    
    def create_test_tasks(self) -> None:
        """Create test tasks in MongoDB with different statuses."""
        try:
            collection = self.mongo_proxy.db.tasks
            
            # Clear existing test tasks
            collection.delete_many({"id": {"$regex": "^test-task-"}})
            
            current_time = int(time.time() * 1000)
            
            # Create test tasks with different statuses
            test_tasks = [
                {
                    "id": "test-task-001",
                    "className": "TestWorker",
                    "source": "TEST",
                    "lifecycleStatus": TaskLifecycleStatus.CREATED.value,
                    "createDateTime": current_time - 3600000,  # 1 hour ago
                    "updateDateTime": current_time - 3600000,
                    "priority": 5
                },
                {
                    "id": "test-task-002", 
                    "className": "TestWorker",
                    "source": "TEST",
                    "lifecycleStatus": TaskLifecycleStatus.RUNNING.value,
                    "createDateTime": current_time - 1800000,  # 30 min ago
                    "updateDateTime": current_time - 900000,   # 15 min ago
                    "priority": 3
                },
                {
                    "id": "test-task-003",
                    "className": "TestWorker", 
                    "source": "TEST",
                    "lifecycleStatus": TaskLifecycleStatus.FINISHED.value,
                    "createDateTime": current_time - 7200000,  # 2 hours ago
                    "updateDateTime": current_time - 1800000,  # 30 min ago
                    "priority": 7
                },
                {
                    "id": "test-task-004",
                    "className": "TestWorker",
                    "source": "TEST", 
                    "lifecycleStatus": TaskLifecycleStatus.FAILED.value,
                    "createDateTime": current_time - 5400000,  # 1.5 hours ago
                    "updateDateTime": current_time - 3600000,  # 1 hour ago
                    "priority": 2
                },
                {
                    "id": "test-task-005",
                    "className": "TestWorker",
                    "source": "TEST",
                    "lifecycleStatus": TaskLifecycleStatus.CANCELLED.value,
                    "createDateTime": current_time - 10800000, # 3 hours ago
                    "updateDateTime": current_time - 7200000,  # 2 hours ago
                    "priority": 1
                }
            ]
            
            collection.insert_many(test_tasks)
            logger.info(f"Created {len(test_tasks)} test tasks in MongoDB")
            
        except Exception as e:
            logger.error(f"Error creating test tasks: {e}")
            raise
    
    def setup_task_store(self) -> None:
        """Setup TaskStore with some running tasks."""
        try:
            # Add some tasks to the store (simulating currently monitored tasks)
            self.task_store.add_task("test-task-002", 150)  # Running task
            self.task_store.add_task("test-task-006", 75)   # Another running task
            self.task_store.add_task("test-task-007", 0)    # Assigning task
            
            logger.info("TaskStore setup with test data")
            
        except Exception as e:
            logger.error(f"Error setting up TaskStore: {e}")
            raise
    
    def test_mongo_task_counts(self) -> Dict[str, Any]:
        """Test MongoDB task counting."""
        try:
            counts = self.summary_service._get_mongo_task_counts()
            
            print("\n=== MongoDB Task Counts ===")
            for status, count in counts.items():
                print(f"{status}: {count}")
            
            return counts
            
        except Exception as e:
            logger.error(f"Error testing MongoDB counts: {e}")
            return {}
    
    def test_task_summary(self) -> Dict[str, Any]:
        """Test comprehensive task summary."""
        try:
            summary = self.summary_service.get_task_summary()
            
            print("\n=== Task Summary ===")
            for key, value in summary.items():
                print(f"{key}: {value}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error testing task summary: {e}")
            return {}
    
    def test_dashboard_summary(self) -> Dict[str, Any]:
        """Test dashboard summary."""
        try:
            summary = self.summary_service.get_dashboard_summary()
            
            print("\n=== Dashboard Summary ===")
            for key, value in summary.items():
                print(f"{key}: {value}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error testing dashboard summary: {e}")
            return {}
    
    def test_task_distribution(self) -> list:
        """Test task status distribution."""
        try:
            distribution = self.summary_service.get_task_status_distribution()
            
            print("\n=== Task Status Distribution ===")
            for item in distribution:
                print(f"{item['status']}: {item['count']} ({item['percentage']}%)")
            
            return distribution
            
        except Exception as e:
            logger.error(f"Error testing task distribution: {e}")
            return []
    
    def test_recent_activity(self) -> Dict[str, Any]:
        """Test recent activity tracking."""
        try:
            activity = self.summary_service.get_recent_task_activity(24)
            
            print("\n=== Recent Activity (24h) ===")
            for key, value in activity.items():
                print(f"{key}: {value}")
            
            return activity
            
        except Exception as e:
            logger.error(f"Error testing recent activity: {e}")
            return {}
    
    def cleanup_test_data(self) -> None:
        """Clean up test data."""
        try:
            if self.mongo_proxy:
                collection = self.mongo_proxy.db.tasks
                result = collection.delete_many({"id": {"$regex": "^test-task-"}})
                logger.info(f"Cleaned up {result.deleted_count} test tasks")
            
            # Clear task store
            self.task_store.clear()
            logger.info("TaskStore cleared")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def run_all_tests(self) -> bool:
        """Run all tests."""
        try:
            print("Starting SummaryService tests...")
            
            # Setup
            if not self.setup_mongo():
                print("❌ MongoDB setup failed - skipping tests")
                return False
            
            self.create_test_tasks()
            self.setup_task_store()
            
            # Run tests
            print("\n" + "="*50)
            print("RUNNING TESTS")
            print("="*50)
            
            mongo_counts = self.test_mongo_task_counts()
            task_summary = self.test_task_summary()
            dashboard_summary = self.test_dashboard_summary()
            distribution = self.test_task_distribution()
            activity = self.test_recent_activity()
            
            # Validate results
            print("\n" + "="*50)
            print("VALIDATION")
            print("="*50)
            
            success = True
            
            # Check if we have the expected counts
            if mongo_counts.get("total", 0) < 5:
                print("❌ Expected at least 5 tasks in MongoDB")
                success = False
            else:
                print("✅ MongoDB task counts look correct")
            
            if task_summary.get("failedTasks", 0) == 0:
                print("❌ Expected failed tasks in summary")
                success = False
            else:
                print("✅ Task summary includes failed tasks")
            
            if task_summary.get("finishedTasks", 0) == 0:
                print("❌ Expected finished tasks in summary")
                success = False
            else:
                print("✅ Task summary includes finished tasks")
            
            if len(distribution) == 0:
                print("❌ Expected task distribution data")
                success = False
            else:
                print("✅ Task distribution data available")
            
            return success
            
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return False
        
        finally:
            self.cleanup_test_data()


def main():
    """Main test function."""
    tester = SummaryServiceTester()
    
    try:
        success = tester.run_all_tests()
        
        if success:
            print("\n🎉 All tests passed!")
            return 0
        else:
            print("\n❌ Some tests failed!")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())