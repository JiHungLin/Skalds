"""
FastAPI Server Module

Main FastAPI application factory for SystemController.
Includes all endpoints, middleware, and static file serving.
"""

import os
import pkg_resources
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager

# from skald.system_controller.api.endpoints import (
#     tasks_router, skalds_router, events_router, system_router
# )
from skald.system_controller.api.endpoints.events import router as events_router
from skald.system_controller.api.endpoints.skalds import router as skalds_router
from skald.system_controller.api.endpoints.tasks import router as tasks_router
from skald.system_controller.api.endpoints.system import router as system_router
from skald.config.systemconfig import SystemConfig
from skald.utils.logging import logger
from skald.system_controller.main import SystemController


def get_dashboard_static_path() -> str:
    """
    Get the dashboard static files path from the installed package.
    This ensures the path works correctly after pip install.
    """
    try:
        # Try to get the path from the installed package
        return pkg_resources.resource_filename('skald', 'system_controller/static/dashboard')
    except Exception:
        # Fallback to relative path for development
        import skald
        skald_path = os.path.dirname(skald.__file__)
        return os.path.join(skald_path, 'system_controller', 'static', 'dashboard')


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    """
    # Startup
    logger.info("SystemController API starting up...")
    
    # Initialize any required resources here
    # (In a real implementation, this would initialize database connections, etc.)
    
    yield
    
    # Shutdown
    logger.info("SystemController API shutting down...")
    
    # Cleanup resources here


def create_app(
    title: str = "Skald SystemController API",
    description: str = "REST API and Dashboard for Skald distributed task system",
    version: str = "1.0.0",
    enable_dashboard: bool = True
) -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Args:
        title: API title
        description: API description
        version: API version
        enable_dashboard: Whether to serve dashboard static files
    
    Returns:
        Configured FastAPI application
    """
    print(SystemController._instance, "server.py")

    # Create FastAPI app with lifespan manager
    app = FastAPI(
        title=title,
        description=description,
        version=version,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )
    
    # Add middleware
    _add_middleware(app)
    
    # Add routers
    _add_routers(app, enable_dashboard)
    
    # Add dashboard static files if enabled
    if enable_dashboard:
        _add_dashboard_routes(app)
    
    # Add error handlers
    _add_error_handlers(app)
    
    logger.info(f"FastAPI app created: {title} v{version}")
    return app


def _add_middleware(app: FastAPI) -> None:
    """Add middleware to the FastAPI app."""
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify actual origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Gzip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Custom logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        
        # Log request
        logger.debug(f"Request: {request.method} {request.url}")
        
        # Process request
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.debug(f"Response: {response.status_code} ({process_time:.3f}s)")
        
        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


def _add_routers(app: FastAPI, enable_dashboard: bool = True) -> None:
    """Add API routers to the FastAPI app."""
    
    # Include all API routers
    app.include_router(tasks_router)
    print(SystemController._instance, "**********")
    app.include_router(skalds_router)
    app.include_router(events_router)
    app.include_router(system_router)
    
    # Root endpoint - redirect to dashboard if enabled, otherwise show system info
    if enable_dashboard:
        from fastapi.responses import RedirectResponse
        
        @app.get("/")
        async def root():
            """Root endpoint - redirect to dashboard."""
            return RedirectResponse(url="/dashboard", status_code=302)
    else:
        @app.get("/")
        async def root():
            """Root endpoint with basic system information."""
            return {
                "name": "Skald SystemController",
                "version": "1.0.0",
                "mode": SystemConfig.SYSTEM_CONTROLLER_MODE.value,
                "status": "running",
                "endpoints": {
                    "api": "/api",
                    "docs": "/api/docs",
                    "dashboard": "/dashboard" if enable_dashboard else None
                }
            }
    
    # API root endpoint
    @app.get("/api")
    async def api_root():
        """API root endpoint."""
        return {
            "name": "SystemController API",
            "version": "1.0.0",
            "endpoints": {
                "tasks": "/api/tasks",
                "skalds": "/api/skalds",
                "events": "/api/events",
                "system": "/api/system"
            }
        }


def _add_dashboard_routes(app: FastAPI) -> None:
    """Add dashboard static file serving."""
    
    dashboard_path = get_dashboard_static_path()
    
    # Check if dashboard files exist
    if not os.path.exists(dashboard_path):
        logger.warning(f"Dashboard static files not found at: {dashboard_path}")
        
        # Add placeholder dashboard route
        @app.get("/dashboard")
        @app.get("/dashboard/{path:path}")
        async def dashboard_placeholder(path: str = ""):
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Dashboard not available",
                    "message": f"Dashboard static files not found at: {dashboard_path}",
                    "suggestion": "Build the dashboard using 'npm run build' in the dashboard directory"
                }
            )
        return
    
    # Mount static files for dashboard
    app.mount(
        "/dashboard/assets",
        StaticFiles(directory=os.path.join(dashboard_path, "assets")),
        name="dashboard-assets"
    )
    
    # Dashboard routes
    @app.get("/dashboard")
    @app.get("/dashboard/{path:path}")
    async def serve_dashboard(path: str = ""):
        """
        Serve the React dashboard SPA.
        All dashboard routes serve the main index.html file.
        """
        index_file = os.path.join(dashboard_path, "index.html")
        
        if os.path.exists(index_file):
            return FileResponse(index_file)
        else:
            raise HTTPException(
                status_code=404,
                detail="Dashboard index.html not found"
            )
    
    logger.info(f"Dashboard static files served from: {dashboard_path}")


def _add_error_handlers(app: FastAPI) -> None:
    """Add custom error handlers."""
    
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: HTTPException):
        """Custom 404 handler."""
        return JSONResponse(
            status_code=404,
            content={
                "error": "Not Found",
                "message": f"The requested resource '{request.url.path}' was not found",
                "suggestion": "Check the API documentation at /api/docs"
            }
        )
    
    @app.exception_handler(500)
    async def internal_error_handler(request: Request, exc: Exception):
        """Custom 500 handler."""
        logger.error(f"Internal server error: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
                "detail": str(exc) if SystemConfig.SKALD_ENV.value == "DEV" else None
            }
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Custom HTTP exception handler."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "path": request.url.path
            }
        )


# Additional utility functions for the server

def get_app_info() -> dict:
    """Get application information."""
    return {
        "name": "Skald SystemController",
        "version": "1.0.0",
        "mode": SystemConfig.SYSTEM_CONTROLLER_MODE.value,
        "host": SystemConfig.SYSTEM_CONTROLLER_HOST,
        "port": SystemConfig.SYSTEM_CONTROLLER_PORT,
        "environment": SystemConfig.SKALD_ENV.value
    }


def validate_dashboard_files() -> bool:
    """Validate that dashboard files exist."""
    dashboard_path = get_dashboard_static_path()
    index_file = os.path.join(dashboard_path, "index.html")
    return os.path.exists(index_file)


# Import time for middleware
import time