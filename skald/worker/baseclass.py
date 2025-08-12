"""
Base classes for Skald task workers with extensible lifecycle hooks.

This module provides abstract and concrete base classes for task workers that
run as separate processes, handle signals, and integrate with Kafka and Redis
for messaging and heartbeat monitoring.

Developers can extend the lifecycle hooks (_run_before, _run_main, _run_after, _release)
by registering custom handlers using the provided decorators.

Classes:
    TaskWorkerConfig: Configuration for task worker mode.
    AbstractTaskWorker: Abstract base class for task worker processes.
    BaseTaskWorker: Concrete base class for task workers with Kafka/Redis integration.

Decorators:
    run_before_handler: Register a custom handler to run before the main logic.
    run_main_handler: Register a custom handler for the main logic.
    run_after_handler: Register a custom handler to run after the main logic.
    release_handler: Register a custom handler for resource release.
"""

import multiprocessing as mp
import sys
import threading
import time
import uuid
from abc import ABC, abstractmethod
from functools import partial
from signal import SIGINT, SIGTERM, signal
from typing import Any, Callable, Optional, TypeVar, Generic

from kafka.consumer.fetcher import ConsumerRecord
from pydantic import BaseModel
from skald.model.task import Task
from skald.handler.survive import SurviveHandler, SurviveRoleEnum
from skald.utils.logging import logger
from skald.proxy.kafka import KafkaConfig, KafkaProxy, KafkaTopic
from skald.proxy.redis import RedisConfig, RedisKey, RedisProxy
from skald.store.taskworker import TaskWorkerStore
from skald.model.event import UpdateTaskWorkerEvent

# --- Decorator registration mechanism for lifecycle hooks ---
def _lifecycle_handler_decorator(attr_name: str):
    """
    Factory for lifecycle hook decorators. Registers the decorated function
    as a handler for the specified lifecycle event on the class.
    """
    def decorator(func: Callable):
        setattr(func, "_skald_lifecycle_hook", attr_name)
        return func
    return decorator

run_before_handler = _lifecycle_handler_decorator("_custom_run_before")
run_main_handler   = _lifecycle_handler_decorator("_custom_run_main")
run_after_handler  = _lifecycle_handler_decorator("_custom_run_after")
release_handler    = _lifecycle_handler_decorator("_custom_release")
update_event_handler = _lifecycle_handler_decorator("_custom_update_event")


class TaskWorkerConfig:
    """
    Configuration for task worker mode.

    Attributes:
        mode (str): The mode of the worker. Default is "node".
    """
    mode: str = "node"

T = TypeVar('T', bound=BaseModel)
class AbstractTaskWorker(mp.Process, ABC, Generic[T]):
    """
    Abstract base class for task worker processes with extensible lifecycle hooks.

    Handles process lifecycle, signal handling, and defines the required
    interface for concrete task workers. Supports custom lifecycle hooks via decorators.
    """

    def __init__(self) -> None:
        super().__init__()
        self.is_done: bool = False
        # Discover and register custom lifecycle handlers
        self._register_lifecycle_hooks()
    

    @abstractmethod
    def initialize(self, data: T) -> None:
        """
        Initialize the task worker with the provided data.

        Args:
            data: The data to initialize the task worker.
        """
        pass

    @classmethod
    def get_data_model(cls) -> BaseModel:
        return cls.__orig_bases__[0].__args__[0]

    def _register_lifecycle_hooks(self) -> None:
        """
        Scans the instance for methods decorated as lifecycle hooks and registers them.
        """
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, "_skald_lifecycle_hook"):
                hook_name = getattr(attr, "_skald_lifecycle_hook")
                setattr(self, hook_name, attr)

    def _call_lifecycle(self, base_method: Callable, custom_attr: str, *args, **kwargs) -> None:
        """
        Calls the custom handler for a lifecycle event if registered, then the base method.
        For _run_main, only the custom handler is called (never call the abstract base _run_main).
        """
        custom_handler = getattr(self, custom_attr, None)
        if custom_attr == "_custom_run_main":
            if callable(custom_handler):
                try:
                    logger.debug(f"Calling custom handler: {custom_attr} (replaces base _run_main)")
                    custom_handler(*args, **kwargs)
                except Exception as exc:
                    logger.error(f"Exception in custom {custom_attr}: {exc}", exc_info=True)
            else:
                raise NotImplementedError("No custom run_main handler registered.")
        else:
            if callable(custom_handler):
                try:
                    logger.debug(f"Calling custom handler: {custom_attr}")
                    custom_handler(*args, **kwargs)
                except Exception as exc:
                    logger.error(f"Exception in custom {custom_attr}: {exc}", exc_info=True)
            # Always call the base method
            base_method(*args, **kwargs)

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
            self._call_lifecycle(self._release, "_custom_release", *args)
        sys.exit(0)

    def run(self) -> None:
        """
        Entry point for the process. Handles setup, main logic, and cleanup.
        """
        self.daemon = True  # Ensure this process is killed if the parent dies
        signal(SIGTERM, partial(self._release_and_exit))
        signal(SIGINT, partial(self._release_and_exit))
        try:
            self._call_lifecycle(self._run_before, "_custom_run_before")
            self._call_lifecycle(self._run_main, "_custom_run_main")
            self._call_lifecycle(self._run_after, "_custom_run_after")
        except Exception as exc:
            self._error_handler(exc)
        except BaseException:
            logger.warning("Unexpected error! Forcing exit.")
        finally:
            logger.info("Leaving subprocess.")
            self._release_and_exit()



class BaseTaskWorker(AbstractTaskWorker, Generic[T]):
    """
    Base implementation of a task worker with Kafka and Redis integration.

    Handles Kafka topic consumption, Redis heartbeat, and error reporting.
    Supports custom lifecycle hooks via decorators.
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

        If a user-defined handler is registered via @update_event_handler,
        it will be called instead of the default implementation.

        Args:
            message (ConsumerRecord): The Kafka message.
        """
        # logger.info(f"Received message: {message}")
        logger.info("Get kafka message: %s:%d:%d: key=%s value=%s" % (message.topic, message.partition,
            message.offset, message.key,
            message.value.decode('utf-8')))
        if message.key.decode('utf-8') != self.task_id:
            pass
        else:
            data = UpdateTaskWorkerEvent.model_validate_json(message.value.decode('utf-8'))
            custom_handler = getattr(self, "_custom_update_event", None)
            if callable(custom_handler):
                try:
                    custom_handler(data)
                except Exception as exc:
                    logger.error(f"Exception in custom update_event_handler: {exc}", exc_info=True)
                return

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
