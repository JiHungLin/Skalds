# https://github.com/aio-libs/aiokafka 之後可以考慮換成異步
from typing import List, Optional
from kafka import KafkaConsumer, KafkaProducer, KafkaAdminClient
from kafka.errors import TopicAlreadyExistsError
from kafka.admin import NewTopic
from skald.config.systemconfig import SystemConfig
from skald.utils.logging import logger
import threading
import time


class KafkaTopic:
    TaskAssign = "task.assign"
    TaskCancel = "task.cancel"
    TaskUpdateAttachment = "task.update.attachment"
    TaskWorkerUpdate = "taskworker.update"
    TestingProducer = "testing"
    
    @staticmethod
    def TaskNotifyProcessUpdate(task_id: str):
        return f"task.{task_id}.update"

class KafkaConfig:
    def __init__(self, host: str = 'localhost', 
                 port: int = 9092, 
                 consume_topic_list: List[str] = [], 
                 consume_group_id: str = SystemConfig.SKALD_ID,
                 username: str = "",
                 password: str= "") -> None:
        self.host = host
        self.port = port
        self.consume_topic_list = consume_topic_list
        self.consume_group_id = consume_group_id
        self.username = username
        self.password = password

class KafkaProxy:
    def __init__(self, kafka_config: KafkaConfig = KafkaConfig(), is_block = True) -> None:
        bootstrap_servers = f"{kafka_config.host}:{kafka_config.port}"
        self.host = kafka_config.host
        self.port = kafka_config.port
        self.__kafka_config = kafka_config
        self.__is_block = is_block
        self.consumer: Optional[KafkaConsumer] = None
        self.producer: Optional[KafkaProducer] = None
        self.__connected = False
        self.__connection_thread = None
        
        # Start the connection thread
        logger.info("Kafka connection attempt started in background thread")
        
        def connection_worker():
            while True:
                try:
                    bootstrap_servers = f"{self.__kafka_config.host}:{self.__kafka_config.port}"
                    # Consumer
                    logger.info(f"Generating KafkaConsumer - host:{bootstrap_servers}")
                    if "confluent.cloud" in bootstrap_servers:
                        consumer: KafkaConsumer = KafkaConsumer(
                                        bootstrap_servers=bootstrap_servers,
                                        enable_auto_commit=True, # 啟用自動提交偏移量
                                        auto_offset_reset='latest', # 至newest啟動時，會至newest偏移量',
                                        max_partition_fetch_bytes=10485760, # 讀取最大字节敏
                                        group_id=self.__kafka_config.consume_group_id,
                                        security_protocol="SASL_SSL",
                                        sasl_plain_username=self.__kafka_config.username,
                                        sasl_plain_password=self.__kafka_config.password,
                                        sasl_mechanism="PLAIN"
                                        )
                    else:
                        consumer: KafkaConsumer = KafkaConsumer(
                                        bootstrap_servers=bootstrap_servers,
                                        enable_auto_commit=True, # 啟用自動提交偏移量
                                        auto_offset_reset='latest', # 至newest啟動時，會至newest偏移量',
                                        max_partition_fetch_bytes=10485760, # 讀取最大字节敏
                                        group_id=self.__kafka_config.consume_group_id
                                        )
                    logger.success(f"Generated KafkaConsumer")

                    if len(self.__kafka_config.consume_topic_list) > 0:
                        consumer.subscribe(self.__kafka_config.consume_topic_list)
                        logger.success(f"KafkaConsumer consume list: {self.__kafka_config.consume_topic_list}")
                    else:
                        logger.warning(f"KafkaConsumer consume list is empty")

                    # Producer
                    logger.info(f"Generating KafkaProducer - host:{bootstrap_servers}")
                    if "confluent.cloud" in bootstrap_servers:
                        producer = KafkaProducer(
                                        bootstrap_servers=bootstrap_servers, 
                                        api_version=(0,10,1),
                                        acks=1,
                                        value_serializer=None,
                                        key_serializer=str.encode,
                                        batch_size=65536,
                                        compression_type='gzip',
                                        linger_ms=0,
                                        # buffer_memory=67108864,
                                        max_request_size=10485760,
                                        max_in_flight_requests_per_connection=1,
                                        retries=1,
                                        security_protocol="SASL_SSL",
                                        sasl_plain_username=self.__kafka_config.username,
                                        sasl_plain_password=self.__kafka_config.password,
                                        sasl_mechanism="PLAIN",
                                        delivery_timeout_ms = 30000
                                        )
                        
                    else:
                        producer = KafkaProducer(
                                        bootstrap_servers=bootstrap_servers, 
                                        api_version=(0,10,1),
                                        acks=1,
                                        value_serializer=None,
                                        key_serializer=str.encode,
                                        batch_size=65536,
                                        compression_type='gzip',
                                        linger_ms=0,
                                        # buffer_memory=67108864,
                                        max_request_size=10485760,
                                        max_in_flight_requests_per_connection=1,
                                        retries=1,
                                        delivery_timeout_ms = 30000
                                        )
                    logger.success(f"Generated KafkaProducer")
                    
                    # Assign the created objects to the class instance
                    self.consumer = consumer
                    self.producer = producer
                    self.__connected = True
                    logger.success(f"Connected to Kafka at {self.__kafka_config.host}:{self.__kafka_config.port}")
                    break
                except Exception as e:
                    logger.error(f"Failed to connect to Kafka at {self.__kafka_config.host}:{self.__kafka_config.port}. Error: {str(e)}. Retrying in 5 seconds...")
                    time.sleep(5)
                        
        if self.__is_block:
            # If blocking mode, run the connection worker directly
            connection_worker()
        else:
            # If non-blocking mode, start the connection worker in a thread
            logger.info("Starting Kafka connection worker in a separate thread")
            self.__connection_thread = threading.Thread(target=connection_worker, daemon=True)
            self.__connection_thread.start()

    
    def produce(self, topic_name: str, key: str, value: str):
        if not self.__connected:
            logger.warning(f"Kafka not yet connected. Message to {topic_name} will not be sent.")
            return
        
        try:
            logger.info(f"Producing - topic:{topic_name}, key:{key}, value:{value}")
            # Send message without blocking
            future = self.producer.send(topic_name, key=key, value=value)
            # Add a callback to handle completion instead of blocking with flush
            def on_send_success(record_metadata):
                logger.success(f"Produced - topic:{topic_name}, key:{key}, partition:{record_metadata.partition}, offset:{record_metadata.offset}")
                
            def on_send_error(excp):
                logger.error(f"Failed to produce message to {topic_name}: {str(excp)}")
                
            future.add_callback(on_send_success).add_errback(on_send_error)
            logger.success(f"Message sent to {topic_name} (async)")
        except Exception as e:
            logger.error(f"Failed to produce message. Error: {str(e)}")


