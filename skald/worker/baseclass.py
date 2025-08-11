import multiprocessing as mp
from abc import ABC, abstractmethod
from signal import SIGINT, signal, SIGTERM
import sys
import threading

from kafka.consumer.fetcher import ConsumerRecord
from entity.task import Task
from entity.task.attachment.base_class import BaseAttachment
from entity.task.task import TaskUnitClassNameEnum
from handler.survive import SurviveHandler, SurviveRoleEnum
from log import logger
from proxy.kafka import KafkaConfig, KafkaProxy, KafkaTopic
from proxy.redis import RedisConfig, RedisKey, RedisProxy
from store.taskworker import TaskWorkerStore
import uuid
from functools import partial
import time

class TaskWorkerConfig:
    mode: str = "node"  # 預設為 node 模式

class AbstractTaskWorker(mp.Process, ABC):
    def __init__(self):
        super(AbstractTaskWorker, self).__init__()
        self.is_done = False

    @abstractmethod
    def release(self, *args): # 任務關閉時，釋放資源用
        pass

    @abstractmethod
    def run_before(self): # 任務初始化，建立所需物件及連線
        pass

    @abstractmethod
    def run_main(self): # 任務實際邏輯部份
        pass

    @abstractmethod
    def run_after(self): # 任務結束後所需的結尾操作，更新完成狀態、通知總Server等...
        pass

    @abstractmethod
    def error_handler(self, e: Exception): # 任務例外處裡部份
        pass

    def __release(self, *args): # 任務釋放資源的實際函數，會叫release()及關閉本身Process
        # args will get signal SIGTERM(15) or SIGINT(2) and code line.
        if not self.is_done: # 避免重複釋放資源(若強制關閉Process，會導致重複釋放)
            self.is_done = True # 更改狀態
            self.release(args)
        sys.exit(0) # 結束Process

    def run(self): # 實際Process執行的函式
        self.daemon = True # 依賴於主Process，若主Process關閉，子Process也一起關閉
        signal(SIGTERM, partial(self.__release)) # 註冊Process關閉時，需要呼叫__release函數
        signal(SIGINT, partial(self.__release)) # 註冊Process關閉時，需要呼叫__release函數
        try:
            self.run_before() # 先呼叫run_before，建立所需資源
            self.run_main() # 開始執行任務
            self.run_after() # 結束任務前的結尾操作
        except Exception as e:
            self.error_handler(e) # 例外處裡函數
        except:
            logger.warning("Unexpected error! Force to exit.")
            # 系統強制關閉會出發的Unexpected error，直接觸__release函數
        finally:
            logger.info("Leaving Subprocess")
            self.__release() # 任務最後呼叫釋放資源的函數

