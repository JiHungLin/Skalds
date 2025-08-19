"""
SystemController Main Module

Main SystemController class that orchestrates all components based on configuration.
Provides a single entry point for the entire SystemController system.
"""

import asyncio
import signal
import threading
import time
import sys
from typing import Optional
import uvicorn
from pretty_loguru.core.cleaner import LoggerCleaner

from skald.config.systemconfig import SystemConfig
from skald.config.system_controller_config import SystemControllerConfig
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

from skald.utils.logging import logger, init_logger


class SystemController:
    """
    Main SystemController class that manages all components.
    
    This class orchestrates the entire SystemController system based on the
    configured mode (controller, monitor, dispatcher).
    """
    _instance: Optional["SystemController"] = None

    def __init__(self, config: SystemControllerConfig):
        """
        Initialize the SystemController application.
        """
        self.config = config
        
        # Overwrite SystemConfig class variables with values from SystemControllerConfig
        for attr in vars(config):
            sys_attr = attr.upper()
            if hasattr(SystemConfig, sys_attr):
                setattr(SystemConfig, sys_attr, getattr(config, attr))
        
        # Initialize logger with config values
        init_logger(
            logger_name="SystemController",
            level=self.config.log_level,
            log_path=self.config.log_path,
            process_id="SystemController",
            rotation=self.config.log_rotation_mb
        )
        
        # Initialize logger cleaner
        self.logger_cleaner = LoggerCleaner(
            log_path=self.config.log_path,
            log_retention=self.config.log_retention,
            check_interval=3600,
            logger_instance=logger
        )
        self.logger_cleaner.start()
        
        # Configuration properties
        self.mode = self.config.system_controller_mode
        self.host = self.config.system_controller_host
        self.port = self.config.system_controller_port
        
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
        self._shutdown_event = asyncio.Event()
        self._is_shutting_down = False
        
        logger.info(f"SystemController initialized in {self.mode} mode")
        print(f"SystemController initialized in {self.mode} mode")
        SystemController._instance = self
        print(f"SystemController instance set: {self._instance is not None}")

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
                logger.info("Stopping FastAPI server...")
                self.server_task.cancel()
                try:
                    await self.server_task
                    logger.info("FastAPI server stopped successfully")
                except asyncio.CancelledError:
                    pass
            
            # Stop monitor components
            if self.dispatcher:
                logger.info("Stopping Dispatcher...10s")
                self.dispatcher.stop()
            
            if self.task_monitor:
                logger.info("Stopping TaskMonitor...10s")
                self.task_monitor.stop()
            
            if self.skald_monitor:
                logger.info("Stopping SkaldMonitor...10s")
                self.skald_monitor.stop()
            
            # Stop logger cleaner
            if hasattr(self, 'logger_cleaner'):
                self.logger_cleaner.stop()
                logger.info("Logger cleaner stopped")
            
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
        if self.config.redis_host:
            redis_config = RedisConfig(
                host=self.config.redis_host,
                port=self.config.redis_port,
                password=self.config.redis_password
            )
            self.redis_proxy = RedisProxy(redis_config, is_block=True)
            logger.info("Redis proxy initialized")
        else:
            logger.warning("Redis host not configured")
        
        # MongoDB proxy
        if self.config.mongo_host:
            mongo_config = MongoConfig(
                host=self.config.mongo_host,
                db_name=self.config.db_name
            )
            self.mongo_proxy = MongoProxy(mongo_config)
            self.mongo_proxy.init_db_index()
            
            # Initialize task repository
            self.task_repository = TaskRepository(self.mongo_proxy)
            logger.info("MongoDB proxy and TaskRepository initialized")
        else:
            logger.warning("MongoDB host not configured")
        
        # Kafka proxy (needed for dispatcher mode)
        # Note: Kafka config not included in SystemControllerConfig as it's typically not needed
        if (self.mode in [SystemControllerModeEnum.MONITOR, SystemControllerModeEnum.DISPATCHER] and
            self.config.kafka_host):
            kafka_config = KafkaConfig(
                host=self.config.kafka_host,
                port=self.config.kafka_port,
                username=self.config.kafka_username,
                password=self.config.kafka_password
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
                self.config.monitor_skald_interval
            )
            
            # Initialize TaskMonitor
            if self.mongo_proxy:
                self.task_monitor = TaskMonitor(
                    self.redis_proxy,
                    self.mongo_proxy,
                    self.kafka_proxy,
                    self.config.monitor_task_interval
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
                    self.config.dispatcher_interval
                )
        
        # Initialize FastAPI app
        enable_dashboard = self.mode in [
            SystemControllerModeEnum.MONITOR,
            SystemControllerModeEnum.DISPATCHER
        ]
        print(SystemController._instance, "main.py")
        self.app = create_app(
            task_repository=self.task_repository,
            kafka_proxy=self.kafka_proxy,
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
        import os
        # 強制 workers=1，避免多進程 in-memory 狀態不同步
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="info" if self.config.log_level == "INFO" else "debug",
            access_log=True,
            workers=1
        )
        # 啟動時檢查外部環境變數，若有多 worker 設定則報錯
        if (
            int(os.environ.get("UVICORN_WORKERS", "1")) > 1 or
            int(os.environ.get("WEB_CONCURRENCY", "1")) > 1 or
            "gunicorn" in sys.argv[0].lower()
        ):
            logger.error("多進程模式會導致 in-memory 狀態不同步，請將 worker 數量設為 1！")
            raise RuntimeError("請勿以多 worker 模式啟動 SystemController，否則 /api/events/tasks 會無法取得正確資料。")
        
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
    
    def _setup_signal_handlers(self, loop):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            if not self._is_shutting_down:
                logger.info(f"Received signal {signum}, starting graceful shutdown...")
                self._is_shutting_down = True
                # Set shutdown event in the event loop
                loop.call_soon_threadsafe(self._shutdown_event.set)
            else:
                logger.warning("Already shutting down, forcing exit...")
                sys.exit(1)

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def _shutdown_gracefully(self):
        """Graceful shutdown of all components"""
        logger.info("Starting graceful shutdown...")
        
        try:
            # Stop the SystemController
            await self.stop()
            
        except Exception as e:
            logger.error(f"Error during graceful shutdown: {e}")
        
        logger.info("Graceful shutdown completed")

    async def _run_async(self):
        """Async run main program"""
        # Wait for shutdown signal
        await self._shutdown_event.wait()
        
        # Execute graceful shutdown
        await self._shutdown_gracefully()

    def run(self):
        """
        Run SystemController as the main application.
        Similar to Skald.run() method for consistent API.
        """
        # Log configuration like Skald does
        config_str_list = []
        for k, v in self.config.dict().items():
            if "password" in k.lower():
                v = "******"
            if k == "mongo_host":
                # mongodb://username:password@localhost:27017/
                if isinstance(v, str) and '@' in v:
                    parts = v.split('@')
                    sub_part1 = parts[0].split(':')[:-1]
                    v = f"{':'.join(sub_part1)}:******@{parts[1]}"
            config_str_list.append(f"{k}: {v}")

        logger.block(
            "SystemController Configuration",
            config_str_list
        )

        logger.info("\n=============================Start SystemController main loop.=============================")
        
        # Use new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        startup_failed = False
        
        try:
            # Setup signal handlers
            self._setup_signal_handlers(loop)
            
            # Start the SystemController
            loop.run_until_complete(self.start())
            
            # Only run the main loop if startup was successful
            if self._running:
                # Run async main program (wait for shutdown signal)
                loop.run_until_complete(self._run_async())
            else:
                startup_failed = True
                logger.error("SystemController failed to start properly")
            
        except KeyboardInterrupt:
            logger.info("SystemController stopped by user")
        except Exception as e:
            logger.error(f"SystemController runtime error: {e}")
            startup_failed = True
        finally:
            # Ensure event loop is closed
            if not loop.is_closed():
                loop.close()
            logger.info("SystemController completely shutdown")
            
            # Exit the process if startup failed
            if startup_failed:
                logger.error("SystemController failed to start, exiting process")
                sys.exit(1)

def main(config: SystemControllerConfig = None):
    """
    Main entry point for SystemController.
    
    Deprecated: Use SystemController(config).run() instead for consistency with Skald.
    This function is kept for backward compatibility.
    """
    logger.info("Starting Skald SystemController...")
    
    if config is None:
        config = SystemControllerConfig()
    
    try:
        controller = SystemController(config)
        controller.run()
    except Exception as e:
        logger.error(f"SystemController failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Create default config when running directly
    default_config = SystemControllerConfig(
        system_controller_mode=SystemControllerModeEnum.MONITOR,
        log_path=""
    )
    main(default_config)