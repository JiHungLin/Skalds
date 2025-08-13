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
    update_event_handler: Register a custom handler for update events with type T.
"""

import multiprocessing as mp
import sys
import threading
import time
import uuid
from abc import ABC, abstractmethod
from functools import partial
from signal import SIGINT, SIGTERM, signal
from typing import Any, Callable, Optional, TypeVar, Generic, Type, Protocol
import secrets

from kafka.consumer.fetcher import ConsumerRecord
from pydantic import BaseModel
from skald.model.task import Task
from skald.handler.survive import SurviveHandler, SurviveRoleEnum
from skald.utils.logging import logger
from skald.proxy.kafka import KafkaConfig, KafkaProxy, KafkaTopic
from skald.proxy.redis import RedisConfig, RedisKey, RedisProxy
from skald.store.taskworker import TaskWorkerStore
from skald.model.event import UpdateTaskWorkerEvent
from skald.config.systemconfig import SystemConfig


# Type variables for generic constraints
T = TypeVar('T', bound=BaseModel)


class LifecycleHandler(Protocol):
    """Protocol for lifecycle handler functions."""
    
    def __call__(self, *args: Any, **kwargs: Any) -> None:
        """Execute the lifecycle handler."""
        ...


class UpdateEventHandler(Protocol[T]):
    """Protocol for update event handler functions with generic type T."""
    
    def __call__(self, data: T) -> None:
        """
        Handle update event with typed data.
        
        Args:
            data: The update event data of type T.
        """
        ...


def _lifecycle_handler_decorator(attr_name: str) -> Callable[[Callable[..., None]], Callable[..., None]]:
    """
    Factory for lifecycle hook decorators. Registers the decorated function
    as a handler for the specified lifecycle event on the class.
    
    Args:
        attr_name: The attribute name to store the handler under.
        
    Returns:
        A decorator function that marks methods as lifecycle handlers.
    """
    def decorator(func: Callable[..., None]) -> Callable[..., None]:
        setattr(func, "_skald_lifecycle_hook", attr_name)
        return func
    return decorator


def _update_event_handler_decorator(func: Callable[[Any, T], None]) -> Callable[[Any, T], None]:
    """
    Decorator for update event handlers with explicit generic type support.
    
    This decorator marks a method as an update event handler and ensures
    type safety for the generic parameter T from AbstractTaskWorker.
    
    Args:
        func: The handler function that takes (self, data: T) -> None
        
    Returns:
        The decorated function with lifecycle hook metadata.
        
    Example:
        @update_event_handler
        def handle_update(self, data: MyDataModel) -> None:
            # data is properly typed as MyDataModel (the T from AbstractTaskWorker[MyDataModel])
            pass
    """
    setattr(func, "_skald_lifecycle_hook", "_custom_update_event")
    return func


# Lifecycle hook decorators
run_before_handler = _lifecycle_handler_decorator("_custom_run_before")
run_main_handler = _lifecycle_handler_decorator("_custom_run_main")
run_after_handler = _lifecycle_handler_decorator("_custom_run_after")
release_handler = _lifecycle_handler_decorator("_custom_release")
update_event_handler = _update_event_handler_decorator


class TaskWorkerConfig:
    """
    Configuration for task worker mode.

    Attributes:
        mode: The mode of the worker. Default is "node".
    """
    mode: str = "node"


class AbstractTaskWorker(mp.Process, ABC, Generic[T]):
    """
    Abstract base class for task worker processes with extensible lifecycle hooks.

    This class provides a framework for task workers that run as separate processes,
    handle signals gracefully, and support custom lifecycle hooks via decorators.
    
    Type Parameters:
        T: The data model type that extends BaseModel, used for initialization
           and update event handling.
    
    Attributes:
        is_done: Flag indicating whether the worker has completed execution.
    """

    def __init__(self) -> None:
        """Initialize the abstract task worker."""
        super().__init__()
        self.is_done: bool = False
        # Discover and register custom lifecycle handlers
        self._register_lifecycle_hooks()

    @abstractmethod
    def initialize(self, data: T) -> None:
        """
        Initialize the task worker with the provided data.

        Args:
            data: The initialization data of type T.
        """
        pass

    @classmethod
    def get_data_model(cls) -> Type[BaseModel]:
        """
        Get the data model class for this worker.
        
        Returns:
            The BaseModel class used as the generic type parameter T.
            
        Raises:
            IndexError: If the class is not properly parameterized with a generic type.
        """
        try:
            return cls.__orig_bases__[0].__args__[0]  # type: ignore
        except (AttributeError, IndexError) as exc:
            raise TypeError(
                f"Class {cls.__name__} must be parameterized with a BaseModel type"
            ) from exc

    def _register_lifecycle_hooks(self) -> None:
        """
        Scan the instance for methods decorated as lifecycle hooks and register them.
        
        This method discovers all methods that have been decorated with lifecycle
        hook decorators and registers them for execution during the appropriate
        lifecycle phases.
        """
        for attr_name in dir(self):
            try:
                attr = getattr(self, attr_name)
                if callable(attr) and hasattr(attr, "_skald_lifecycle_hook"):
                    hook_name = getattr(attr, "_skald_lifecycle_hook")
                    setattr(self, hook_name, attr)
                    logger.debug(f"Registered lifecycle hook: {hook_name} -> {attr_name}")
            except (ValueError, AttributeError) as exc:
                # Skip attributes that can't be accessed (e.g., multiprocessing attributes before process start)
                logger.debug(f"Skipping attribute {attr_name}: {exc}")
                continue

    def _call_lifecycle(
        self, 
        base_method: Callable[..., None], 
        custom_attr: str, 
        *args: Any, 
        **kwargs: Any
    ) -> None:
        """
        Call the custom handler for a lifecycle event if registered, then the base method.
        
        For _run_main, only the custom handler is called (never call the abstract base _run_main).
        For other lifecycle events, both custom and base methods are called.
        
        Args:
            base_method: The base lifecycle method to call.
            custom_attr: The attribute name of the custom handler.
            *args: Positional arguments to pass to the handlers.
            **kwargs: Keyword arguments to pass to the handlers.
            
        Raises:
            NotImplementedError: If no custom run_main handler is registered.
        """
        custom_handler = getattr(self, custom_attr, None)
        
        if custom_attr == "_custom_run_main":
            if callable(custom_handler):
                try:
                    logger.debug(f"Calling custom handler: {custom_attr} (replaces base _run_main)")
                    custom_handler(*args, **kwargs)
                except Exception as exc:
                    logger.error(f"Exception in custom {custom_attr}: {exc}", exc_info=True)
                    raise
            else:
                raise NotImplementedError("No custom run_main handler registered.")
        else:
            # Call custom handler first if available
            if callable(custom_handler):
                try:
                    logger.debug(f"Calling custom handler: {custom_attr}")
                    custom_handler(*args, **kwargs)
                except Exception as exc:
                    logger.error(f"Exception in custom {custom_attr}: {exc}", exc_info=True)
                    # Continue to base method even if custom handler fails
            
            # Always call the base method for non-main lifecycle events
            try:
                base_method(*args, **kwargs)
            except Exception as exc:
                logger.error(f"Exception in base method {base_method.__name__}: {exc}", exc_info=True)
                raise

    @abstractmethod
    def _release(self, *args: Any) -> None:
        """
        Release resources when the task is shutting down.
        
        Args:
            *args: Optional signal number and stack frame from signal handler.
        """
        pass

    @abstractmethod
    def _run_before(self) -> None:
        """
        Initialize resources and connections before running the main task logic.
        
        This method is called before the main task execution and should handle
        any setup operations such as establishing connections, initializing
        resources, or preparing the environment.
        """
        pass

    def _run_main(self) -> None:
        """
        Execute the main logic of the task.
        
        This method contains the core business logic of the task worker.
        It should be implemented by concrete subclasses or replaced by
        a custom handler registered with @run_main_handler.
        """
        pass

    @abstractmethod
    def _run_after(self) -> None:
        """
        Perform operations after the task is complete.
        
        This method is called after successful completion of the main task
        and should handle cleanup, status updates, or notifications.
        """
        pass

    @abstractmethod
    def _error_handler(self, exc: Exception) -> None:
        """
        Handle exceptions that occur during task execution.

        Args:
            exc: The exception that was raised during task execution.
        """
        pass

    def _release_and_exit(self, *args: Any) -> None:
        """
        Internal method to release resources and exit the process gracefully.

        Args:
            *args: Signal number and stack frame (from signal handler).
        """
        if not self.is_done:
            self.is_done = True
            try:
                self._call_lifecycle(self._release, "_custom_release", *args)
            except Exception as exc:
                logger.error(f"Error during resource release: {exc}", exc_info=True)
        sys.exit(0)

    def run(self) -> None:
        """
        Entry point for the process. Handles setup, main logic, and cleanup.
        
        This method orchestrates the entire lifecycle of the task worker:
        1. Sets up signal handlers for graceful shutdown
        2. Executes the before hook
        3. Executes the main logic
        4. Executes the after hook
        5. Handles any exceptions that occur
        6. Ensures proper cleanup
        """
        self.daemon = True  # Ensure this process is killed if the parent dies
        signal(SIGTERM, partial(self._release_and_exit))
        signal(SIGINT, partial(self._release_and_exit))
        
        try:
            self._call_lifecycle(self._run_before, "_custom_run_before")
            self._call_lifecycle(self._run_main, "_custom_run_main")
            self._call_lifecycle(self._run_after, "_custom_run_after")
        except Exception as exc:
            logger.error(f"Task execution failed: {exc}", exc_info=True)
            self._error_handler(exc)
        except BaseException as exc:
            logger.warning(f"Unexpected error during task execution: {exc}")
        finally:
            logger.info("Leaving subprocess.")
            self._release_and_exit()


class BaseTaskWorker(AbstractTaskWorker[T]):
    """
    Base implementation of a task worker with Kafka and Redis integration.

    This class provides a concrete implementation of AbstractTaskWorker with
    built-in support for Kafka message consumption, Redis heartbeat monitoring,
    and error reporting. It handles the infrastructure concerns while allowing
    subclasses to focus on business logic.
    
    Type Parameters:
        T: The data model type that extends BaseModel.
    
    Attributes:
        task_id: Unique identifier for the task.
        task_type: Class name of the task being processed.
    """

    def __init__(
        self,
        task: Task = None,
        redis_config: Optional[RedisConfig] = None,
        kafka_config: Optional[KafkaConfig] = None,
    ) -> None:
        """
        Initialize the task worker with infrastructure configurations.

        Args:
            task: The task to be processed.
            redis_config: Redis connection configuration. Uses default if None.
            kafka_config: Kafka connection configuration. Uses default if None.
        """
        super().__init__()
        if task is None:
            self.task_id = f"MOCK_TASK_{secrets.token_hex(4)}"
            self.task_type = self.__class__.__name__
        else:
            self.task_id: str = task.id
            self.task_type: str = task.class_name
            self.initialize(task.attachments)
        self._redis_config: RedisConfig = redis_config
        self._kafka_config: KafkaConfig = kafka_config
        self._redis_proxy: Optional[RedisProxy] = None
        self._kafka_proxy: Optional[KafkaProxy] = None
        self._survive_handler: Optional[SurviveHandler] = None
        self._update_consume_thread: Optional[threading.Thread] = None

    def _consume_update_messages(self) -> None:
        """
        Thread target for consuming update messages from Kafka.
        
        This method runs in a separate daemon thread and continuously
        consumes messages from the Kafka topic, handling reconnection
        automatically if the connection is lost.
        """
        while not self.is_done:
            try:
                if self._kafka_proxy and self._kafka_proxy.consumer:
                    for message in self._kafka_proxy.consumer:
                        if self.is_done:
                            break
                        self.handle_update_message(message)
            except TypeError as te:
                logger.debug(f"Kafka Client not created yet, message: {te}")
            except Exception as exc:
                if not self.is_done:
                    logger.error(
                        f"Kafka consumer error, will retry in 5 seconds. Error: {exc}"
                    )
            finally:
                    time.sleep(5)

    def handle_update_message(self, message: ConsumerRecord) -> None:
        """
        Handle a single update message from Kafka.

        If a user-defined handler is registered via @update_event_handler,
        it will be called with the properly typed data. The custom handler
        receives data of type T (the generic parameter of AbstractTaskWorker).

        Args:
            message: The Kafka message containing update event data.
        """
        try:
            logger.info(
                f"Received Kafka message: {message.topic}:{message.partition}:{message.offset}: key={message.key.decode('utf-8')}, value={message.value.decode('utf-8') if message.value else None}"
            )
            
            if not message.key or message.key.decode('utf-8') != self.task_id:
                logger.debug(f"Message key {message.key} does not match task_id {self.task_id}")
                return
            
            if not message.value:
                logger.warning("Received message with empty value")
                return
                
            # Parse the update event
            event_data = UpdateTaskWorkerEvent.model_validate_json(message.value.decode('utf-8'))
            
            # Call custom handler if registered
            custom_handler = getattr(self, "_custom_update_event", None)
            if callable(custom_handler):
                try:
                    # The custom handler expects data of type T, but we have UpdateTaskWorkerEvent
                    # The attachments field should contain the actual T-typed data
                    if event_data.attachments is not None:
                        # Get the expected model type for validation
                        model_type = self.get_data_model()
                        # Validate the attachments data against the expected model type
                        typed_data = model_type.model_validate(event_data.attachments)
                        custom_handler(typed_data)
                    else:
                        logger.warning("Update event has no attachments data")
                except Exception as exc:
                    logger.error(f"Exception in custom update_event_handler: {exc}", exc_info=True)
            else:
                logger.debug("No custom update event handler registered")
                
        except Exception as exc:
            logger.error(f"Error handling update message: {exc}", exc_info=True)

    def _run_before(self) -> None:
        """
        Initialize Kafka and Redis connections, start heartbeat and message consumption.
        
        This method sets up the infrastructure components:
        - Configures and starts Kafka consumer for update messages
        - Initializes Redis connection for heartbeat monitoring
        - Starts background threads for message consumption and heartbeat
        """
        # Initialize Kafka proxy and start message consumption
        if SystemConfig.LOG_SPLIT_WITH_WORKER_ID:
            from skald.utils.logging import init_logger
            logger_name = f"{SystemConfig.SKALD_ID}_{self.task_id}"
            init_logger(
                logger_name=logger_name,
                level=SystemConfig.LOG_LEVEL,
                log_path=SystemConfig.LOG_PATH,
                process_id=SystemConfig.SKALD_ID,
                rotation=SystemConfig.LOG_ROTATION_MB
            )
        if self._kafka_config is not None:
            try:
                # Configure Kafka topic and consumer group
                self._kafka_config.consume_topic_list = [KafkaTopic.TASK_WORKER_UPDATE]
                self._kafka_config.consume_group_id = f"{self.task_id}_{str(uuid.uuid4())[:8]}"
                
                self._kafka_proxy = KafkaProxy(
                    kafka_config=self._kafka_config,
                    is_block=TaskWorkerConfig.mode == "node"
                )
                
                # Start message consumption thread
                self._update_consume_thread = threading.Thread(
                    target=self._consume_update_messages,
                    daemon=True,
                    name=f"kafka-consumer-{self.task_id}"
                )
                self._update_consume_thread.start()
                logger.info(f"Started Kafka consumer thread for task {self.task_id}")
                
            except Exception as exc:
                logger.error(f"Failed to initialize Kafka proxy: {exc}", exc_info=True)
                raise

        # Initialize Redis proxy and start heartbeat monitoring
        if self._redis_config is not None:
            try:
                self._redis_proxy = RedisProxy(
                    redis_config=self._redis_config,
                    is_block=TaskWorkerConfig.mode == "node"
                )
                
                self._survive_handler = SurviveHandler(
                    redis_proxy=self._redis_proxy,
                    key=RedisKey.task_heartbeat(self.task_id),
                    role=SurviveRoleEnum.TASKWORKER
                )
                self._survive_handler.start_heartbeat_update()
                
                # Clear any previous exception state
                self._redis_proxy.set_message(
                    key=RedisKey.task_exception(self.task_id),
                    message=""
                )
                logger.info(f"Started heartbeat monitoring for task {self.task_id}")
                
            except Exception as exc:
                logger.error(f"Failed to initialize Redis proxy: {exc}", exc_info=True)
                raise

    def _run_after(self) -> None:
        """
        Stop heartbeat and mark task as completed in Redis.
        
        This method performs cleanup after successful task completion:
        - Stops the heartbeat monitoring
        - Sends a success heartbeat to indicate completion
        """
        try:
            if self._redis_proxy and self._survive_handler:
                self._survive_handler.stop_heartbeat_update()
                if not self.is_done:
                    self._survive_handler.push_success_heartbeat()
            logger.success(f"Task Worker {self.task_id} completed successfully.")
        except Exception as exc:
            logger.error(f"Error during post-execution cleanup: {exc}", exc_info=True)

    def _error_handler(self, exc: Exception) -> None:
        """
        Handle errors by stopping heartbeat and reporting failure in Redis.

        Args:
            exc: The exception that was raised during task execution.
        """
        try:
            # Stop heartbeat monitoring
            if self._survive_handler:
                self._survive_handler.stop_heartbeat_update()
            
            # Report the error to Redis
            if self._redis_proxy:
                self._redis_proxy.set_message(
                    key=RedisKey.task_exception(self.task_id),
                    message=str(exc)
                )
            
            # Send failure heartbeat
            if self._survive_handler:
                self._survive_handler.push_failed_heartbeat()
                
            logger.error(f"Task Worker {self.task_id} failed with error: {exc}")
            
        except Exception as cleanup_exc:
            logger.error(f"Error during error handling: {cleanup_exc}", exc_info=True)

    def _release(self, *args: Any) -> None:
        """
        Release all resources, close connections, and update heartbeat status.

        Args:
            *args: Optional signal number and stack frame from signal handler.
        """
        # Close Kafka connections
        try:
            if self._kafka_proxy:
                if self._kafka_proxy.consumer:
                    self._kafka_proxy.consumer.close()
                if self._kafka_proxy.producer:
                    self._kafka_proxy.producer.close()
                logger.debug("Closed Kafka connections")
        except Exception as exc:
            logger.error(
                f"Task Worker {self.task_id}:{self.task_type} failed during Kafka release: {exc}"
            )

        # Handle signal-based cancellation
        try:
            if len(args) >= 2:
                signum = args[0]
                if signum in (SIGINT, SIGTERM) and self._survive_handler:
                    self._survive_handler.stop_heartbeat_update()
                    self._survive_handler.push_canceled_heartbeat()
                    logger.info(f"Task Worker {self.task_id} was canceled by signal {signum}")
        except Exception as exc:
            logger.error(
                f"Task Worker {self.task_id}:{self.task_type} error handling signal: {exc}"
            )

        # Remove from task worker store
        try:
            TaskWorkerStore.TaskWorkerUidDic.pop(self.task_id, None)
            logger.debug(f"Removed task {self.task_id} from worker store")
        except Exception as exc:
            logger.warning(f"Task Worker may not exist in store: {exc}")

        logger.info(f"Task Worker {self.task_id} finished releasing resources.")