class KafkaAdmin:
    def __init__(self, kafka_config: KafkaConfig):
        bootstrap_servers = f"{kafka_config.host}:{kafka_config.port}"
        self.host = kafka_config.host
        self.port = kafka_config.port
        try:
            logger.info(f"Generating KafkaAdmin - host:{bootstrap_servers}")
            if "confluent.cloud" in bootstrap_servers:
                self.admin = KafkaAdminClient(
                                    bootstrap_servers=bootstrap_servers,
                                    security_protocol="SASL_SSL",
                                    sasl_plain_username=kafka_config.username,
                                    sasl_plain_password=kafka_config.password,
                                    sasl_mechanism="PLAIN"
                                    )
            else:
                self.admin = KafkaAdminClient(
                                    bootstrap_servers=bootstrap_servers
                                    )
            logger.success(f"Generated KafkaAdmin")
        except Exception as e:
            logger.error(e)
            raise e
        
    def create_topic(self, topic_name: str, partitions: int=6, replication_factor: int=SystemConfig.KAFKA_REPLICATION_FACTOR):
        try:
            logger.info(f"Creating topic - topic:{topic_name}")
            self.admin.create_topics([NewTopic(name=topic_name, num_partitions=partitions, replication_factor=replication_factor)])
            logger.success(f"Created topic - topic:{topic_name}, partitions:{partitions}, replication_factor:{replication_factor}")
        except TopicAlreadyExistsError as e:
            logger.warning("Topic Already Exist")
        except Exception as e:
            logger.error(e)

    def delete_topic(self, topic_name: str):
        try:
            logger.info(f"Deleting topic - topic:{topic_name}")
            self.admin.delete_topics([topic_name])
            logger.success(f"Deleted topic - topic:{topic_name}")
        except Exception as e:
            logger.error(str(e))

    def disconnect(self):
        self.admin.close()
"""Detail
consumer = KafkaConsumer(topic_name,
                        bootstrap_servers=bootstrap_servers,
                        fetch_max_bytes=52428800,
                        fetch_max_wait_ms=1000,
                        fetch_min_bytes=1,
                        max_partition_fetch_bytes=10485760,
                        value_deserializer=None,
                        key_deserializer=None,
                        max_in_flight_requests_per_connection=10,
                        # client_id=self.client_id,
                        # group_id=self.group_id,
                        auto_offset_reset='latest',
                        max_poll_records=500,
                        max_poll_interval_ms=300000,
                        heartbeat_interval_ms=3000,
                        session_timeout_ms=10000,
                        enable_auto_commit=True,
                        auto_commit_interval_ms=5000,
                        reconnect_backoff_ms=50,
                        reconnect_backoff_max_ms=500,
                        request_timeout_ms=305000,
                        receive_buffer_bytes=32768,
                        )

producer = KafkaProducer(
    bootstrap_servers=bootstrap_servers, 
            api_version=(0,10,1),
            acks=1,

```            value_serializer=None,
            key_serializer=str.encode,
            batch_size=65536,
            compression_type='gzip',
            linger_ms=0,
            # buffer_memory=67108864,
            max_request_size=10485760,
            max_in_flight_requests_per_connection=1,
            retries=1
    )                       

"""