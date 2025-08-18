#!/usr/bin/env python3
"""
Unit test for SummaryService logic without requiring MongoDB connection.

This test validates the core logic of the SummaryService by mocking
the MongoDB responses and testing the data combination logic.
"""

import sys
import os
from unittest.mock import Mock, MagicMock
from typing import Dict, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from skald.system_controller.service.summary_service import SummaryService
from skald.system_controller.store.task_store import TaskStore
from skald.system_controller.store.skald_store import SkaldStore
from skald.model.task import TaskLifecycleStatus


def test_summary_service_logic():
    """Test the SummaryService logic with mocked dependencies."""
    
    print("Testing SummaryService logic...")
    
    # Create mock MongoDB proxy
    mock_mongo = Mock()
    mock_collection = Mock()
    mock_mongo.db.tasks = mock_collection
    
    # Mock aggregation results
    mock_aggregation_results = [
        {"_id": TaskLifecycleStatus.CREATED.value, "count": 2},
        {"_id": TaskLifecycleStatus.RUNNING.value, "count": 3},
        {"_id": TaskLifecycleStatus.FINISHED.value, "count": 5},
        {"_id": TaskLifecycleStatus.FAILED.value, "count": 2},
        {"_id": TaskLifecycleStatus.CANCELLED.value, "count": 1},
    ]
    mock_collection.aggregate.return_value = mock_aggregation_results
    
    # Create real stores
    task_store = TaskStore()
    skald_store = SkaldStore()
    
    # Add some test data to task store (simulating running tasks)
    task_store.add_task("running-task-1", 150)
    # Simulate heartbeat variation to make it "Running"
    task_store.update_task_heartbeat("running-task-1", 151)
    task_store.update_task_heartbeat("running-task-1", 152)
    task_store.update_task_heartbeat("running-task-1", 153)
    task_store.update_task_heartbeat("running-task-1", 154)
    
    task_store.add_task("running-task-2", 75)
    # Simulate heartbeat variation to make it "Running"
    task_store.update_task_heartbeat("running-task-2", 76)
    task_store.update_task_heartbeat("running-task-2", 77)
    task_store.update_task_heartbeat("running-task-2", 78)
    task_store.update_task_heartbeat("running-task-2", 79)
    
    task_store.add_task("assigning-task-1", 0)  # This will stay in "Assigning"
    
    # Add some test data to skald store
    import time
    current_time = int(time.time() * 1000)
    skald_store.add_skald("test-skald-1", current_time, "node")
    
    # Create summary service
    summary_service = SummaryService(mock_mongo, task_store, skald_store)
    
    # Test MongoDB task counts
    print("\n=== Testing MongoDB Task Counts ===")
    mongo_counts = summary_service._get_mongo_task_counts()
    
    expected_counts = {
        "total": 13,  # Sum of all counts
        "created": 2,
        "assigning": 0,  # Not in mock data
        "running": 3,
        "paused": 0,     # Not in mock data
        "completed": 5,
        "failed": 2,
        "cancelled": 1
    }
    
    print("Expected counts:", expected_counts)
    print("Actual counts:", mongo_counts)
    
    # Validate MongoDB counts
    success = True
    for key, expected_value in expected_counts.items():
        if mongo_counts.get(key, 0) != expected_value:
            print(f"❌ {key}: expected {expected_value}, got {mongo_counts.get(key, 0)}")
            success = False
        else:
            print(f"✅ {key}: {expected_value}")
    
    # Test task summary (combines store + MongoDB)
    print("\n=== Testing Task Summary ===")
    task_summary = summary_service.get_task_summary()
    
    print("Task summary:", task_summary)
    
    # Validate task summary
    if task_summary["totalTasks"] != 13:
        print(f"❌ totalTasks: expected 13, got {task_summary['totalTasks']}")
        success = False
    else:
        print("✅ totalTasks: 13")
    
    if task_summary["runningTasks"] != 2:  # From task store
        print(f"❌ runningTasks: expected 2, got {task_summary['runningTasks']}")
        success = False
    else:
        print("✅ runningTasks: 2")
    
    if task_summary["assigningTasks"] != 1:  # From task store
        print(f"❌ assigningTasks: expected 1, got {task_summary['assigningTasks']}")
        success = False
    else:
        print("✅ assigningTasks: 1")
    
    if task_summary["failedTasks"] != 2:  # From MongoDB
        print(f"❌ failedTasks: expected 2, got {task_summary['failedTasks']}")
        success = False
    else:
        print("✅ failedTasks: 2")
    
    if task_summary["completedTasks"] != 5:  # From MongoDB
        print(f"❌ completedTasks: expected 5, got {task_summary['completedTasks']}")
        success = False
    else:
        print("✅ completedTasks: 5")
    
    # Test dashboard summary
    print("\n=== Testing Dashboard Summary ===")
    dashboard_summary = summary_service.get_dashboard_summary()
    
    print("Dashboard summary keys:", list(dashboard_summary.keys()))
    
    # Validate dashboard summary has all required fields
    required_fields = [
        "totalSkalds", "onlineSkalds", "nodeSkalds", "edgeSkalds",
        "totalTasks", "runningTasks", "assigningTasks", 
        "failedTasks", "completedTasks", "cancelledTasks"
    ]
    
    for field in required_fields:
        if field not in dashboard_summary:
            print(f"❌ Missing field: {field}")
            success = False
        else:
            print(f"✅ Field present: {field} = {dashboard_summary[field]}")
    
    # Test task distribution
    print("\n=== Testing Task Distribution ===")
    distribution = summary_service.get_task_status_distribution()
    
    print(f"Distribution items: {len(distribution)}")
    for item in distribution:
        print(f"  {item['status']}: {item['count']} ({item['percentage']}%)")
    
    if len(distribution) == 0:
        print("❌ No distribution data")
        success = False
    else:
        print("✅ Distribution data available")
    
    # Test recent activity (mock time-based queries)
    print("\n=== Testing Recent Activity ===")
    
    # Mock the time-based queries
    mock_collection.count_documents.return_value = 3
    
    activity = summary_service.get_recent_task_activity(24)
    print("Recent activity:", activity)
    
    if "timeframe" not in activity:
        print("❌ Missing timeframe in activity")
        success = False
    else:
        print("✅ Activity data structure correct")
    
    return success


