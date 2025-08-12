"""
Base classes for Skald task workers.

This module provides abstract and concrete base classes for task workers that
run as separate processes, handle signals, and integrate with Kafka and Redis
for messaging and heartbeat monitoring.

Classes:
    TaskWorkerConfig: Configuration for task worker mode.
    AbstractTaskWorker: Abstract base class for task worker processes.
    BaseTaskWorkerV1: Concrete base class for task workers with Kafka/Redis integration.
"""

import multiprocessing as mp
import sys
import threading
import time
import uuid
from abc import ABC, abstractmethod
from functools import partial
from signal import SIGINT, SIGTERM, signal
from typing import Any, Optional

from kafka.consumer.fetcher import ConsumerRecord
from skald.model.task import Task
from skald.handler.survive import SurviveHandler, SurviveRoleEnum
from skald.utils.logging import logger
from skald.proxy.kafka import KafkaConfig, KafkaProxy, KafkaTopic
from skald.proxy.redis import RedisConfig, RedisKey, RedisProxy
from skald.store.taskworker import TaskWorkerStore


class TaskWorkerConfig:
    """
    Configuration for task worker mode.

    Attributes:
        mode (str): The mode of the worker. Default is "node".
    """
    mode: str = "node"


class AbstractTaskWorker(mp.Process, ABC):
    """
    Abstract base class for task worker processes.

    Handles process lifecycle, signal handling, and defines the required
    interface for concrete task workers.
    """

    def __init__(self) -> None:
        super().__init__()
        self.is_done: bool = False

    @abstractmethod
    def _release(self, *args: Any) -> None:
        """
        Release resources when the task is shutting down.
        """
        pass

    @abstractmethod
    def _run_before(self) -> None:
        """
        Initialize resources and connections before running the main task logic.
        """
        pass

    @abstractmethod
    def _run_main(self) -> None:
        """
        The main logic of the task.
        """
        pass

    @abstractmethod
    def _run_after(self) -> None:
        """
        Operations to perform after the task is complete, such as updating status or notifying the server.
        """
        pass

    @abstractmethod
    def _error_handler(self, exc: Exception) -> None:
        """
        Handle exceptions that occur during task execution.

        Args:
            exc (Exception): The exception that was raised.
        """
        pass

    def _release_and_exit(self, *args: Any) -> None:
        """
        Internal method to release resources and exit the process.

        Args:
            *args: Signal number and stack frame (from signal handler).
        """
        if not self.is_done:
            self.is_done = True
            self._release(*args)
        sys.exit(0)

    def run(self) -> None:
        """
        Entry point for the process. Handles setup, main logic, and cleanup.
        """
        self.daemon = True  # Ensure this process is killed if the parent dies
        signal(SIGTERM, partial(self._release_and_exit))
        signal(SIGINT, partial(self._release_and_exit))
        try:
            self._run_before()
            self._run_main()
            self._run_after()
        except Exception as exc:
            self._error_handler(exc)
        except BaseException:
            logger.warning("Unexpected error! Forcing exit.")
        finally:
            logger.info("Leaving subprocess.")
            self._release_and_exit()


