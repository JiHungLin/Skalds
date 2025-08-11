from enum import Enum
from dotenv import load_dotenv
load_dotenv()

import os
import uuid
from skald.config._enum import LogLevelEnum, SkaldEnvEnum

def _bool(input):
    input = str(input)
    if input.lower() in ['true', '1', 'yes', 'y']:
        return True
    elif input.lower() in ['false', '0', 'no', 'n']:
        return False
    else:
        return False

class SkaldModeEnum(str, Enum):
    EDGE = "edge"
    NODE = "node"

class SkaldConfig:
    """
    Configuration class for the Skald application.
    """

    def __init__(
        self,
        skald_id: str = None,
        skald_env: str = None,
        log_level: str = None,
        log_path: str = None,
        log_retention: str = None,
        log_rotation_mb: str = None,
        redis_host: str = None,
        redis_port: int = None,
        redis_password: str = None,
        redis_sync_period: int = None,
        kafka_host: str = None,
        kafka_port: int = None,
        kafka_username: str = None,
        kafka_password: str = None,
        kafka_topic_partitions: int = None,
        kafka_replication_factor: int = None,
        mongo_host: str = None,
        db_name: str = None,
        task_worker_retry: int = None,
        mode: SkaldModeEnum = SkaldModeEnum.NODE,
    ):
        """
        Initialize the SkaldConfig with environment variables, defaults, or provided arguments.
        Variable names follow Python snake_case convention.
        """
        # General Config
        self.skald_id: str = skald_id if skald_id is not None else os.getenv("SKALD_ID", f"skald-{str(uuid.uuid4())[:5]}")
        self.skald_env: SkaldEnvEnum = skald_env if skald_env is not None else os.getenv("SKALD_ENV", SkaldEnvEnum.DEV.value)
        self.log_level: LogLevelEnum = log_level if log_level is not None else os.getenv("LOG_LEVEL", LogLevelEnum.DEBUG.value)
        self.log_path: str = log_path if log_path is not None else os.getenv("LOG_PATH", "logs")
        self.log_retention: str = log_retention if log_retention is not None else os.getenv("LOG_RETENTION", "3")
        self.log_rotation_mb: str = log_rotation_mb if log_rotation_mb is not None else os.getenv("LOG_ROTATION_MB", "10")

        # Redis Config
        self.redis_host: str = redis_host if redis_host is not None else os.getenv("REDIS_HOST", "")
        self.redis_port: int = redis_port if redis_port is not None else int(os.getenv("REDIS_PORT", 6379))
        self.redis_password: str = redis_password if redis_password is not None else os.getenv("REDIS_PASSWORD", "")
        self.redis_sync_period: int = redis_sync_period if redis_sync_period is not None else int(os.getenv("REDIS_SYNC_PERIOD", 3))

        # Kafka Config
        self.kafka_host: str = kafka_host if kafka_host is not None else os.getenv("KAFKA_HOST", "")
        self.kafka_port: int = kafka_port if kafka_port is not None else int(os.getenv("KAFKA_PORT", 9092))
        self.kafka_username: str = kafka_username if kafka_username is not None else os.getenv("KAFKA_USERNAME", "")
        self.kafka_password: str = kafka_password if kafka_password is not None else os.getenv("KAFKA_PASSWORD", "")
        self.kafka_topic_partitions: int = kafka_topic_partitions if kafka_topic_partitions is not None else int(os.getenv("KAFKA_TOPIC_PARTITIONS", 6))
        self.kafka_replication_factor: int = kafka_replication_factor if kafka_replication_factor is not None else int(os.getenv("KAFKA_REPLICATION_FACTOR", 3))

        # Mongo Config
        self.mongo_host: str = mongo_host if mongo_host is not None else os.getenv("MONGO_HOST", "")
        self.db_name: str = db_name if db_name is not None else os.getenv("DB_NAME", "media-module")

        # Task Worker
        self.task_worker_retry: int = task_worker_retry if task_worker_retry is not None else int(os.getenv("TASK_WORKER_RETRY", -1))

        self.mode = mode