class BaseTaskWorkerV1(AbstractTaskWorker): # 基底任務類別
    
    className: TaskUnitClassNameEnum = "BaseTaskWorkerV1" # 任務類別名稱

    def __init__(self, 
                 task: Task[BaseAttachment] = Task[BaseAttachment](), 
                 redis_config: RedisConfig = RedisConfig(), # Redis 連線參數
                 kafka_config: KafkaConfig = KafkaConfig()  # Kafka 連線參數
                 ):
        super(BaseTaskWorkerV1, self).__init__()
        ## 初始化需要變數
        self.task_id = task.id
        self.task_type = task.className
        self.redis_config = redis_config
        self.kafka_config = kafka_config
        self.redis_proxy: RedisProxy = None
        self.kafka_proxy: KafkaProxy = None
        self.survive_handler: SurviveHandler = None
        self.update_consume_thread: threading.Thread = None

    def __handle_update_message(self):
        while True:
            try:
                for message in self.kafka_proxy.consumer:

                    self.handle_update_message(message)
            except Exception as e:
                logger.error(f"Kafka consumer might disconnected, try to reconnect later. Error: {str(e)}")
                time.sleep(5)  # 等待5秒後重試                

    def handle_update_message(self, message: ConsumerRecord):
        logger.info(f"Received message: {message}")

    def run_before(self):
        if self.kafka_config is not None:
            # Kafka 訂閱主題清單
            # self.kafka_config.consume_topic_list = [KafkaTopic.TaskNotifyProcessUpdate(self.task_id)]
            self.kafka_config.consume_topic_list = [KafkaTopic.TaskWorkerUpdate]
            # 更換Kafka group ip
            self.kafka_config.consume_group_id = f"{self.task_id}_{str(uuid.uuid4())[:5]}"
            # Kafka 連線代理
            self.kafka_proxy = KafkaProxy(kafka_config=self.kafka_config, is_block=TaskWorkerConfig.mode == "node")
            # Kafka 消化主題負責執行序
            self.update_consume_thread = threading.Thread(target=self.__handle_update_message, daemon=True)
            # 啟動執行序消化Kafka主題
            self.update_consume_thread.start()
        
        if self.redis_config is not None:
            # Redis 連線代理
            self.redis_proxy = RedisProxy(redis_config=self.redis_config, is_block=TaskWorkerConfig.mode == "node")
            # TaskWorker 心跳運行物件
            self.survive_handler = SurviveHandler(
                                    redis_proxy=self.redis_proxy, # Redis 連線代理物件，發布心跳用
                                    key=RedisKey.TaskHeartbeat_key(self.task_id), # Redis 中的心跳名稱
                                    role=SurviveRoleEnum.TASKWORKER.value # 心跳所屬角色
                                    )
            # TaskWorker 啟動心跳
            self.survive_handler.start_heartbeat_update()
            # 清除 Redis 中TaskWorker的異常暫存
            self.redis_proxy.set_message(key=RedisKey.TaskException_key(self.task_id), message="")

    def run_after(self):
        if self.redis_proxy:
            self.survive_handler.stop_heartbeat_update() # 結束心跳
            if not self.is_done:
                self.survive_handler.push_success_heartbeat() # 發布完成狀態
        logger.success(f"Task Worker {self.task_id} is done.")

    def error_handler(self, e: Exception):
        self.survive_handler.stop_heartbeat_update() # 結束心跳
        
        # 發布 TaskWorker 異常訊息 
        self.redis_proxy.set_message(key=RedisKey.TaskException_key(self.task_id), message=str(e))
        self.survive_handler.push_failed_heartbeat() # 發布異常狀態
        logger.error(f"Task Worker {self.task_id} is failed with error: {str(e)}")

    def release(self, *args):
        try:
            if self.kafka_proxy:
                self.kafka_proxy.consumer.close() # 關閉 Kafka 訂閱連線 
                self.kafka_proxy.producer.close() # 關閉 Kafka 發布連線
                # kafka_admin_client = KafkaAdmin(self.kafka_config) # 建立 Kafka 高權限連接
                # 清除 Kafka 主題
                # kafka_admin_client.delete_topic(topic_name=KafkaTopic.TaskNotifyProcessUpdate(self.task_id))
        except Exception as e:
            logger.error(f"Task Worker {self.task_id}:{self.task_type} is failed with error in release stage: {str(e)}")
        
        try:
            if len(args) >= 2:
                if args[0] == SIGINT or args[0] == SIGTERM:
                    self.survive_handler.stop_heartbeat_update() # 結束心跳
                    self.survive_handler.push_canceled_heartbeat()
        except Exception as e:
            logger.error(f"Task Worker {self.task_id}:{self.task_type} is get unknown signal: {str(e)}")
        
        try:
            TaskWorkerStore.TaskWorkerUidDic.pop(self.task_id) # 清除主程式的 TaskWorker Process 暫存
        except Exception as e:
            logger.warning(f"Task Worker maybe not exist in Store: {str(e)}")
        logger.info(f"Task Worker {self.task_id} is releasing.")

