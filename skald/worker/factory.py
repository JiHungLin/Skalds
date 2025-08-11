from entity.task import Task, TaskUnitClassNameEnum
from log import logger
from proxy.kafka import KafkaConfig
from proxy.redis import RedisConfig
from taskworker.baseclass import BaseTaskWorkerV1

class TaskWorkerFactory:

    taskWorkerClassMap: dict[TaskUnitClassNameEnum, BaseTaskWorkerV1] = {}  # type: ignore

    def __init__(self, 
                redis_config: RedisConfig = None, 
                kafka_config: KafkaConfig = None, 
                ) -> None:
        self.redsConfig = redis_config
        self.kafka_config = kafka_config

    @classmethod
    def register_task_worker(cls, task_class_name: TaskUnitClassNameEnum, task_worker_class: BaseTaskWorkerV1):
        if task_class_name in cls.taskWorkerClassMap:
            raise ValueError(f"Task worker for {task_class_name} already registered.")
        else:
            cls.taskWorkerClassMap[task_class_name] = task_worker_class

    def create_task_worker(self, task: Task)-> BaseTaskWorkerV1:
        taskWorker: BaseTaskWorkerV1 = None
        try:
            use_class_enum = TaskUnitClassNameEnum(task.className) if isinstance(task.className, str) else task.className
            use_class = TaskWorkerFactory.taskWorkerClassMap.get(use_class_enum, None)
            if use_class:
                logger.info(f"Create {task.className} Task Worker [{use_class.__name__}]")
                taskWorker = use_class(task=task, redis_config=self.redsConfig, kafka_config=self.kafka_config)
                return taskWorker
            else:
                logger.warning(f"No Task Worker registered for {task.className}, skip creating worker.")

        except Exception as e:
            logger.error(f"Create {task.className} Task Worker Error: {e}")
        finally:
            return taskWorker
        
        