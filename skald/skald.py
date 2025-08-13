import asyncio
import atexit
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


def exit_handler(skald_survive_handler: Optional[SurviveHandler], task_worker_manager: Optional[TaskWorkerManager]):
    # 結束所有子進程
    try:
        TaskWorkerStore.terminate_all_task()
        if skald_survive_handler:
            skald_survive_handler.stop_activity_update()
            skald_survive_handler.stop_heartbeat_update()
        if task_worker_manager:
            task_worker_manager.stop_kafka_consume()
    finally:
        return 0


class Skald:
    """
    Main class for the Skald application.
    """

    def __init__(self, config: SkaldConfig):
        """
        Initialize the Skald application.
        """
        self.config = config

        # Overwrite SystemConfig class variables with values from SkaldConfig
        for attr in vars(config):
            sys_attr = attr.upper()
            if hasattr(SystemConfig, sys_attr):
                setattr(SystemConfig, sys_attr, getattr(config, attr))

        init_logger(level=SystemConfig.LOG_LEVEL,
                log_path=SystemConfig.LOG_PATH,
                process_id=SystemConfig.SKALD_ID,
                rotation=SystemConfig.LOG_ROTATION_MB)

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

    def register_task_worker(self, worker: BaseTaskWorker):
        TaskWorkerFactory.register_task_worker_class(worker)

    def run(self):
        TaskWorkerStore.TaskWorkerUidDic = mp.Manager().dict()  # str: str
        
        config_str_list = []
        for k, v in self.config.dict().items():
            config_str_list.append(f"{k}: {v}")
        

        logger.block(
            "Configuration",
            config_str_list
        )
        logger.info("\n=============================Start main loop.=============================")
        
        # 啟動 Slave 活動註冊與心跳於Redis
        if self.redis_proxy is not None:
            slave_survive_handler = SurviveHandler(
                redis_proxy=self.redis_proxy,
                key=RedisKey.skald_heartbeat(SystemConfig.SKALD_ID), 
                role=SurviveRoleEnum.SKALD
                )
            slave_survive_handler.start_activity_update()
            logger.info("Start update slave activity time.")
            slave_survive_handler.start_heartbeat_update()
            logger.info("Start update slave heartbeat.")
        else:
            slave_survive_handler = None
            logger.info("Redis is not available, skip update slave activity time and heartbeat.")

        self.task_worker_manager = TaskWorkerManager(
            kafka_proxy=self.kafka_proxy, 
            redis_proxy=self.redis_proxy, 
            mongo_proxy=self.mongo_proxy
        )
        self.task_worker_manager.start_kafka_consume()

        if self.config.yaml_file:
            self.task_worker_manager.load_taskworker_from_yaml(yaml_file=self.config.yaml_file)

        loop = asyncio.get_event_loop()
        try:
            atexit.register(exit_handler, 
                            skald_survive_handler=self.skald_survive_handler, 
                            task_worker_manager=self.task_worker_manager
                            )
            loop.run_forever()
        except KeyboardInterrupt:
            logger.warning("強制中斷主程式")
        finally:
            loop.close()