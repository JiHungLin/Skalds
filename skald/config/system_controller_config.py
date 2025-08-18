from skald.config.systemconfig import SystemConfig
from skald.config._enum import LogLevelEnum, SkaldEnvEnum, SystemControllerModeEnum, DispatcherStrategyEnum


def _bool(input):
    input = str(input)
    if input.lower() in ['true', '1', 'yes', 'y']:
        return True
    elif input.lower() in ['false', '0', 'no', 'n']:
        return False
    else:
        return False


class SystemControllerConfig:
    """
    Configuration class for the SystemController application.
    """

    def __init__(
        self,
        system_controller_id: str = None,
        system_controller_mode: SystemControllerModeEnum = None,
        system_controller_host: str = None,
        system_controller_port: int = None,
        log_level: LogLevelEnum = None,
        log_path: str = None,
        log_retention: str = None,
        log_rotation_mb: str = None,
        log_split_with_worker_id: bool = None,
        redis_host: str = None,
        redis_port: int = None,
        redis_password: str = None,
        redis_sync_period: int = None,
        redis_key_ttl: int = None,
        kafka_host: str = None,
        kafka_port: int = None,
        kafka_username: str = None,
        kafka_password: str = None,
        kafka_topic_partitions: int = None,
        kafka_replication_factor: int = None,
        mongo_host: str = None,
        db_name: str = None,
        monitor_skald_interval: int = None,
        monitor_task_interval: int = None,
        monitor_heartbeat_timeout: int = None,
        dispatcher_interval: int = None,
        dispatcher_strategy: DispatcherStrategyEnum = None,
    ):
        """
        Initialize the SystemControllerConfig with environment variables, defaults, or provided arguments.
        Variable names follow Python snake_case convention.
        """
        # General Config
        self.system_controller_id: str = system_controller_id if system_controller_id is not None else "SystemController"
        self.system_controller_mode: SystemControllerModeEnum = system_controller_mode if system_controller_mode is not None else SystemConfig.SYSTEM_CONTROLLER_MODE
        self.system_controller_host: str = system_controller_host if system_controller_host is not None else SystemConfig.SYSTEM_CONTROLLER_HOST
        self.system_controller_port: int = system_controller_port if system_controller_port is not None else SystemConfig.SYSTEM_CONTROLLER_PORT
        
        # Logging Config
        self.log_level: LogLevelEnum = log_level if log_level is not None else SystemConfig.LOG_LEVEL
        self.log_path: str = log_path if log_path is not None else SystemConfig.LOG_PATH
        self.log_retention: str = log_retention if log_retention is not None else SystemConfig.LOG_RETENTION
        self.log_rotation_mb: str = log_rotation_mb if log_rotation_mb is not None else SystemConfig.LOG_ROTATION_MB
        self.log_split_with_worker_id: bool = log_split_with_worker_id if log_split_with_worker_id is not None else SystemConfig.LOG_SPLIT_WITH_WORKER_ID
        
        # Redis Config
        self.redis_host: str = redis_host if redis_host is not None else SystemConfig.REDIS_HOST
        self.redis_port: int = redis_port if redis_port is not None else SystemConfig.REDIS_PORT
        self.redis_password: str = redis_password if redis_password is not None else SystemConfig.REDIS_PASSWORD
        self.redis_sync_period: int = redis_sync_period if redis_sync_period is not None else SystemConfig.REDIS_SYNC_PERIOD
        self.redis_key_ttl: int = redis_key_ttl if redis_key_ttl is not None else SystemConfig.REDIS_KEY_TTL

        # Kafka Config
        self.kafka_host: str = kafka_host if kafka_host is not None else SystemConfig.KAFKA_HOST
        self.kafka_port: int = kafka_port if kafka_port is not None else SystemConfig.KAFKA_PORT
        self.kafka_username: str = kafka_username if kafka_username is not None else SystemConfig.KAFKA_USERNAME
        self.kafka_password: str = kafka_password if kafka_password is not None else SystemConfig.KAFKA_PASSWORD
        self.kafka_topic_partitions: int = kafka_topic_partitions if kafka_topic_partitions is not None else SystemConfig.KAFKA_TOPIC_PARTITIONS
        self.kafka_replication_factor: int = kafka_replication_factor if kafka_replication_factor is not None else SystemConfig.KAFKA_REPLICATION_FACTOR

        # Mongo Config
        self.mongo_host: str = mongo_host if mongo_host is not None else SystemConfig.MONGO_HOST
        self.db_name: str = db_name if db_name is not None else SystemConfig.DB_NAME

        # Monitor Configuration
        self.monitor_skald_interval: int = monitor_skald_interval if monitor_skald_interval is not None else SystemConfig.MONITOR_SKALD_INTERVAL
        self.monitor_task_interval: int = monitor_task_interval if monitor_task_interval is not None else SystemConfig.MONITOR_TASK_INTERVAL
        self.monitor_heartbeat_timeout: int = monitor_heartbeat_timeout if monitor_heartbeat_timeout is not None else SystemConfig.MONITOR_HEARTBEAT_TIMEOUT

        # Dispatcher Configuration
        self.dispatcher_interval: int = dispatcher_interval if dispatcher_interval is not None else SystemConfig.DISPATCHER_INTERVAL
        self.dispatcher_strategy: DispatcherStrategyEnum = dispatcher_strategy if dispatcher_strategy is not None else SystemConfig.DISPATCHER_STRATEGY

    def dict(self):
        """
        Convert the configuration to a dictionary.
        """
        return {
            "system_controller_id": self.system_controller_id,
            "system_controller_mode": self.system_controller_mode,
            "system_controller_host": self.system_controller_host,
            "system_controller_port": self.system_controller_port,
            "log_level": self.log_level,
            "log_path": self.log_path,
            "log_retention": self.log_retention,
            "log_rotation_mb": self.log_rotation_mb,
            "log_split_with_worker_id": self.log_split_with_worker_id,
            "redis_host": self.redis_host,
            "redis_port": self.redis_port,
            "redis_password": self.redis_password,
            "redis_sync_period": self.redis_sync_period,
            "redis_key_ttl": self.redis_key_ttl,
            "kafka_host": self.kafka_host,
            "kafka_port": self.kafka_port,
            "kafka_username": self.kafka_username,
            "kafka_password": self.kafka_password,
            "kafka_topic_partitions": self.kafka_topic_partitions,
            "kafka_replication_factor": self.kafka_replication_factor,
            "mongo_host": self.mongo_host,
            "db_name": self.db_name,
            "monitor_skald_interval": self.monitor_skald_interval,
            "monitor_task_interval": self.monitor_task_interval,
            "monitor_heartbeat_timeout": self.monitor_heartbeat_timeout,
            "dispatcher_interval": self.dispatcher_interval,
            "dispatcher_strategy": self.dispatcher_strategy
        }