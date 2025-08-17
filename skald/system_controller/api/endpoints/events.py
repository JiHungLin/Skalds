"""
Events API Endpoints

FastAPI endpoints for Server-Sent Events (SSE) real-time notifications.
"""

import asyncio
import json
import time
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from skald.system_controller.api.models import SkaldEvent, TaskEvent
from skald.system_controller.store.skald_store import SkaldStore
from skald.system_controller.store.task_store import TaskStore
from skald.utils.logging import logger

router = APIRouter(prefix="/api/events", tags=["events"])

# Dependencies
def get_skald_store() -> SkaldStore:
    return SkaldStore()

def get_task_store() -> TaskStore:
    return TaskStore()


class SSEManager:
    """
    Manages Server-Sent Events for real-time updates.
    """
    
    def __init__(self):
        self._clients = set()
        self._running = False
    
    def add_client(self, client_id: str):
        """Add a client to the SSE stream."""
        self._clients.add(client_id)
        logger.debug(f"Added SSE client: {client_id}")
    
    def remove_client(self, client_id: str):
        """Remove a client from the SSE stream."""
        self._clients.discard(client_id)
        logger.debug(f"Removed SSE client: {client_id}")
    
    def get_client_count(self) -> int:
        """Get the number of connected clients."""
        return len(self._clients)


# Global SSE manager instance
sse_manager = SSEManager()


