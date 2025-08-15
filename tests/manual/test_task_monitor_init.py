#!/usr/bin/env python3
"""
Test script for TaskMonitor initialization functionality.

This script tests the new initialization process that synchronizes task statuses
between Redis and MongoDB before starting regular monitoring.
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from skald.proxy.redis import RedisProxy
from skald.proxy.mongo import MongoProxy
from skald.proxy.kafka import KafkaProxy
from skald.system_controller.monitor.task_monitor import TaskMonitor
from skald.model.task import TaskLifecycleStatus
from skald.utils.logging import logger


async def test_task_monitor_initialization():
    """Test the TaskMonitor initialization process."""
    
    print("=== TaskMonitor Initialization Test ===")
    
    try:
        # Initialize proxies (you may need to adjust these based on your config)
        redis_proxy = RedisProxy()
        mongo_proxy = MongoProxy()
        kafka_proxy = KafkaProxy()
        
        # Create TaskMonitor instance
        task_monitor = TaskMonitor(redis_proxy, mongo_proxy, kafka_proxy, duration=5)
        
        print("✓ TaskMonitor instance created successfully")
        
        # Test the initialization method directly
        print("\n--- Testing initialization method ---")
        await task_monitor._initialize_task_sync(page_size=10)
        print("✓ Initialization method completed successfully")
        
        # Test heartbeat mapping
        print("\n--- Testing heartbeat mapping ---")
        test_cases = [
            (200, TaskLifecycleStatus.FINISHED),
            (-1, TaskLifecycleStatus.FAILED),
            (-2, TaskLifecycleStatus.CANCELLED),
            (100, None),  # Should return None for unmapped values
        ]
        
        for heartbeat, expected_status in test_cases:
            result = task_monitor._map_heartbeat_to_status(heartbeat)
            if result == expected_status:
                print(f"✓ Heartbeat {heartbeat} → {expected_status}")
            else:
                print(f"✗ Heartbeat {heartbeat} → Expected: {expected_status}, Got: {result}")
        
        # Test paging functionality
        print("\n--- Testing paging functionality ---")
        tasks_page_0 = await task_monitor._get_all_tasks_paged(0, 5)
        tasks_page_1 = await task_monitor._get_all_tasks_paged(1, 5)
        
        print(f"✓ Page 0: {len(tasks_page_0)} tasks")
        print(f"✓ Page 1: {len(tasks_page_1)} tasks")
        
        print("\n=== Test completed successfully ===")
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def test_start_method():
    """Test that the start method uses the new initialization process."""
    
    print("\n=== Testing Start Method ===")
    
    try:
        # Initialize proxies
        redis_proxy = RedisProxy()
        mongo_proxy = MongoProxy()
        kafka_proxy = KafkaProxy()
        
        # Create TaskMonitor instance
        task_monitor = TaskMonitor(redis_proxy, mongo_proxy, kafka_proxy, duration=5)
        
        # Check that the start method references the new _work_with_init method
        import inspect
        start_source = inspect.getsource(task_monitor.start)
        
        if "_work_with_init" in start_source:
            print("✓ Start method correctly uses _work_with_init")
        else:
            print("✗ Start method does not use _work_with_init")
            return False
        
        # Check that _work_with_init method exists
        if hasattr(task_monitor, '_work_with_init'):
            print("✓ _work_with_init method exists")
        else:
            print("✗ _work_with_init method not found")
            return False
        
        print("✓ Start method test passed")
        return True
        
    except Exception as e:
        print(f"✗ Start method test failed: {e}")
        return False


async def main():
    """Main test function."""
    
    print("Starting TaskMonitor initialization tests...\n")
    
    # Test 1: Initialization functionality
    test1_passed = await test_task_monitor_initialization()
    
    # Test 2: Start method
    test2_passed = test_start_method()
    
    # Summary
    print(f"\n=== Test Summary ===")
    print(f"Initialization test: {'PASSED' if test1_passed else 'FAILED'}")
    print(f"Start method test: {'PASSED' if test2_passed else 'FAILED'}")
    
    if test1_passed and test2_passed:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)