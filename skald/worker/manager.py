"""TaskWorkerManager: Manages the lifecycle and orchestration of TaskWorkers.

This module provides the TaskWorkerManager class, which is responsible for:
- Loading TaskWorkers from YAML configuration or MongoDB
- Creating, updating, and cancelling TaskWorkers based on Kafka events
- Synchronizing TaskWorker state to Redis
- Managing TaskWorker process lifecycle and state
- Handling Kafka consumer loop for task events

Author: Skald Project Contributors
"""

import asyncio
import datetime
import secrets
import time
import threading
from threading import Thread
from typing import Optional

from skald.model.event import TaskEvent, UpdateTaskWorkerEvent
from skald.repository.repository import TaskRepository
from skald.model.task import ModeEnum, Task, TaskWorkerSimpleMapList, TaskLifecycleStatus
from skald.proxy.kafka import KafkaConfig, KafkaProxy, KafkaTopic
from ruamel.yaml import YAML
from skald.proxy.mongo import MongoProxy
from skald.utils.logging import logger
from skald.proxy.redis import RedisConfig, RedisKey, RedisProxy
from skald.store.taskworker import TaskWorkerStore
from skald.config.systemconfig import SystemConfig
from skald.worker.baseclass import BaseTaskWorker
from skald.worker.factory import TaskWorkerFactory

