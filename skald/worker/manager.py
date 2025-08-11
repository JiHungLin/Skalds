import asyncio
import datetime
import secrets
import time
from entity.task.event import TaskEvent, UpdateTaskWorkerEvent
from entity.task.repository import TaskRepository
from entity.task.task import ModeEnum, Task, TaskUnitClassNameEnum, TaskWorkerSimpleMapList, VideoInfo
from proxy.kafka import KafkaConfig, KafkaProxy, KafkaTopic
from ruamel.yaml import YAML
from proxy.mongo import MongoProxy
from threading import Thread
from log import logger
from proxy.redis import RedisConfig, RedisKey, RedisProxy
from store.taskworker import TaskWorkerStore
from config.systemconfig import SystemConfig
from taskworker.baseclass import BaseTaskWorkerV1
from taskworker.factory import TaskWorkerFactory
import threading

class TaskWorkerManager:
    def __init__(self, kafka_proxy: KafkaProxy, redis_proxy: RedisProxy,mongo_proxy: MongoProxy) -> None:
        self.kafka_proxy = kafka_proxy
        self.redis_proxy = redis_proxy
        self.mongo_proxy = mongo_proxy
        self.__kafka_consume_thread = None
        logger.info("TaskWorkerManager init")
        # Entity Repository
        self.task_repository = TaskRepository(mongo_proxy=self.mongo_proxy)

        # All Config
        self.redis_config = RedisConfig(
                                                host=SystemConfig.REDIS_HOST, 
                                                port=SystemConfig.REDIS_PORT,
                                                password=SystemConfig.REDIS_PASSWORD
                                            )
        self.kafka_config = KafkaConfig(
                                                host=SystemConfig.KAFKA_HOST, 
                                                port=SystemConfig.KAFKA_PORT ,
                                                username=SystemConfig.KAFKA_USERNAME,
                                                password=SystemConfig.KAFKA_PASSWORD
                                            )
        
        # self.kafka_admin_client = KafkaAdmin(self.kafka_config)

        # TaskWorkerFactory
        self.task_worker_factory = TaskWorkerFactory(redis_config=self.redis_config, kafka_config=self.kafka_config)

        # TaskWorkerSimpleList
        self.task_worker_simple_map_list = TaskWorkerSimpleMapList()
        self.__is_sync_all_taskworker_to_redis_flag = False
        self.__async_all_taskworker_to_redis_thread = None
        self.__start_sync_all_taskworker_to_redis()

            
    def start_kafka_consume(self):
        if self.__kafka_consume_thread is None:
            self.__kafka_consume_thread = Thread(target=self.__kafka_consume_func, daemon=True)
            self.__kafka_consume_thread.start()
            logger.success("start kafka consume")
        else:
            logger.warning("kafka consume already started")

    def stop_kafka_consume(self):
        logger.warning("Kafka consume don't support stop function")


    # # # # # # # # # #
    # Load From YAML  #
    # # # # # # # # # #
    def load_taskworker_from_yaml(self, yaml_file: str):
        config = {}
        yaml = YAML(typ="safe")
        yaml.default_flow_style = False

        with open(yaml_file, 'r') as f:
            config = yaml.load(f)
        
        if config and config["TaskWorkers"]:
            for key, value in config["TaskWorkers"].items():
                task_id = key
                task: Task = None
                task_worker: BaseTaskWorkerV1 = None
                attachments = value.get('attachments', {})
                camera_id: str = attachments.get('cameraId', None)
                if camera_id is None:
                    logger.warning(f"TaskWorkerManager: Task {key} has no cameraId in attachments, skip register task worker.")
                    continue
                
                try:
                    remote_task = self.task_repository.get_task_by_task_id(id=task_id)
                    if remote_task is not None:
                        # If task already exist, update task attachments
                        value['attachments'] = remote_task.attachments
                        attachments_obj = type('AttachmentsObject', (), {})()
                        if value['attachments'] is not None:
                            for k, v in value['attachments'].items():
                                setattr(attachments_obj, k, v)
                        logger.info(f"TaskWorkerManager: Task {task_id} already exist, update task attachments from MongoDB.")
                        task = Task(
                            id=task_id,
                            name=task_id,
                            className=value['className'],
                            description="Active TaskWorker from MongoDB. ClassName: " + value['className'],
                            source="YAML",
                            executor=SystemConfig.SLAVE_ID,
                            mode=ModeEnum.ACTIVE,
                            createDateTime=remote_task.createDateTime,
                            updateDateTime=datetime.datetime.now().timestamp(),
                            deadlineDateTime=remote_task.deadlineDateTime,
                            lifecycleStatus=remote_task.lifecycleStatus,
                            priority=remote_task.priority,
                            attachments=attachments_obj
                        )
                        self.task_repository.update_executor(id=task_id, executor=SystemConfig.SLAVE_ID)
                    else:
                        attachments_obj = type('AttachmentsObject', (), {})()
                        for k, v in attachments.items():
                            setattr(attachments_obj, k, v)
                        task = Task(
                            id=task_id,
                            name=task_id,
                            className=value['className'],
                            description="Active TaskWorker from YAML. ClassName: " + value['className'],
                            source="YAML",
                            executor=SystemConfig.SLAVE_ID,
                            mode=ModeEnum.ACTIVE,
                            createDateTime=datetime.datetime.now().timestamp(),
                            updateDateTime=datetime.datetime.now().timestamp(),
                            deadlineDateTime=0,
                            lifecycleStatus="Active",
                            priority=0,
                            attachments=attachments_obj
                        )
                        task_mongo = Task(

                            id=task_id,
                            name=task_id,
                            className=value['className'],
                            description="Active TaskWorker from YAML. ClassName: " + value['className'],
                            source="YAML",
                            executor=SystemConfig.SLAVE_ID,
                            mode=ModeEnum.ACTIVE,
                            createDateTime=datetime.datetime.now().timestamp(),
                            updateDateTime=datetime.datetime.now().timestamp(),
                            deadlineDateTime=0,
                            lifecycleStatus="Active",
                            priority=0,
                            attachments=attachments
                        )
                        self.task_repository.create_task(task=task_mongo)
                        logger.info(f"TaskWorkerManager: Task {task_id} not exist, create new task.")

                except Exception as e:
                    logger.error(f"TaskWorkerManager: Task {task_id} get from MongoDB error or implement error: {e}")
                    attachments_obj = type('AttachmentsObject', (), {})()
                    for k, v in attachments.items():
                        setattr(attachments_obj, k, v)
                    task = Task(
                            id=task_id,
                            name=task_id,
                            className=value['className'],
                            description="Active TaskWorker from YAML. ClassName: " + value['className'],
                            source="YAML",
                            executor=SystemConfig.SLAVE_ID,
                            mode=ModeEnum.ACTIVE,
                            createDateTime=datetime.datetime.now().timestamp(),
                            updateDateTime=datetime.datetime.now().timestamp(),
                            deadlineDateTime=0,
                            lifecycleStatus="Active",
                            priority=0,
                            attachments=attachments_obj
                        )
                finally:
                    task_worker = self.task_worker_factory.create_task_worker(task=task)
                    if camera_id is not None and task_worker is not None:
                        TaskWorkerStore.register_task_with_camera_id_and_start(task_id=task_id, process=task_worker, camera_id=camera_id)
                        self.task_worker_simple_map_list.push(task_id=task_id, task_type=TaskUnitClassNameEnum(task.className))
                        logger.success(f'New TaskWorker created from YAML. TaskId: {task_id}, ProcessId: {task_worker.pid}, TaskWorker: {task_worker.__dict__}')
                    else:
                        logger.warning(f"TaskWorkerManager: Task {task_id} has no cameraId in attachments, or get a None taskworker. Skip register task worker.")

        with open("new_launch.yaml", 'w') as f:
            yaml.dump(config, f)

    # # # # # # # #
    # Create Task #
    # # # # # # # #

    def __create_task_worker(self, message: str):
        task_event = TaskEvent(json_str=message)
        for i in task_event.taskIds:
            if i not in TaskWorkerStore.all_task_worker_task_id():
                task = self.task_repository.get_task_by_task_id(id=i)
                if not  self.__ensure_task_can_be_process(task=task, id=i):
                    continue
                new_task_worker = self.task_worker_factory.create_task_worker(task=task)
                if new_task_worker is None: # If can't create TaskWorker, skip
                    logger.error(f"Create TaskWorker failed. Task: {task.to_json(pretty=True)}")
                    continue
                else:
                    # TaskWorkerStore.register_task_and_start(task_id=i, process=new_task_worker)
                    TaskWorkerStore.register_task_with_camera_id_and_start(task_id=i, process=new_task_worker, camera_id=task.attachments.cameraId)
                    self.task_worker_simple_map_list.push(task_id=i, task_type=TaskUnitClassNameEnum(task.className))
                    # self.kafka_admin_client.create_topic(topic_name=KafkaTopic.TaskNotifyProcessUpdate(task_id=i))
                    logger.success(f'New TaskWorker created. TaskId: {i}, ProcessId: {new_task_worker.pid}, TaskWorker: {new_task_worker.__dict__}')
            else:
                self.__reset_task_worker_state(task_id=i)
                logger.warning(f"TaskWorkerManager: TaskId {i} already exist, Already reset TaskWorker State.")

    def __reset_task_worker_state(self, task_id: str):
        self.redis_proxy.set_message(RedisKey.TaskHeartbeat_key(task_id=task_id), secrets.randbelow(200))
        self.redis_proxy.set_message(RedisKey.TaskException_key(task_id=task_id), "")

    def __ensure_task_can_be_process(self, task: Task, id: str):
        if task is None:
            logger.warning(f"TaskWorkerManager: TaskId {id} doesn't exist")
            return False
        elif task.className not in TaskUnitClassNameEnum.list():
            logger.warning(f"TaskWorkerManager: Task({id})'s type ({task.className}) is not in TaskUnitClassNameEnum")
            return False
        elif task.executor != SystemConfig.SLAVE_ID:
            logger.warning(f"TaskWorkerManager: Task({id})'s executor ({task.executor}) is not {SystemConfig.SLAVE_ID}")
            return False
        else:
            return True

    # # # # # # # #
    # Cancel Task #
    # # # # # # # #

    def __cancel_task_worker(self, message: str):
        task_event = TaskEvent(json_str=message)
        for i in task_event.taskIds:
            if i in TaskWorkerStore.all_task_worker_task_id():
                # TaskWorkerStore.terminate_all_task()
                task_id = i
                TaskWorkerStore.terminate_task_by_task_id(task_id)
                logger.success(f'TaskWorker canceled. TaskId: {task_id}')
            else:
                logger.warning(f"TaskWorkerManager: TaskId {i} doesn't exist")
    
    # # # # # # # #
    # Update Task #
    # # # # # # # #

    def __update_task_worker(self, message: str):
        task_event = TaskEvent(json_str=message)
        logger.info(f"Update task worker. {task_event}")
        for i in task_event.taskIds:
            if i in TaskWorkerStore.all_task_worker_task_id():
                task = self.task_repository.get_task_by_task_id(id=i)
                if not  self.__ensure_task_can_be_process(task=task, id=i):
                    continue
                self.__update_task_worker_strategy(task=task)
            else:
                logger.warning(f"TaskWorkerManager: TaskId {i} doesn't exist")

    def __update_task_worker_strategy(self, task: Task):
        update_task_event = None
        try:
            if task.className == TaskUnitClassNameEnum.VideoStreamSettings.value:
                update_task_event = UpdateTaskWorkerEvent(task=task)
            
            if update_task_event is not None:
                self.kafka_proxy.producer.send(KafkaTopic.TaskWorkerUpdate, value=update_task_event.to_json().encode('utf-8'), key=task.id)
                self.kafka_proxy.producer.flush()
                logger.success(f'TaskWorker updating. TaskId: {task.id}, TaskWorker: {update_task_event.to_json(pretty=True)}')
        except Exception as e:
            logger.error(f"Update {task.className} Task Worker Error: {e}")

    def __testing_kafka_producer(self, message: str):
        logger.info(f"Kafka producer is working fine. Got message: {message}")


    # # # # # # # # #
    # Kafka Consumer #
    # # # # # # # # #

    def __kafka_consume_func(self):
        while True:
            try:
                for message in self.kafka_proxy.consumer:
                    logger.info("Get kafka message: %s:%d:%d: key=%s value=%s" % (message.topic, message.partition,
                                                message.offset, message.key,
                                                message.value.decode('utf-8')))
                    try:
                        if message.topic == KafkaTopic.TaskAssign:
                            self.__create_task_worker(message.value.decode('utf-8'))
                        elif message.topic == KafkaTopic.TaskCancel:
                            self.__cancel_task_worker(message.value.decode('utf-8'))
                        elif message.topic == KafkaTopic.TaskUpdateAttachment:
                            self.__update_task_worker(message.value.decode('utf-8'))
                        elif message.topic == KafkaTopic.TestingProducer:
                            self.__testing_kafka_producer(message.value.decode('utf-8'))
                        else:
                            logger.warning("Unknown topic: %s" % message.topic)
                    except Exception as e:
                        logger.error(f"Kafka consume error: {str(e)}")
            except Exception as e:
                logger.error(f"Kafka consumer might disconnected, try to reconnect later. Error: {str(e)}")
                time.sleep(5)
                
    # # # # # # # #
    # Redis Sync #
    # # # # # # # #

    def stop_sync_all_taskworker_to_redis(self):
        self.__is_sync_all_taskworker_to_redis_flag = False
        if self.__async_all_taskworker_to_redis_thread != None:
            self.__async_all_taskworker_to_redis_thread.join()
            self.__async_all_taskworker_to_redis_thread = None
            self.task_worker_simple_map_list.clear()
            self.redis_proxy.set_message(RedisKey.SlaveAllTask_key(SystemConfig.SLAVE_ID), self.task_worker_simple_map_list.to_json())
        else:
            logger.warning("Sync All TaskWorkerSimpleMap is already stopped!")

    def __start_sync_all_taskworker_to_redis(self):

        def run_async_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.__sync_all_taskworker_to_redis())
            loop.close()

        if self.__async_all_taskworker_to_redis_thread == None and not self.__is_sync_all_taskworker_to_redis_flag:
            self.__is_sync_all_taskworker_to_redis_flag = True
            self.__async_all_taskworker_to_redis_thread = threading.Thread(target=run_async_in_thread, daemon=True)
            self.__async_all_taskworker_to_redis_thread.start()
        else:
            logger.warning("Sync All TaskWorkerSimpleMap is already running!")

    # Sync All TaskWorkerSimpleMap to Redis
    async def __sync_all_taskworker_to_redis(self):
        while self.__is_sync_all_taskworker_to_redis_flag:
            self.task_worker_simple_map_list.keep_specify_tasks(TaskWorkerStore.all_task_worker_task_id())
            self.redis_proxy.set_message(RedisKey.SlaveAllTask_key(SystemConfig.SLAVE_ID), self.task_worker_simple_map_list.to_json())
            await asyncio.sleep(SystemConfig.REDIS_SYNC_PERIOD)
        logger.info("Sync All TaskWorkerSimpleMap done!")
