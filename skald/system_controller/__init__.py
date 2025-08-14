"""
SystemController Module

Provides centralized control and monitoring for the Skald distributed task system.
Includes FastAPI server, monitoring components, task dispatching, and dashboard.
"""

from .main import SystemController

__all__ = ["SystemController"]