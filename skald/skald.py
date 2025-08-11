import asyncio
import atexit
from typing import Optional
from skald.config.skald_config import SkaldConfig, SkaldModeEnum
from skald.config.systemconfig import SystemConfig
from skald.handler.survive import SurviveHandler
from skald.store.taskworker import TaskWorkerStore
from skald.utils.logging import logger
from skald.worker.baseclass import BaseTaskWorkerV1
from skald.worker.manager import TaskWorkerManager


def exit_handler(slave_survive_handler: Optional[SurviveHandler], task_worker_manager: Optional[TaskWorkerManager]):
    # 結束所有子進程
    try:
        TaskWorkerStore.terminate_all_task()
        if slave_survive_handler:
            slave_survive_handler.stop_activity_update()
            slave_survive_handler.stop_heartbeat_update()
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

        self.slave_survive_handler: Optional[SurviveHandler] = None
        self.task_worker_manager: Optional[TaskWorkerManager] = None

    def register_task_worker(self, worker: BaseTaskWorkerV1):
        ...

    def run(self):
        loop = asyncio.get_event_loop()
        logger.info("\n=============================Start main loop.=============================")

        try:
            atexit.register(exit_handler, 
                            slave_survive_handler=self.slave_survive_handler, 
                            task_worker_manager=self.task_worker_manager
                            )
            loop.run_forever()
        except KeyboardInterrupt:
            logger.warning("強制中斷主程式")
        finally:
            loop.close()