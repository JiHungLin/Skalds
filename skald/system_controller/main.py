"""
SystemController Main Module

Main SystemController class that orchestrates all components based on configuration.
Provides a single entry point for the entire SystemController system.
"""

import asyncio
import threading
import time
from typing import Optional
import uvicorn

from skald.config.systemconfig import SystemConfig
from skald.config._enum import SystemControllerModeEnum
from skald.proxy.redis import RedisProxy, RedisConfig
from skald.proxy.mongo import MongoProxy, MongoConfig
from skald.proxy.kafka import KafkaProxy, KafkaConfig
from skald.repository.repository import TaskRepository

from skald.system_controller.store.skald_store import SkaldStore
from skald.system_controller.store.task_store import TaskStore
from skald.system_controller.monitor.skald_monitor import SkaldMonitor
from skald.system_controller.monitor.task_monitor import TaskMonitor
from skald.system_controller.monitor.dispatcher import Dispatcher
from skald.system_controller.api.server import create_app

from skald.utils.logging import logger


class SystemController:
    """
    Main SystemController class that manages all components.
    
    This class orchestrates the entire SystemController system based on the
    configured mode (controller, monitor, dispatcher).
    """
    
    _instance: Optional['SystemController'] = None
    _lock = threading.RLock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not getattr(self, '_initialized', False):
            self.mode = SystemConfig.SYSTEM_CONTROLLER_MODE
            self.host = SystemConfig.SYSTEM_CONTROLLER_HOST
            self.port = SystemConfig.SYSTEM_CONTROLLER_PORT
            
            # Proxy services
            self.redis_proxy: Optional[RedisProxy] = None
            self.mongo_proxy: Optional[MongoProxy] = None
            self.kafka_proxy: Optional[KafkaProxy] = None
            
            # Repository
            self.task_repository: Optional[TaskRepository] = None
            
            # Store components
            self.skald_store: Optional[SkaldStore] = None
            self.task_store: Optional[TaskStore] = None
            
            # Monitor components
            self.skald_monitor: Optional[SkaldMonitor] = None
            self.task_monitor: Optional[TaskMonitor] = None
            self.dispatcher: Optional[Dispatcher] = None
            
            # FastAPI app
            self.app = None
            self.server_task: Optional[asyncio.Task] = None
            
            # State tracking
            self._running = False
            self._start_time = None
            self._initialized = True
            
            logger.info(f"SystemController initialized in {self.mode} mode")
    
    async def start(self) -> None:
        """
        Start the SystemController with all configured components.
        """
        if self._running:
            logger.warning("SystemController is already running")
            return
        
        self._start_time = time.time()
        logger.info(f"Starting SystemController in {self.mode} mode...")
        
        try:
            # Initialize proxy services
            await self._init_proxy_services()
            
            # Initialize components based on mode
            await self._init_components()
            
            # Start components
            await self._start_components()
            
            # Start FastAPI server
            await self._start_api_server()
            
            self._running = True
            logger.success(f"SystemController started successfully in {self.mode} mode")
            
        except Exception as e:
            logger.error(f"Failed to start SystemController: {e}")
            await self.stop()
            raise
    
    async def stop(self) -> None:
        """
        Stop the SystemController and all components.
        """
        if not self._running:
            logger.warning("SystemController is not running")
            return
        
        logger.info("Stopping SystemController...")
        
        try:
            # Stop FastAPI server
            if self.server_task:
                self.server_task.cancel()
                try:
                    await self.server_task
                except asyncio.CancelledError:
                    pass
            
            # Stop monitor components
            if self.dispatcher:
                self.dispatcher.stop()
            
            if self.task_monitor:
                self.task_monitor.stop()
            
            if self.skald_monitor:
                self.skald_monitor.stop()
            
            # Close proxy connections
            if self.mongo_proxy:
                self.mongo_proxy.close()
            
            self._running = False
            logger.info("SystemController stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping SystemController: {e}")
    
    async def _init_proxy_services(self) -> None:
        """Initialize proxy services (Redis, MongoDB, Kafka)."""
        logger.info("Initializing proxy services...")
        
        # Redis proxy
        if SystemConfig.REDIS_HOST:
            redis_config = RedisConfig(
                host=SystemConfig.REDIS_HOST,
                port=SystemConfig.REDIS_PORT,
                password=SystemConfig.REDIS_PASSWORD
            )
            self.redis_proxy = RedisProxy(redis_config, is_block=True)
            logger.info("Redis proxy initialized")
        else:
            logger.warning("Redis host not configured")
        
        # MongoDB proxy
        if SystemConfig.MONGO_HOST:
            mongo_config = MongoConfig(
                host=SystemConfig.MONGO_HOST,
                db_name=SystemConfig.DB_NAME
            )
            self.mongo_proxy = MongoProxy(mongo_config)
            self.mongo_proxy.init_db_index()
            
            # Initialize task repository
            self.task_repository = TaskRepository(self.mongo_proxy)
            logger.info("MongoDB proxy and TaskRepository initialized")
        else:
            logger.warning("MongoDB host not configured")
        
        # Kafka proxy (needed for dispatcher mode)
        if (self.mode == SystemControllerModeEnum.DISPATCHER and 
            SystemConfig.KAFKA_HOST):
            kafka_config = KafkaConfig(
                host=SystemConfig.KAFKA_HOST,
                port=SystemConfig.KAFKA_PORT,
                username=SystemConfig.KAFKA_USERNAME,
                password=SystemConfig.KAFKA_PASSWORD
            )
            self.kafka_proxy = KafkaProxy(kafka_config, is_block=True)
            logger.info("Kafka proxy initialized")
        elif self.mode == SystemControllerModeEnum.DISPATCHER:
            logger.warning("Kafka host not configured for dispatcher mode")
    
    async def _init_components(self) -> None:
        """Initialize components based on the configured mode."""
        logger.info(f"Initializing components for {self.mode} mode...")
        
        # Always initialize stores
        self.skald_store = SkaldStore()
        self.task_store = TaskStore()
        
        # Initialize monitoring components for monitor and dispatcher modes
        if self.mode in [SystemControllerModeEnum.MONITOR, SystemControllerModeEnum.DISPATCHER]:
            if not self.redis_proxy:
                raise RuntimeError("Redis proxy required for monitoring components")
            
            # Initialize SkaldMonitor
            self.skald_monitor = SkaldMonitor(
                self.redis_proxy,
                SystemConfig.MONITOR_SKALD_INTERVAL
            )
            
            # Initialize TaskMonitor
            if self.mongo_proxy:
                self.task_monitor = TaskMonitor(
                    self.redis_proxy,
                    self.mongo_proxy,
                    self.kafka_proxy,
                    SystemConfig.MONITOR_TASK_INTERVAL
                )
            else:
                logger.warning("TaskMonitor not initialized - MongoDB proxy not available")
        
        # Initialize dispatcher for dispatcher mode
        if self.mode == SystemControllerModeEnum.DISPATCHER:
            if not all([self.redis_proxy, self.mongo_proxy, self.kafka_proxy]):
                logger.warning("Some proxy services not available for dispatcher")
            
            if self.redis_proxy and self.mongo_proxy and self.kafka_proxy:
                self.dispatcher = Dispatcher(
                    self.redis_proxy,
                    self.mongo_proxy,
                    self.kafka_proxy,
                    SystemConfig.DISPATCHER_INTERVAL
                )
        
        # Initialize FastAPI app
        enable_dashboard = self.mode in [
            SystemControllerModeEnum.MONITOR,
            SystemControllerModeEnum.DISPATCHER
        ]
        
        self.app = create_app(
            title=f"Skald SystemController ({self.mode.title()})",
            description=f"SystemController running in {self.mode} mode",
            version="1.0.0",
            enable_dashboard=enable_dashboard
        )
        
        logger.info("Components initialized successfully")
    
    async def _start_components(self) -> None:
        """Start all initialized components."""
        logger.info("Starting components...")
        
        # Start monitoring components
        if self.skald_monitor:
            self.skald_monitor.start()
            logger.info("SkaldMonitor started")
        
        if self.task_monitor:
            self.task_monitor.start()
            logger.info("TaskMonitor started")
        
        if self.dispatcher:
            self.dispatcher.start()
            logger.info("Dispatcher started")
        
        logger.info("All components started successfully")
    
    async def _start_api_server(self) -> None:
        """Start the FastAPI server."""
        if not self.app:
            raise RuntimeError("FastAPI app not initialized")
        
        logger.info(f"Starting FastAPI server on {self.host}:{self.port}")
        
        # Configure uvicorn
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="info" if SystemConfig.LOG_LEVEL == "INFO" else "debug",
            access_log=True
        )
        
        server = uvicorn.Server(config)
        
        # Start server in background task
        self.server_task = asyncio.create_task(server.serve())
        
        logger.info(f"FastAPI server started at http://{self.host}:{self.port}")
    
    def get_status(self) -> dict:
        """Get current SystemController status."""
        uptime = int(time.time() - self._start_time) if self._start_time else 0
        
        components = []
        
        if self.skald_monitor:
            components.append({
                "name": "SkaldMonitor",
                "running": self.skald_monitor.is_running(),
                "details": self.skald_monitor.get_status()
            })
        
        if self.task_monitor:
            components.append({
                "name": "TaskMonitor", 
                "running": self.task_monitor.is_running(),
                "details": self.task_monitor.get_status()
            })
        
        if self.dispatcher:
            components.append({
                "name": "Dispatcher",
                "running": self.dispatcher.is_running(),
                "details": self.dispatcher.get_status()
            })
        
        return {
            "mode": self.mode,
            "running": self._running,
            "uptime": uptime,
            "host": self.host,
            "port": self.port,
            "components": components,
            "stores": {
                "skalds": len(self.skald_store.get_all_skalds()) if self.skald_store else 0,
                "tasks": len(self.task_store.get_all_tasks()) if self.task_store else 0
            }
        }
    
    def is_running(self) -> bool:
        """Check if SystemController is running."""
        return self._running
    
    @classmethod
    def get_instance(cls) -> 'SystemController':
        """Get the singleton instance."""
        return cls()


# Convenience functions for running SystemController

async def run_system_controller():
    """
    Run SystemController as the main application.
    """
    controller = SystemController()
    
    try:
        await controller.start()
        
        # Keep running until interrupted
        while controller.is_running():
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"SystemController error: {e}")
    finally:
        await controller.stop()


def main():
    """
    Main entry point for SystemController.
    """
    logger.info("Starting Skald SystemController...")
    
    try:
        asyncio.run(run_system_controller())
    except KeyboardInterrupt:
        logger.info("SystemController stopped by user")
    except Exception as e:
        logger.error(f"SystemController failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()