async def generate_skald_events(
    skald_store: SkaldStore,
    skald_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Generate Server-Sent Events for Skald updates.
    """
    client_id = f"skald_client_{int(time.time() * 1000)}"
    sse_manager.add_client(client_id)
    
    try:
        # Send initial connection event
        yield f"data: {json.dumps({'type': 'connection', 'message': 'Connected to Skald events'})}\n\n"
        
        # Track previous state to detect changes
        previous_state = {}
        
        while True:
            try:
                current_skalds = skald_store.get_all_skalds()
                
                for skald_id_key, skald_data in current_skalds.items():
                    # Filter by specific Skald ID if provided
                    if skald_id and skald_id_key != skald_id:
                        continue
                    
                    current_state = {
                        'status': 'online' if skald_data.is_online() else 'offline',
                        'heartbeat': skald_data.heartbeat,
                        'taskCount': skald_data.get_task_count(),
                        'updateTime': skald_data.update_time
                    }
                    
                    previous_skald_state = previous_state.get(skald_id_key, {})
                    
                    # Check for status changes
                    if current_state.get('status') != previous_skald_state.get('status'):
                        event = SkaldEvent(
                            type="skald_status",
                            skaldId=skald_id_key,
                            data={
                                "status": current_state['status'],
                                "taskCount": current_state['taskCount']
                            },
                            timestamp=int(time.time() * 1000)
                        )
                        yield f"data: {event.model_dump_json()}\n\n"
                    
                    # Check for heartbeat changes
                    if current_state.get('heartbeat') != previous_skald_state.get('heartbeat'):
                        event = SkaldEvent(
                            type="skald_heartbeat",
                            skaldId=skald_id_key,
                            data={
                                "heartbeat": current_state['heartbeat'],
                                "status": current_state['status'],
                                "tasks": [task.id for task in skald_data.all_tasks]
                            },
                            timestamp=int(time.time() * 1000)
                        )
                        yield f"data: {event.model_dump_json()}\n\n"
                    
                    # Update previous state
                    previous_state[skald_id_key] = current_state
                
                # Remove Skalds that no longer exist
                for old_skald_id in list(previous_state.keys()):
                    if old_skald_id not in current_skalds:
                        event = SkaldEvent(
                            type="skald_status",
                            skaldId=old_skald_id,
                            data={"status": "offline", "taskCount": 0},
                            timestamp=int(time.time() * 1000)
                        )
                        yield f"data: {event.model_dump_json()}\n\n"
                        del previous_state[old_skald_id]
                
                # Wait before next check
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error in Skald SSE generation: {e}")
                await asyncio.sleep(5)
                
    except asyncio.CancelledError:
        logger.info(f"Skald SSE client {client_id} disconnected")
    finally:
        sse_manager.remove_client(client_id)


async def generate_task_events(
    task_store: TaskStore,
    task_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Generate Server-Sent Events for Task updates.
    """
    client_id = f"task_client_{int(time.time() * 1000)}"
    sse_manager.add_client(client_id)
    
    try:
        # Send initial connection event
        yield f"data: {json.dumps({'type': 'connection', 'message': 'Connected to Task events'})}\n\n"
        
        # Track previous state to detect changes
        previous_state = {}
        
        while True:
            try:
                print("Checking for task updates...")
                current_tasks = task_store.get_all_tasks()
                print(current_tasks)
                for task_id_key, task_record in current_tasks.items():
                    # Filter by specific Task ID if provided
                    if task_id and task_id_key != task_id:
                        continue
                    
                    current_state = {
                        'heartbeat': task_record.get_latest_heartbeat(),
                        'status': task_record.get_status(),
                        'error': task_record.error_message,
                        'exception': task_record.exception_message,
                        'lastUpdate': task_record.last_update
                    }
                    print(current_state)
                    previous_task_state = previous_state.get(task_id_key, {})
                    
                    # Check for heartbeat changes
                    if current_state.get('heartbeat') != previous_task_state.get('heartbeat'):
                        event = TaskEvent(
                            type="task_heartbeat",
                            taskId=task_id_key,
                            data={
                                "heartbeat": current_state['heartbeat'],
                                "status": current_state['status']
                            },
                            timestamp=int(time.time() * 1000)
                        )
                        yield f"data: {event.model_dump_json()}\n\n"
                    
                    # Check for error changes
                    if (current_state.get('error') != previous_task_state.get('error') and 
                        current_state.get('error') is not None):
                        event = TaskEvent(
                            type="task_error",
                            taskId=task_id_key,
                            data={
                                "error": current_state['error'],
                                "status": current_state['status']
                            },
                            timestamp=int(time.time() * 1000)
                        )
                        yield f"data: {event.model_dump_json()}\n\n"
                    
                    # Check for exception changes
                    if (current_state.get('exception') != previous_task_state.get('exception') and 
                        current_state.get('exception') is not None):
                        event = TaskEvent(
                            type="task_exception",
                            taskId=task_id_key,
                            data={
                                "exception": current_state['exception'],
                                "status": current_state['status']
                            },
                            timestamp=int(time.time() * 1000)
                        )
                        yield f"data: {event.model_dump_json()}\n\n"
                    
                    # Update previous state
                    previous_state[task_id_key] = current_state
                
                # Remove tasks that no longer exist
                for old_task_id in list(previous_state.keys()):
                    if old_task_id not in current_tasks:
                        del previous_state[old_task_id]
                
                # Wait before next check
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in Task SSE generation: {e}")
                await asyncio.sleep(5)
                
    except asyncio.CancelledError:
        logger.info(f"Task SSE client {client_id} disconnected")
    finally:
        sse_manager.remove_client(client_id)


@router.get("/skalds")
async def stream_skald_events(
    skald_id: Optional[str] = Query(None, description="Filter events for specific Skald ID"),
    skald_store: SkaldStore = Depends(get_skald_store)
):
    """
    Stream Server-Sent Events for Skald status and heartbeat updates.
    """
    return StreamingResponse(
        generate_skald_events(skald_store, skald_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


@router.get("/tasks")
async def stream_task_events(
    task_id: Optional[str] = Query(None, description="Filter events for specific Task ID"),
    task_store: TaskStore = Depends(get_task_store)
):
    """
    Stream Server-Sent Events for Task heartbeat, error, and exception updates.
    """
    return StreamingResponse(
        generate_task_events(task_store, task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


@router.get("/status")
async def get_sse_status():
    """
    Get SSE connection status and statistics.
    """
    return {
        "connectedClients": sse_manager.get_client_count(),
        "timestamp": int(time.time() * 1000),
        "status": "active"
    }


@router.get("/test")
async def test_sse():
    """
    Test SSE endpoint that sends periodic test messages.
    """
    async def generate_test_events():
        counter = 0
        while True:
            counter += 1
            test_event = {
                "type": "test",
                "message": f"Test message {counter}",
                "timestamp": int(time.time() * 1000)
            }
            yield f"data: {json.dumps(test_event)}\n\n"
            await asyncio.sleep(5)
    
    return StreamingResponse(
        generate_test_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )