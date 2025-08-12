"""
Redis Proxy Module

Provides a user-friendly, Pythonic interface for Redis operations.
"""

from typing import Optional
import redis
from skald.utils.logging import logger
import threading
import time

class RedisKey:
    """
    Predefined Redis key patterns and utilities.
    """

    # Skald
    SKALD_LIST_HASH = "skald:hash"
    SKALD_MODE_LIST_HASH = "skald:mode:hash"

    @staticmethod
    def skald_heartbeat(skald_id: str) -> str:
        return f"skald:{skald_id}:heartbeat"
    
    @staticmethod
    def skald_allow_task_class_name(skald_id: str) -> str:
        return f"skald:{skald_id}:allow-task-class-name"

    @staticmethod
    def skald_all_task(skald_id: str) -> str:
        return f"skald:{skald_id}:all-task"

    # Task
    @staticmethod
    def task_has_error(task_id: str) -> str:
        return f"task:{task_id}:has-error"

    @staticmethod
    def task_heartbeat(task_id: str) -> str:
        return f"task:{task_id}:heartbeat"

    @staticmethod
    def task_exception(task_id: str) -> str:
        return f"task:{task_id}:exception"


class RedisConfig:
    """
    Configuration for Redis connection.
    """
    def __init__(self, host: str = "localhost", port: int = 6379, password: str = ""):
        self.host = host
        self.port = port
        self.password = password


class RedisProxy:
    """
    Redis Proxy for common Redis operations.

    Usage:
        proxy = RedisProxy(RedisConfig(...))
        proxy.set_message("key", "value")
    """

    def __init__(self, redis_config: RedisConfig = RedisConfig(), is_block: bool = True):
        self.host = redis_config.host
        self.port = redis_config.port
        self.is_block = is_block
        self._client: Optional[redis.StrictRedis] = None
        self._redis_config = redis_config
        self._connection_thread = None
        self._connected = False

        logger.info(f"Connecting to Redis at {self.host}:{self.port}")

        def connection_worker():
            while True:
                try:
                    pool = redis.ConnectionPool(
                        host=self._redis_config.host,
                        port=self._redis_config.port,
                        decode_responses=False,
                        password=self._redis_config.password,
                        health_check_interval=10,
                        socket_timeout=10,
                        socket_keepalive=True,
                        socket_connect_timeout=10,
                        retry_on_timeout=True,
                    )
                    client = redis.StrictRedis(connection_pool=pool)
                    client.ping()

                    # Check if it's a cluster
                    info = client.info()
                    if info.get("cluster_enabled", 0) == 1:
                        client = redis.cluster.RedisCluster(
                            host=self._redis_config.host,
                            port=self._redis_config.port,
                            password=self._redis_config.password,
                        )
                        client.ping()

                    self._client = client
                    self._connected = True
                    logger.success(f"Connected to Redis at {self.host}:{self.port}")
                    break
                except Exception as e:
                    logger.error(
                        f"Failed to connect to Redis at {self.host}:{self.port}. Error: {e}. Retrying in 5 seconds..."
                    )
                    if self.is_block:
                        raise
                    time.sleep(5)

        if self.is_block:
            connection_worker()
        else:
            self._connection_thread = threading.Thread(target=connection_worker, daemon=True)
            self._connection_thread.start()

        logger.info("Redis connection attempt started in background thread")

    def flush_all(self):
        """Flush all keys in the current database."""
        try:
            self._client.flushall()
        except Exception as e:
            logger.error(f"Failed to flush all. Error: {e}")

    def set_hash(self, key: str, field: str, value: str):
        """Set a field in a hash."""
        try:
            self._client.hset(key, field, value)
        except Exception as e:
            logger.error(f"Failed to set hash. Error: {e}")

    def get_hash(self, key: str, field: str):
        """Get a field value from a hash."""
        try:
            value = self._client.hget(key, field)
            return value.decode() if value else None
        except Exception as e:
            logger.error(f"Failed to get hash. Error: {e}")
            return None

    def push_list(self, key: str, value: str, insert_head: bool = True):
        """Push a value to a list (head or tail)."""
        try:
            if insert_head:
                self._client.rpush(key, value)
            else:
                self._client.lpush(key, value)
        except Exception as e:
            logger.error(f"Failed to push list. Error: {e}")
    
    def overwrite_list(self, key: str, values: list[str]):
        """Overwrite a list with new values."""
        try:
            self._client.delete(key)  # Clear the existing list
            self._client.rpush(key, *values)  # Push new values
        except Exception as e:
            logger.error(f"Failed to overwrite list. Error: {e}")

    def delete_hash(self, key: str, field: str):
        """Delete a field from a hash."""
        try:
            self._client.hdel(key, field)
        except Exception as e:
            logger.error(f"Failed to delete hash. Error: {e}")

    def set_message(self, key: str, message, expire: int = 0):
        """Set a string value with optional expiration."""
        try:
            if expire > 0:
                self._client.set(key, message, ex=expire)
            else:
                self._client.set(key, message)
        except Exception as e:
            logger.error(f"Failed to set message. Error: {e}")

    def get_message(self, key: str):
        """Get a string value."""
        try:
            message = self._client.get(key)
            return message
        except Exception as e:
            logger.error(f"Failed to get message. Error: {e}")
            return None

    def get_sub_keys(self, root_key: str):
        """Get all keys matching a root pattern."""
        try:
            keys = self._client.keys(root_key + "*")
            return [key.decode() for key in keys]
        except Exception as e:
            logger.error(f"Failed to get sub keys. Error: {e}")
            return []

    def get_all_hash(self, root_key: str):
        """Get all fields and values from a hash."""
        try:
            hash_dict = self._client.hgetall(root_key)
            return {k.decode(): v.decode() for k, v in hash_dict.items()}
        except Exception as e:
            logger.error(f"Failed to get all hash. Error: {e}")
            return {}

    def get_subscribe(self, ignore_subscribe_messages=True):
        """Get a pubsub object for subscribing to channels."""
        try:
            return self._client.pubsub(ignore_subscribe_messages=ignore_subscribe_messages)
        except Exception as e:
            logger.error(f"Failed to get subscribe. Error: {e}")
            return None

    def publish_message(self, channel, message):
        """Publish a message to a channel."""
        try:
            return self._client.publish(channel, message)
        except Exception as e:
            logger.error(f"Failed to publish message. Error: {e}")
            return None

    def delete_key(self, key):
        """Delete a key."""
        try:
            return self._client.delete(key)
        except Exception as e:
            logger.error(f"Failed to delete key. Error: {e}")
            return None

# End of file