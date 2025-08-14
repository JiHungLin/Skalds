"""
API Module

FastAPI server components for SystemController HTTP endpoints and SSE events.
Provides REST API for task and Skald management, plus real-time event streaming.
"""

from .server import create_app
from .models import *

__all__ = ["create_app"]