class TaskWorkerManager:
    """
    Manages TaskWorker lifecycle, event handling, and state synchronization.

    Responsibilities:
    - Load TaskWorkers from YAML or MongoDB
    - Handle Kafka events for task assignment, cancellation, and updates
    - Synchronize TaskWorker state to Redis
    - Manage TaskWorker process lifecycle
    """

    def __init__(
        self,
        kafka_proxy: KafkaProxy,
        redis_proxy: RedisProxy,
        mongo_proxy: MongoProxy
    ) -> None:
        """
        Initialize the TaskWorkerManager.

        Args:
            kafka_proxy: KafkaProxy instance for event communication.
            redis_proxy: RedisProxy instance for state synchronization.
            mongo_proxy: MongoProxy instance for task persistence.
        """
        self.kafka_proxy = kafka_proxy
        self.redis_proxy = redis_proxy
        self.mongo_proxy = mongo_proxy
        self._kafka_consume_thread: Optional[Thread] = None
        logger.info("TaskWorkerManager initialized.")

        # Entity Repository
        self.task_repository = TaskRepository(mongo_proxy=self.mongo_proxy)

        # Configuration
        redis_config = RedisConfig(
            host=SystemConfig.REDIS_HOST,
            port=SystemConfig.REDIS_PORT,
            password=SystemConfig.REDIS_PASSWORD
        )
        kafka_config = KafkaConfig(
            host=SystemConfig.KAFKA_HOST,
            port=SystemConfig.KAFKA_PORT,
            username=SystemConfig.KAFKA_USERNAME,
            password=SystemConfig.KAFKA_PASSWORD
        )

        TaskWorkerFactory.set_redis_config(redis_config)
        TaskWorkerFactory.set_kafka_config(kafka_config)

        # TaskWorkerSimpleMapList
        self.task_worker_simple_map_list = TaskWorkerSimpleMapList()
        self._is_sync_all_taskworker_to_redis_flag = False
        self._async_all_taskworker_to_redis_thread: Optional[threading.Thread] = None
        self._start_sync_all_taskworker_to_redis()

    def start_kafka_consume(self) -> None:
        """Start the Kafka consumer thread for task events."""
        if self._kafka_consume_thread is None:
            self._kafka_consume_thread = Thread(target=self._kafka_consume_func, daemon=True)
            self._kafka_consume_thread.start()
            logger.success("Started Kafka consumer thread.")
        else:
            logger.warning("Kafka consumer already started.")

    def stop_kafka_consume(self) -> None:
        """Stop the Kafka consumer thread (not supported)."""
        logger.warning("Kafka consumer stop function is not supported.")

    # -------------------
    # Load From YAML
    # -------------------
    def load_taskworker_from_yaml(self, yaml_file: str) -> None:
        """
        Load TaskWorkers from a YAML configuration file.

        Args:
            yaml_file: Path to the YAML file.
        """
        yaml = YAML(typ="safe")
        yaml.default_flow_style = False

        try:
            with open(yaml_file, 'r') as f:
                config = yaml.load(f)
        except Exception as e:
            logger.error(f"Failed to load YAML file '{yaml_file}': {e}")
            return

        if config and config.get("TaskWorkers"):
            for task_id, value in config["TaskWorkers"].items():
                task: Optional[Task] = None
                attachments = value.get('attachments', {})
                try:
                    raise NotImplementedError("YAML loading not implemented")
                    remote_task = self.task_repository.get_task_by_task_id(id=task_id)
                    if remote_task is not None:
                        # If task already exists, update task attachments
                        value['attachments'] = remote_task.attachments.model_dump()
                        logger.info(f"Task {task_id} already exists, updating attachments from MongoDB.")
                        task = Task(
                            id=task_id,
                            name=task_id,
                            class_name=value['className'],
                            description=f"Active TaskWorker from MongoDB. ClassName: {value['className']}",
                            source="YAML",
                            executor=SystemConfig.SKALD_ID,
                            mode=ModeEnum.ACTIVE,
                            create_date_time=remote_task.createDateTime,
                            update_date_time=int(datetime.datetime.now().timestamp() * 1000),
                            deadline_date_time=remote_task.deadlineDateTime,
                            lifecycle_status=remote_task.lifecycleStatus,
                            priority=remote_task.priority,
                            attachments=remote_task.attachments
                        )
                        self.task_repository.update_executor(id=task_id, executor=SystemConfig.SKALD_ID)
                    else:
                        attachments_obj = TaskWorkerFactory.create_attachment_with_class_name_and_dict(
                            value['className'],
                            attachments
                        )
                        task = Task(
                            id=task_id,
                            name=task_id,
                            class_name=value['className'],
                            description=f"Active TaskWorker from YAML. ClassName: {value['className']}",
                            source="YAML",
                            executor=SystemConfig.SKALD_ID,
                            mode=ModeEnum.ACTIVE,
                            create_date_time=int(datetime.datetime.now().timestamp() * 1000),
                            update_date_time=int(datetime.datetime.now().timestamp() * 1000),
                            deadline_date_time=0,
                            lifecycle_status=TaskLifecycleStatus.RUNNING,
                            priority=0,
                            attachments=attachments_obj
                        )
                        self.task_repository.create_task(task=task)
                        logger.info(f"Task {task_id} did not exist, created new task.")
                except Exception as e:
                    logger.error(f"Error loading task {task_id} from MongoDB or YAML: {e}")
                    attachments_obj = TaskWorkerFactory.create_attachment_with_class_name_and_dict(
                        value['className'],
                        attachments
                    )
                    task = Task(
                        id=task_id,
                        name=task_id,
                        class_name=value['className'],
                        description=f"Active TaskWorker from YAML. ClassName: {value['className']}",
                        source="YAML",
                        executor=SystemConfig.SKALD_ID,
                        mode=ModeEnum.ACTIVE,
                        create_date_time=int(datetime.datetime.now().timestamp() * 1000),
                        update_date_time=int(datetime.datetime.now().timestamp() * 1000),
                        deadline_date_time=0,
                        lifecycle_status=TaskLifecycleStatus.RUNNING,
                        priority=0,
                        attachments=attachments_obj
                    )
                finally:
                    task_worker = TaskWorkerFactory.create_task_worker(task=task)
                    if task_worker is not None:
                        TaskWorkerStore.register_task_and_start(task_id=task_id, process=task_worker)
                        self.task_worker_simple_map_list.push(task_id=task_id, class_name=task.class_name)
                        logger.success(
                            f"New TaskWorker created from YAML. TaskId: {task_id}, "
                            f"ProcessId: {getattr(task_worker, 'pid', None)}, TaskWorker: {getattr(task_worker, '__dict__', {})}"
                        )
                    else:
                        logger.warning(
                            f"Failed to create TaskWorker from YAML. TaskId: {task_id}, " +
                            f"ClassName: {task.class_name}, Attachments: {attachments_obj}"
                        )

        try:
            with open(yaml_file, 'w') as f:
                yaml.dump(config, f)
        except Exception as e:
            logger.error(f"Failed to write back to YAML file '{yaml_file}': {e}")

    # -------------------
    # Task Creation
    # -------------------
    def _create_task_worker(self, message: str) -> None:
        """
        Create TaskWorkers based on a TaskEvent message.

        Args:
            message: JSON string representing a TaskEvent.
        """
        task_event = TaskEvent(json_str=message)
        for task_id in task_event.taskIds:
            if task_id not in TaskWorkerStore.all_task_worker_task_id():
                task = self.task_repository.get_task_by_task_id(id=task_id)
                if not self._ensure_task_can_be_processed(task=task, task_id=task_id):
                    continue
                new_task_worker = TaskWorkerFactory.create_task_worker(task=task)
                if new_task_worker is None:
                    logger.error(f"Failed to create TaskWorker. Task: {task.model_dump_json(indent=2)}")
                    continue
                TaskWorkerStore.register_task_and_start(task_id=task_id, process=new_task_worker)
                self.task_worker_simple_map_list.push(task_id=task_id, class_name=task.class_name)
                logger.success(
                    f"New TaskWorker created. TaskId: {task_id}, "
                    f"ProcessId: {getattr(new_task_worker, 'pid', None)}, TaskWorker: {getattr(new_task_worker, '__dict__', {})}"
                )
            else:
                self._reset_task_worker_state(task_id=task_id)
                logger.warning(f"TaskId {task_id} already exists, state reset.")

    def _reset_task_worker_state(self, task_id: str) -> None:
        """
        Reset the heartbeat and exception state for a TaskWorker in Redis.

        Args:
            task_id: The ID of the task worker.
        """
        self.redis_proxy.set_message(RedisKey.task_heartbeat(task_id=task_id), secrets.randbelow(200))
        self.redis_proxy.set_message(RedisKey.task_exception(task_id=task_id), "")

    def _ensure_task_can_be_processed(self, task: Optional[Task], task_id: str) -> bool:
        """
        Ensure the task is valid and can be processed.

        Args:
            task: The Task object.
            task_id: The ID of the task.

        Returns:
            True if the task can be processed, False otherwise.
        """
        if task is None:
            logger.warning(f"TaskId {task_id} does not exist.")
            return False
        if task.class_name not in TaskWorkerFactory.get_all_task_worker_class_names():
            logger.warning(
                f"Task({task_id})'s type ({task.class_name}) is not in {TaskWorkerFactory.get_all_task_worker_class_names()}"
            )
            return False
        if task.executor != SystemConfig.SKALD_ID:
            logger.warning(
                f"Task({task_id})'s executor ({task.executor}) is not {SystemConfig.SKALD_ID}"
            )
            return False
        return True

    # -------------------
    # Task Cancellation
    # -------------------
    def _cancel_task_worker(self, message: str) -> None:
        """
        Cancel TaskWorkers based on a TaskEvent message.

        Args:
            message: JSON string representing a TaskEvent.
        """
        task_event = TaskEvent(json_str=message)
        for task_id in task_event.taskIds:
            if task_id in TaskWorkerStore.all_task_worker_task_id():
                TaskWorkerStore.terminate_task_by_task_id(task_id)
                logger.success(f"TaskWorker canceled. TaskId: {task_id}")
            else:
                logger.warning(f"TaskId {task_id} does not exist.")

    # -------------------
    # Task Update
    # -------------------
    def _update_task_worker(self, message: str) -> None:
        """
        Update TaskWorkers based on a TaskEvent message.

        Args:
            message: JSON string representing a TaskEvent.
        """
        task_event = TaskEvent(json_str=message)
        logger.info(f"Update task worker event: {task_event}")
        for task_id in task_event.taskIds:
            if task_id in TaskWorkerStore.all_task_worker_task_id():
                task = self.task_repository.get_task_by_task_id(id=task_id)
                if not self._ensure_task_can_be_processed(task=task, task_id=task_id):
                    continue
                self._update_task_worker_strategy(task=task)
            else:
                logger.warning(f"TaskId {task_id} does not exist.")

    def _update_task_worker_strategy(self, task: Task) -> None:
        """
        Send an update event for a TaskWorker via Kafka.

        Args:
            task: The Task object to update.
        """
        try:
            update_task_event = UpdateTaskWorkerEvent(attachments=task.attachments)
            if update_task_event is not None:
                self.kafka_proxy.producer.send(
                    KafkaTopic.TaskWorkerUpdate,
                    value=update_task_event.model_dump_json().encode('utf-8'),
                    key=task.id
                )
                self.kafka_proxy.producer.flush()
                logger.success(
                    f"TaskWorker updating. TaskId: {task.id}, TaskWorker: {update_task_event.model_dump_json(indent=2)}"
                )
        except Exception as e:
            logger.error(f"Error updating {task.class_name} TaskWorker: {e}")

    def _testing_kafka_producer(self, message: str) -> None:
        """Test Kafka producer by logging the received message."""
        logger.info(f"Kafka producer test message: {message}")

    # -------------------
    # Kafka Consumer Loop
    # -------------------
    def _kafka_consume_func(self) -> None:
        """Kafka consumer loop for handling task events."""
        while True:
            try:
                for message in self.kafka_proxy.consumer:
                    logger.info(
                        # "Received Kafka message: %s:%d:%d: key=%s value=%s",
                        # message.topic, message.partition, message.offset,
                        # message.key, message.value.decode('utf-8')
                        f"Received Kafka message: {message.topic}:{message.partition}:{message.offset}: key={message.key.decode('utf-8')}, value={message.value.decode('utf-8') if message.value else None}"
                    )
                    try:
                        if message.topic == KafkaTopic.TASK_ASSIGN:
                            self._create_task_worker(message.value.decode('utf-8'))
                        elif message.topic == KafkaTopic.TASK_CANCEL:
                            self._cancel_task_worker(message.value.decode('utf-8'))
                        elif message.topic == KafkaTopic.TASK_UPDATE_ATTACHMENT:
                            self._update_task_worker(message.value.decode('utf-8'))
                        elif message.topic == KafkaTopic.TESTING_PRODUCER:
                            self._testing_kafka_producer(message.value.decode('utf-8'))
                        else:
                            logger.warning(f"Unknown Kafka topic: {message.topic}")
                    except Exception as e:
                        logger.error(f"Error processing Kafka message: {e}")
            except TypeError as te:
                logger.debug(f"Kafka Client not created yet, message: {te}")
            except Exception as e:
                logger.error(f"Kafka consumer disconnected, retrying in 5s. Error: {e}")
            finally:
                time.sleep(5)

    # -------------------
    # Redis Sync
    # -------------------
    def stop_sync_all_taskworker_to_redis(self) -> None:
        """Stop the background thread that syncs all TaskWorkerSimpleMap to Redis."""
        self._is_sync_all_taskworker_to_redis_flag = False
        if self._async_all_taskworker_to_redis_thread is not None:
            self._async_all_taskworker_to_redis_thread.join()
            self._async_all_taskworker_to_redis_thread = None
            self.task_worker_simple_map_list.clear()
            self.redis_proxy.set_message(
                RedisKey.skald_all_task(SystemConfig.SKALD_ID),
                self.task_worker_simple_map_list.model_dump_json()
            )
        else:
            logger.warning("Sync All TaskWorkerSimpleMap is already stopped.")

    def _start_sync_all_taskworker_to_redis(self) -> None:
        """Start the background thread that syncs all TaskWorkerSimpleMap to Redis."""
        def run_async_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._sync_all_skald_info_to_redis())
            loop.close()

        if self._async_all_taskworker_to_redis_thread is None and not self._is_sync_all_taskworker_to_redis_flag:
            self._is_sync_all_taskworker_to_redis_flag = True
            self._async_all_taskworker_to_redis_thread = threading.Thread(
                target=run_async_in_thread, daemon=True
            )
            self._async_all_taskworker_to_redis_thread.start()
        else:
            logger.warning("Sync All TaskWorkerSimpleMap is already running.")
    # _sync_all_taskworker_and_allow_task_class_name_to_redis
    async def _sync_all_skald_info_to_redis(self) -> None: # all taskworkers, allow task class names, skald mode
        """
        Periodically sync all TaskWorkerSimpleMap and allowed task class names to Redis.
        """
        while self._is_sync_all_taskworker_to_redis_flag:
            self.task_worker_simple_map_list.keep_specify_tasks(TaskWorkerStore.all_task_worker_task_id())
            self.redis_proxy.set_message(
                RedisKey.skald_all_task(SystemConfig.SKALD_ID),
                self.task_worker_simple_map_list.model_dump_json(),
                0,
                SystemConfig.REDIS_KEY_TTL
            )
            allow_task_class_name = TaskWorkerFactory.get_all_task_worker_class_names()
            self.redis_proxy.overwrite_list(
                RedisKey.skald_allow_task_class_name(SystemConfig.SKALD_ID),
                allow_task_class_name,
                SystemConfig.REDIS_KEY_TTL
            )
            await asyncio.sleep(SystemConfig.REDIS_SYNC_PERIOD)
        logger.info("Sync All TaskWorkerSimpleMap done!")
