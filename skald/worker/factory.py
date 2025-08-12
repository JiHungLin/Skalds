from typing import Optional
from pydantic import BaseModel
from skald.model.task import Task
from skald.utils.logging import logger
from proxy.kafka import KafkaConfig
from proxy.redis import RedisConfig
from skald.worker.baseclass import BaseTaskWorker

class TaskWorkerFactory:

    redisConfig: Optional[RedisConfig] = None
    kafkaConfig: Optional[KafkaConfig] = None
    taskWorkerClassMap: dict[str, BaseTaskWorker] = {}  # type: ignore
    taskWorkerAttachmentModelMap: dict[str, BaseModel] = {}

    @classmethod
    def set_redis_config(cls, redis_config: RedisConfig):
        cls.redisConfig = redis_config

    @classmethod
    def set_kafka_config(cls, kafka_config: KafkaConfig):
        cls.kafkaConfig = kafka_config

    @classmethod
    def get_all_task_worker_class_names(cls):
        return list(cls.taskWorkerClassMap.keys())

    @classmethod
    def register_task_worker_class(cls, task_worker_class: BaseTaskWorker):
        # check task_worker_class is instance of BaseTaskWorker
        class_name = None
        try:
            class_name = task_worker_class.__class__.__name__
        except Exception as e:
            raise ValueError(f"Failed to get class name for task worker class {task_worker_class}: {e}")

        if not isinstance(task_worker_class, BaseTaskWorker):
            raise ValueError(f"Task worker class must be an instance of BaseTaskWorker")

        cls.taskWorkerClassMap[class_name] = task_worker_class

        # TODO: Need to define some way to get TaskWorker init model

    @classmethod
    def create_task_worker(cls, task: Task) -> Optional[BaseTaskWorker]:
        taskWorker: BaseTaskWorker = None
        use_class = None
        use_attachment = None
        if task is None and task.className is None:
            use_class = cls.taskWorkerClassMap.get(task.className, None)
            use_attachment = cls.taskWorkerAttachmentModelMap.get(task.className, None)
        if use_class is None:
            raise ValueError(f"Cannot find TaskWorker Class for {task.className}")
        if use_attachment is None:
            raise ValueError(f"Cannot find TaskWorker Attachment Model for {task.className}")
        try:
            logger.info(f"Create {task.className} Task Worker [{use_class.__name__}]")
            # TODO: implement task worker creation logic
            return taskWorker

        except Exception as e:
            logger.error(f"Create {task.className} Task Worker Error: {e}")
        finally:
            return taskWorker
    
    @classmethod
    def create_attachment_with_class_name_and_dict(cls, task_class_name: str, data: dict) -> Optional[BaseModel]:
        attachment_model = cls.taskWorkerAttachmentModelMap.get(task_class_name, None)
        if attachment_model is None:
            logger.error(f"Cannot find Attachment Model for {task_class_name}")
            return None
        try:
            return attachment_model.model_validate(data)
        except Exception as e:
            logger.error(f"Create {task_class_name} Attachment Error: {e}")
            return None