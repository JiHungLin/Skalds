from typing import Optional
from pydantic import BaseModel
from skalds.model.task import Task
from skalds.utils.logging import logger
from skalds.proxy.kafka import KafkaConfig
from skalds.proxy.redis import RedisConfig
from skalds.worker.baseclass import BaseTaskWorker

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
    def get_all_task_worker_attachment_models(cls):
        return list(cls.taskWorkerAttachmentModelMap.values())

    @classmethod
    def register_task_worker_class(cls, task_worker_class: BaseTaskWorker):
        # check task_worker_class is instance of BaseTaskWorker
        class_name = None
        try:
            class_name = task_worker_class.__name__
        except Exception as e:
            raise ValueError(f"Failed to get class name for task worker class {task_worker_class}: {e}")

        if not issubclass(task_worker_class, BaseTaskWorker):
            raise ValueError(f"Task worker class must be an instance of BaseTaskWorker")
        
        cls.taskWorkerClassMap[class_name] = task_worker_class
        cls.taskWorkerAttachmentModelMap[class_name] = task_worker_class.get_data_model()

    @classmethod
    def create_task_worker(cls, task: Task) -> Optional[BaseTaskWorker]:
        taskWorker: BaseTaskWorker = None
        use_class: Optional[BaseTaskWorker] = None
        use_attachment: Optional[BaseModel] = None
        if task is None or task.class_name is None:
            logger.error(f"Invalid task or class name: {task}")
            return taskWorker
        use_class = cls.taskWorkerClassMap.get(task.class_name, None)
        use_attachment = cls.taskWorkerAttachmentModelMap.get(task.class_name, None)
        if use_class is None:
            logger.error(f"Cannot find TaskWorker Class for {task.class_name}")
            return taskWorker
        if use_attachment is None:
            logger.error(f"Cannot find TaskWorker Attachment Model for {task.class_name}")
            return taskWorker
        try:
            logger.info(f"Create {task.class_name} Task Worker [{use_class.__name__}]")
            task.attachments = use_attachment.model_validate(task.attachments) if task.attachments else None
            taskWorker = use_class(
                task=task, 
                redis_config=cls.redisConfig, 
                kafka_config=cls.kafkaConfig
                )
            return taskWorker

        except Exception as e:
            logger.error(f"Create {task.class_name} Task Worker Error: {e}")
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