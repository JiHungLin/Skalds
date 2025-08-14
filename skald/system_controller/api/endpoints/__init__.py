"""
API Endpoints Module

FastAPI endpoint implementations for SystemController.
"""

from .tasks import router as tasks_router
from .skalds import router as skalds_router
from .events import router as events_router
from .system import router as system_router

__all__ = ["tasks_router", "skalds_router", "events_router", "system_router"]