class BaseTaskWorkerV1(AbstractTaskWorker):
    """
    Base implementation of a task worker with Kafka and Redis integration.

    Handles Kafka topic consumption, Redis heartbeat, and error reporting.
    """

    def __init__(
        self,
        task: Task,
        redis_config: Optional[RedisConfig] = None,
        kafka_config: Optional[KafkaConfig] = None,
    ) -> None:
        """
        Initialize the task worker.

        Args:
            task (Task): The task to be processed.
            redis_config (Optional[RedisConfig]): Redis connection configuration.
            kafka_config (Optional[KafkaConfig]): Kafka connection configuration.
        """
        super().__init__()
        self.task_id: str = task.id
        self.task_type: str = task.className
        self._redis_config: RedisConfig = redis_config or RedisConfig()
        self._kafka_config: KafkaConfig = kafka_config or KafkaConfig()
        self._redis_proxy: Optional[RedisProxy] = None
        self._kafka_proxy: Optional[KafkaProxy] = None
        self._survive_handler: Optional[SurviveHandler] = None
        self._update_consume_thread: Optional[threading.Thread] = None

    def _consume_update_messages(self) -> None:
        """
        Thread target for consuming update messages from Kafka.
        """
        while True:
            try:
                for message in self._kafka_proxy.consumer:
                    self.handle_update_message(message)
            except Exception as exc:
                logger.error(
                    f"Kafka consumer might be disconnected, will retry. Error: {exc}"
                )
                time.sleep(5)

    def handle_update_message(self, message: ConsumerRecord) -> None:
        """
        Handle a single update message from Kafka.

        Args:
            message (ConsumerRecord): The Kafka message.
        """
        logger.info(f"Received message: {message}")

    def _run_before(self) -> None:
        """
        Initialize Kafka and Redis connections, start heartbeat and message consumption.
        """
        if self._kafka_config is not None:
            # Set Kafka topic and group
            self._kafka_config.consume_topic_list = [KafkaTopic.TaskWorkerUpdate]
            self._kafka_config.consume_group_id = f"{self.task_id}_{str(uuid.uuid4())[:5]}"
            self._kafka_proxy = KafkaProxy(
                kafka_config=self._kafka_config,
                is_block=TaskWorkerConfig.mode == "node"
            )
            self._update_consume_thread = threading.Thread(
                target=self._consume_update_messages,
                daemon=True
            )
            self._update_consume_thread.start()

        if self._redis_config is not None:
            self._redis_proxy = RedisProxy(
                redis_config=self._redis_config,
                is_block=TaskWorkerConfig.mode == "node"
            )
            self._survive_handler = SurviveHandler(
                redis_proxy=self._redis_proxy,
                key=RedisKey.TaskHeartbeat_key(self.task_id),
                role=SurviveRoleEnum.TASKWORKER.value
            )
            self._survive_handler.start_heartbeat_update()
            # Clear any previous exception state
            self._redis_proxy.set_message(
                key=RedisKey.TaskException_key(self.task_id),
                message=""
            )

    def _run_after(self) -> None:
        """
        Stop heartbeat and mark task as completed in Redis.
        """
        if self._redis_proxy and self._survive_handler:
            self._survive_handler.stop_heartbeat_update()
            if not self.is_done:
                self._survive_handler.push_success_heartbeat()
        logger.success(f"Task Worker {self.task_id} is done.")

    def _error_handler(self, exc: Exception) -> None:
        """
        Handle errors by stopping heartbeat and reporting failure in Redis.

        Args:
            exc (Exception): The exception that was raised.
        """
        if self._survive_handler:
            self._survive_handler.stop_heartbeat_update()
        if self._redis_proxy:
            self._redis_proxy.set_message(
                key=RedisKey.TaskException_key(self.task_id),
                message=str(exc)
            )
        if self._survive_handler:
            self._survive_handler.push_failed_heartbeat()
        logger.error(f"Task Worker {self.task_id} failed with error: {exc}")

    def _release(self, *args: Any) -> None:
        """
        Release all resources, close connections, and update heartbeat status.

        Args:
            *args: Optional signal number and stack frame.
        """
        try:
            if self._kafka_proxy:
                if self._kafka_proxy.consumer:
                    self._kafka_proxy.consumer.close()
                if self._kafka_proxy.producer:
                    self._kafka_proxy.producer.close()
        except Exception as exc:
            logger.error(
                f"Task Worker {self.task_id}:{self.task_type} failed during Kafka release: {exc}"
            )

        try:
            # Handle signal-based cancellation
            if len(args) >= 2:
                signum = args[0]
                if signum in (SIGINT, SIGTERM) and self._survive_handler:
                    self._survive_handler.stop_heartbeat_update()
                    self._survive_handler.push_canceled_heartbeat()
        except Exception as exc:
            logger.error(
                f"Task Worker {self.task_id}:{self.task_type} received unknown signal: {exc}"
            )

        try:
            TaskWorkerStore.TaskWorkerUidDic.pop(self.task_id, None)
        except Exception as exc:
            logger.warning(f"Task Worker may not exist in store: {exc}")

        logger.info(f"Task Worker {self.task_id} is releasing resources.")
