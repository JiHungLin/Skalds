import asyncio
import atexit
import signal
import sys
from typing import Optional
from skald.config.skald_config import SkaldConfig, SkaldModeEnum
from skald.config.systemconfig import SystemConfig
from skald.handler.survive import SurviveHandler, SurviveRoleEnum
from skald.proxy.kafka import KafkaConfig, KafkaProxy, KafkaTopic
from skald.proxy.mongo import MongoConfig, MongoProxy
from skald.proxy.redis import RedisConfig, RedisKey, RedisProxy
from skald.store.taskworker import TaskWorkerStore
from skald.utils.logging import logger
from skald.worker.baseclass import BaseTaskWorker, TaskWorkerConfig
from skald.worker.factory import TaskWorkerFactory
from skald.worker.manager import TaskWorkerManager
from pretty_loguru.core.cleaner import LoggerCleaner
import multiprocessing as mp
from skald.utils.logging import init_logger


class Skald:
    """
    Main class for the Skald application.
    """

    def __init__(self, config: SkaldConfig):
        """
        Initialize the Skald application.
        """
        self.config = config
        self._shutdown_event = asyncio.Event()
        self._is_shutting_down = False

        # Overwrite SystemConfig class variables with values from SkaldConfig
        for attr in vars(config):
            sys_attr = attr.upper()
            if hasattr(SystemConfig, sys_attr):
                setattr(SystemConfig, sys_attr, getattr(config, attr))

        init_logger(
            logger_name=SystemConfig.SKALD_ID,
            level=SystemConfig.LOG_LEVEL,
            log_path=SystemConfig.LOG_PATH,
            process_id=SystemConfig.SKALD_ID,
            rotation=SystemConfig.LOG_ROTATION_MB
        )

        self.logger_cleaner = LoggerCleaner(log_path=SystemConfig.LOG_PATH, 
                                   log_retention=SystemConfig.LOG_RETENTION, 
                                   check_interval=3600,
                                   logger_instance=logger)
        self.logger_cleaner.start()

        if config.skald_mode == SkaldModeEnum.EDGE:
            TaskWorkerConfig.mode = "edge"
        else:
            TaskWorkerConfig.mode = "node"

        # kafka
        if config.skald_mode == "edge" and not SystemConfig.KAFKA_HOST:
            kafka_config = None
            self.kafka_proxy = None
        else:
            consume_topic_list = []
            if config.skald_mode == "node":
                consume_topic_list = [
                    KafkaTopic.TASK_ASSIGN,
                    KafkaTopic.TASK_CANCEL,
                    KafkaTopic.TASK_UPDATE_ATTACHMENT,
                    KafkaTopic.TESTING_PRODUCER
                ]
            elif config.skald_mode == "edge":
                consume_topic_list = [
                    KafkaTopic.TASK_UPDATE_ATTACHMENT,
                    KafkaTopic.TESTING_PRODUCER
                ]
            kafka_config = KafkaConfig(host=SystemConfig.KAFKA_HOST,
                                       port=SystemConfig.KAFKA_PORT,
                                       consume_topic_list=consume_topic_list,
                                       username=SystemConfig.KAFKA_USERNAME,
                                       password=SystemConfig.KAFKA_PASSWORD)
            self.kafka_proxy = KafkaProxy(kafka_config=kafka_config, is_block=config.skald_mode == "node")

        self.skald_survive_handler: Optional[SurviveHandler] = None
        self.task_worker_manager: Optional[TaskWorkerManager] = None

        # redis
        if config.skald_mode == "edge" and not SystemConfig.REDIS_HOST:
            redis_config = None
            self.redis_proxy = None
            logger.info("Edge mode, No Redis Config. Skip update slave task.")
        else:
            redis_config = RedisConfig(host=SystemConfig.REDIS_HOST, 
                                    port=SystemConfig.REDIS_PORT,
                                    password=SystemConfig.REDIS_PASSWORD)
            self.redis_proxy = RedisProxy(redis_config=redis_config, is_block=config.skald_mode == "node")

        # mongo
        mongo_config = MongoConfig(host=SystemConfig.MONGO_HOST, db_name=SystemConfig.DB_NAME)
        self.mongo_proxy = MongoProxy(mongo_config=mongo_config)
        if config.skald_mode == "node":
            self.mongo_proxy.init_db_index()
            logger.info("MongoDB index initialized.")

    def register_task_worker(self, worker: BaseTaskWorker):
        TaskWorkerFactory.register_task_worker_class(worker)

    def _setup_signal_handlers(self, loop):
        """Setup signal handlers"""
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
        """Graceful shutdown"""
        logger.info("Starting resource cleanup...")
        
        try:
            # Stop task workers
            if self.task_worker_manager:
                self.task_worker_manager.stop_kafka_consume()
                logger.info("Kafka consumption stopped")
            
            # Terminate all tasks
            TaskWorkerStore.terminate_all_task()
            logger.info("All tasks terminated")
            
            # Stop survive handler
            if self.skald_survive_handler:
                self.skald_survive_handler.stop_activity_update()
                self.skald_survive_handler.stop_heartbeat_update()
                logger.info("Heartbeat update stopped")
            
            # Stop logger cleaner
            if hasattr(self, 'logger_cleaner'):
                self.logger_cleaner.stop()
                logger.info("Logger cleaner stopped")
                
        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}")
        
        logger.info("Resource cleanup completed")

    async def _run_async(self):
        """Async run main program"""
        # Wait for shutdown signal
        await self._shutdown_event.wait()
        
        # Execute graceful shutdown
        await self._shutdown_gracefully()

    def run(self):
        TaskWorkerStore.TaskWorkerUidDic = mp.Manager().dict()  # str: str
        
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
            "Configuration",
            config_str_list
        )

        all_allow_task_worker_class_names = TaskWorkerFactory.get_all_task_worker_class_names()
        all_allow_task_worker_data_model = TaskWorkerFactory.get_all_task_worker_attachment_models()
        all_allow_task_worker_data_model = [cls.__name__ for cls in all_allow_task_worker_data_model]
        message = ["Class \t\tDataModel"]
        for class_name, data_model in zip(all_allow_task_worker_class_names, all_allow_task_worker_data_model):
            message.append(f"{class_name} \t\t{data_model}")
        logger.block(
            "All Allowed TaskWorker Class And DataModel",
            message
        )

        logger.info("\n=============================Start main loop.=============================")
        
        # Start Slave activity registration and heartbeat to Redis
        if self.redis_proxy is not None:
            self.skald_survive_handler = SurviveHandler(
                redis_proxy=self.redis_proxy,
                key=RedisKey.skald_heartbeat(SystemConfig.SKALD_ID), 
                role=SurviveRoleEnum.SKALD
                )
            self.skald_survive_handler.start_activity_update()
            logger.info("Start update slave activity time.")
            self.skald_survive_handler.start_heartbeat_update()
            logger.info("Start update slave heartbeat.")
        else:
            logger.info("Redis is not available, skip update slave activity time and heartbeat.")

        self.task_worker_manager = TaskWorkerManager(
            kafka_proxy=self.kafka_proxy, 
            redis_proxy=self.redis_proxy, 
            mongo_proxy=self.mongo_proxy
        )
        self.task_worker_manager.start_kafka_consume()

        if self.config.yaml_file and self.config.skald_mode == "edge":
            self.task_worker_manager.load_taskworker_from_yaml(yaml_file=self.config.yaml_file)

        # Use new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Setup signal handlers
            self._setup_signal_handlers(loop)
            
            # Run async main program
            loop.run_until_complete(self._run_async())
            
        except Exception as e:
            logger.error(f"Runtime error occurred: {e}")
        finally:
            # Ensure event loop is closed
            if not loop.is_closed():
                loop.close()
            logger.info("Program completely shutdown")
