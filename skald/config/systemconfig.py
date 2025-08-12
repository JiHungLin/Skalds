from dotenv import load_dotenv
load_dotenv()

import os
from  skald.config._enum import LogLevelEnum, SkaldEnvEnum, SkaldModeEnum
import uuid


def _bool(input):
    input = str(input)
    if input.lower() in ['true', '1', 'yes', 'y']:
        return True
    elif input.lower() in ['false', '0', 'no', 'n']:
        return False
    else:
        return False
    
class SystemConfig:
    SKALD_ID : str = os.getenv("SKALD_ID", f"skald-{str(uuid.uuid4())[:5]}") 
    SKALD_ENV: SkaldEnvEnum = os.getenv("SKALD_ENV", SkaldEnvEnum.DEV.value)  # dev / production 
    SKALD_MODE: SkaldModeEnum = os.getenv("SKALD_MODE", SkaldModeEnum.NODE.value)  # edge / node
    LOG_LEVEL: LogLevelEnum = os.getenv("LOG_LEVEL", LogLevelEnum.DEBUG.value) # TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL
    LOG_PATH: str = os.getenv("LOG_PATH", "logs")
    LOG_RETENTION: str = os.getenv("LOG_RETENTION", "3")
    LOG_ROTATION_MB: str = os.getenv("LOG_ROTATION_MB", "10")

    # TaskWorker YAML Config
    YAML_FILE: str = os.getenv("YAML_FILE", "")

    # Redis Config
    REDIS_HOST: str = os.getenv("REDIS_HOST", "")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_SYNC_PERIOD: int = int(os.getenv("REDIS_SYNC_PERIOD", 3))

    # Kafka Config
    KAFKA_HOST: str = os.getenv("KAFKA_HOST", "")
    KAFKA_PORT: int = int(os.getenv("KAFKA_PORT", 9092))
    KAFKA_USERNAME: str = os.getenv("KAFKA_USERNAME", "")
    KAFKA_PASSWORD: str = os.getenv("KAFKA_PASSWORD", "")
    KAFKA_TOPIC_PARTITIONS: int = int(os.getenv("KAFKA_TOPIC_PARTITIONS", 6))
    KAFKA_REPLICATION_FACTOR: int = int(os.getenv("KAFKA_REPLICATION_FACTOR", 3))

    # Mongo Config
    MONGO_HOST: str = os.getenv("MONGO_HOST", "")
    DB_NAME: str = os.getenv("DB_NAME", "media-module")

    TASK_WORKER_RETRY: int = int(os.getenv("TASK_WORKER_RETRY", -1))
