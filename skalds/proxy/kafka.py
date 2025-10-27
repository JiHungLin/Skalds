"""
Kafka Proxy Module

Provides simplified, user-friendly interfaces for Kafka producer, consumer, and admin operations.
"""

from typing import List, Optional
from kafka import KafkaConsumer, KafkaProducer, KafkaAdminClient
from kafka.errors import TopicAlreadyExistsError, NoBrokersAvailable
from kafka.admin import NewTopic
from skalds.config.systemconfig import SystemConfig
from skalds.utils.logging import logger
import threading
import time


class KafkaTopic:
    """Predefined Kafka topic names and utilities."""
    TASK_ASSIGN = "task.assign"
    TASK_CANCEL = "task.cancel"
    TASK_UPDATE_ATTACHMENT = "task.update.attachment"
    TASK_WORKER_UPDATE = "taskworker.update"
    TESTING_PRODUCER = "testing"

    @staticmethod
    def task_notify_process_update(task_id: str) -> str:
        """Generate a topic name for task process update."""
        return f"task.{task_id}.update"


class KafkaConfig:
    """Configuration for Kafka connection."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 9092,
        consume_topic_list: Optional[List[str]] = None,
        consume_group_id: str = SystemConfig.SKALD_ID,
        username: str = "",
        password: str = "",
    ) -> None:
        if host is None or host.strip() == "":
            host = "localhost"
        if port is None or port <= 0:
            port = 9092
        self.host = host
        self.port = port
        self.consume_topic_list = consume_topic_list or []
        self.consume_group_id = consume_group_id
        self.username = username
        self.password = password


class KafkaProxy:
    """
    Kafka Proxy for producing and consuming messages.

    Usage:
        proxy = KafkaProxy(KafkaConfig(...))
        proxy.produce("topic", "key", "value")
    """

    def __init__(self, kafka_config: KafkaConfig = KafkaConfig(), is_block: bool = True) -> None:
        self.host = kafka_config.host
        self.port = kafka_config.port
        self._kafka_config = kafka_config
        self._is_block = is_block
        self.consumer: Optional[KafkaConsumer] = None
        self.producer: Optional[KafkaProducer] = None
        self._connected = False
        self._connection_thread = None

        logger.info("Kafka connection attempt started in background thread")

        def connection_worker():
            while True:
                try:
                    bootstrap_servers = f"{self._kafka_config.host}:{self._kafka_config.port}"
                    # Consumer
                    consumer_kwargs = dict(
                        bootstrap_servers=bootstrap_servers,
                        enable_auto_commit=True,
                        auto_offset_reset="latest",
                        max_partition_fetch_bytes=10485760,
                        group_id=self._kafka_config.consume_group_id,
                    )
                    if "confluent.cloud" in bootstrap_servers:
                        consumer_kwargs.update(
                            security_protocol="SASL_SSL",
                            sasl_plain_username=self._kafka_config.username,
                            sasl_plain_password=self._kafka_config.password,
                            sasl_mechanism="PLAIN",
                        )
                    consumer = KafkaConsumer(**consumer_kwargs)
                    logger.success("KafkaConsumer created")

                    if self._kafka_config.consume_topic_list:
                        consumer.subscribe(self._kafka_config.consume_topic_list)
                        logger.success(f"KafkaConsumer subscribed to: {self._kafka_config.consume_topic_list}")
                    else:
                        logger.warning("KafkaConsumer topic list is empty")

                    # Producer
                    logger.info(f"Creating KafkaProducer - host:{bootstrap_servers}")
                    producer_kwargs = dict(
                        bootstrap_servers=bootstrap_servers,
                        api_version=(0, 10, 1),
                        acks=1,
                        value_serializer=None,
                        key_serializer=str.encode,
                        batch_size=65536,
                        compression_type="gzip",
                        linger_ms=0,
                        max_request_size=10485760,
                        max_in_flight_requests_per_connection=1,
                        retries=1,
                        delivery_timeout_ms=30000,
                    )
                    if "confluent.cloud" in bootstrap_servers:
                        producer_kwargs.update(
                            security_protocol="SASL_SSL",
                            sasl_plain_username=self._kafka_config.username,
                            sasl_plain_password=self._kafka_config.password,
                            sasl_mechanism="PLAIN",
                        )
                    producer = KafkaProducer(**producer_kwargs)
                    logger.success("KafkaProducer created")

                    self.consumer = consumer
                    self.producer = producer
                    self._connected = True
                    logger.success(f"Connected to Kafka at {self._kafka_config.host}:{self._kafka_config.port}")
                    break
                except NoBrokersAvailable as nba:
                    logger.debug(f"Failed to connect to Kafka at {self._kafka_config.host}:{self._kafka_config.port}. ConnectionError: {nba}")
                    time.sleep(5)
                except Exception as e:
                    logger.error(
                        f"Failed to connect to Kafka at {self._kafka_config.host}:{self._kafka_config.port}. " +
                        f"Error: {e}. Retrying in 5 seconds..."
                    )
                    time.sleep(5)

        if self._is_block:
            connection_worker()
        else:
            logger.info("Starting Kafka connection worker in a separate thread")
            self._connection_thread = threading.Thread(target=connection_worker, daemon=True)
            self._connection_thread.start()

    def produce(self, topic_name: str, key: str, value: str):
        """
        Produce a message to a Kafka topic.

        Args:
            topic_name (str): The topic to send to.
            key (str): The message key.
            value (str): The message value.
        """
        if not self._connected:
            logger.warning(f"Kafka not yet connected. Message to {topic_name} will not be sent.")
            return

        try:
            value = value.encode('utf-8')
        except (UnicodeEncodeError, AttributeError):
            logger.error(f"Value cannot be encoded as UTF-8: {value}")
            return

        try:
            logger.info(f"Producing - topic:{topic_name}, key:{key}, value:{value}")
            future = self.producer.send(topic_name, key=key, value=value)

            def on_send_success(record_metadata):
                logger.success(
                    f"Produced - topic:{topic_name}, key:{key}, partition:{record_metadata.partition}, offset:{record_metadata.offset}"
                )

            def on_send_error(excp):
                logger.error(f"Failed to produce message to {topic_name}: {excp}")

            future.add_callback(on_send_success).add_errback(on_send_error)
            logger.success(f"Message sent to {topic_name} (async)")
        except Exception as e:
            logger.error(f"Failed to produce message. Error: {e}")


class KafkaAdmin:
    """
    Kafka Admin for managing topics.
    """

    def __init__(self, kafka_config: KafkaConfig):
        bootstrap_servers = f"{kafka_config.host}:{kafka_config.port}"
        self.host = kafka_config.host
        self.port = kafka_config.port
        try:
            logger.info(f"Creating KafkaAdmin - host:{bootstrap_servers}")
            admin_kwargs = dict(bootstrap_servers=bootstrap_servers)
            if "confluent.cloud" in bootstrap_servers:
                admin_kwargs.update(
                    security_protocol="SASL_SSL",
                    sasl_plain_username=kafka_config.username,
                    sasl_plain_password=kafka_config.password,
                    sasl_mechanism="PLAIN",
                )
            self.admin = KafkaAdminClient(**admin_kwargs)
            logger.success("KafkaAdmin created")
        except Exception as e:
            logger.error(f"Failed to create KafkaAdmin: {e}")
            raise

    def create_topic(
        self,
        topic_name: str,
        partitions: int = 6,
        replication_factor: int = SystemConfig.KAFKA_REPLICATION_FACTOR,
    ):
        """
        Create a new Kafka topic.
        """
        try:
            logger.info(f"Creating topic: {topic_name}")
            self.admin.create_topics(
                [NewTopic(name=topic_name, num_partitions=partitions, replication_factor=replication_factor)]
            )
            logger.success(
                f"Created topic: {topic_name}, partitions: {partitions}, replication_factor: {replication_factor}"
            )
        except TopicAlreadyExistsError:
            logger.warning("Topic already exists")
        except Exception as e:
            logger.error(f"Failed to create topic: {e}")

    def delete_topic(self, topic_name: str):
        """
        Delete a Kafka topic.
        """
        try:
            logger.info(f"Deleting topic: {topic_name}")
            self.admin.delete_topics([topic_name])
            logger.success(f"Deleted topic: {topic_name}")
        except Exception as e:
            logger.error(f"Failed to delete topic: {e}")

    def disconnect(self):
        """
        Close the admin client connection.
        """
        self.admin.close()

# End of file