def test_fallback_behavior():
    """Test behavior when MongoDB is not available."""
    
    print("\n" + "="*50)
    print("Testing Fallback Behavior (No MongoDB)")
    print("="*50)
    
    # Create stores
    task_store = TaskStore()
    skald_store = SkaldStore()
    
    # Add test data
    task_store.add_task("test-1", 100)
    task_store.add_task("test-2", 50)
    
    # Create summary service with None mongo proxy
    summary_service = SummaryService(None, task_store, skald_store)
    
    # Test that it falls back gracefully
    try:
        mongo_counts = summary_service._get_mongo_task_counts()
        print("MongoDB counts (fallback):", mongo_counts)
        
        # Should return all zeros
        if mongo_counts["total"] == 0:
            print("✅ Fallback returns zero counts")
            return True
        else:
            print("❌ Fallback should return zero counts")
            return False
            
    except Exception as e:
        print(f"❌ Fallback failed with exception: {e}")
        return False


def main():
    """Run all tests."""
    print("Starting SummaryService Logic Tests")
    print("="*50)
    
    try:
        # Test main logic
        success1 = test_summary_service_logic()
        
        # Test fallback behavior
        success2 = test_fallback_behavior()
        
        print("\n" + "="*50)
        print("TEST RESULTS")
        print("="*50)
        
        if success1 and success2:
            print("🎉 All logic tests passed!")
            return 0
        else:
            print("❌ Some logic tests failed!")
            return 1
            
    except Exception as e:
        print(f"💥 Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())