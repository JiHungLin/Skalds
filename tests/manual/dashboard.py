from skald.config._enum import DispatcherStrategyEnum, LogLevelEnum, SystemControllerModeEnum
from skald.system_controller import SystemController
from skald.config.system_controller_config import SystemControllerConfig
import asyncio


config = SystemControllerConfig(
    system_controller_mode=SystemControllerModeEnum.MONITOR,
    system_controller_host="0.0.0.0",
    system_controller_port=8000,
    redis_host="localhost",
    redis_port=6379,
    kafka_host="127.0.0.1",
    kafka_port=9092,
    mongo_host="mongodb://root:root@localhost:27017",
    db_name="skald",
    monitor_skald_interval=5,
    monitor_task_interval=5,
    monitor_heartbeat_timeout=5,
    dispatcher_interval=5,
    dispatcher_strategy=DispatcherStrategyEnum.ROUND_ROBIN,
    log_level=LogLevelEnum.DEBUG
)

system_controller = SystemController(config)

if __name__ == "__main__":
    system_controller.run()
