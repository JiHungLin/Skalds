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
                except redis.ConnectionError as ce:
                    logger.debug(f"Failed to connect to Redis at {self.host}:{self.port}. ConnectionError: {ce}")
                    time.sleep(5)
                except Exception as e:
                    logger.error(
                        f"Failed to connect to Redis at {self.host}:{self.port}. Error: {e}. Retrying in 5 seconds..."
                    )
                    time.sleep(5)

        if self.is_block:
            connection_worker()
        else:
            logger.info("Starting Redis connection worker in a separate thread")
            self._connection_thread = threading.Thread(target=connection_worker, daemon=True)
            self._connection_thread.start()

    def flush_all(self):
        """Flush all keys in the current database."""
        if not self._client:
            return None
        try:
            self._client.flushall()
        except redis.ConnectionError as ce:
            logger.debug(f"Failed to flush all. ConnectionError: {ce}")
        except Exception as e:
            logger.error(f"Failed to flush all. Error: {e}")

    def set_hash(self, key: str, field: str, value: str, ttl: int = 0):
        """Set a field in a hash."""
        if not self._client:
            return None
        try:
            self._client.hset(key, field, value)
            if ttl > 0:
                self._client.hexpire(key, ttl, field)
        except redis.ConnectionError as ce:
            logger.debug(f"Failed to set hash. ConnectionError: {ce}")
        except Exception as e:
            logger.error(f"Failed to set hash. Error: {e}")

    def get_hash(self, key: str, field: str):
        """Get a field value from a hash."""
        if not self._client:
            return None
        try:
            value = self._client.hget(key, field)
            return value.decode() if value else None
        except redis.ConnectionError as ce:
            logger.debug(f"Failed to get hash. ConnectionError: {ce}")
        except Exception as e:
            logger.error(f"Failed to get hash. Error: {e}")
            return None

    def push_list(self, key: str, value: str, insert_head: bool = True, ttl: int = 0):
        """Push a value to a list (head or tail)."""
        if not self._client:
            return None
        try:
            if insert_head:
                self._client.rpush(key, value)
            else:
                self._client.lpush(key, value)
            if ttl > 0:
                self._client.expire(key, ttl)
        except redis.ConnectionError as ce:
            logger.debug(f"Failed to push list. ConnectionError: {ce}")
        except Exception as e:
            logger.error(f"Failed to push list. Error: {e}")

    def overwrite_list(self, key: str, values: list[str], ttl: int = 0):
        """Overwrite a list with new values."""
        if not self._client:
            return None
        try:
            self._client.delete(key)  # Clear the existing list
            for value in values:
                self._client.rpush(key, value)
            if ttl > 0:
                self._client.expire(key, ttl)
        except redis.ConnectionError as ce:
            logger.debug(f"Failed to overwrite list. ConnectionError: {ce}")
        except Exception as e:
            logger.error(f"Failed to overwrite list. Error: {e}")

    def delete_hash(self, key: str, field: str):
        """Delete a field from a hash."""
        if not self._client:
            return None
        try:
            self._client.hdel(key, field)
        except redis.ConnectionError as ce:
            logger.debug(f"Failed to delete hash. ConnectionError: {ce}")
        except Exception as e:
            logger.error(f"Failed to delete hash. Error: {e}")

    def set_message(self, key: str, message, expire: int = 0, ttl: int = 0):
        """Set a string value with optional expiration."""
        if not self._client:
            return None
        try:
            if expire > 0:
                self._client.set(key, message, ex=expire)
            else:
                self._client.set(key, message)
            if ttl > 0:
                self._client.expire(key, ttl)
        except redis.ConnectionError as ce:
            logger.debug(f"Failed to set message. ConnectionError: {ce}")
        except Exception as e:
            logger.error(f"Failed to set message. Error: {e}")

    def get_message(self, key: str):
        """Get a string value."""
        if not self._client:
            return None
        try:
            message = self._client.get(key)
            return message
        except redis.ConnectionError as ce:
            logger.debug(f"Failed to get message. ConnectionError: {ce}")
        except Exception as e:
            logger.error(f"Failed to get message. Error: {e}")
            return None

    def get_sub_keys(self, root_key: str):
        """Get all keys matching a root pattern."""
        if not self._client:
            return []
        try:
            keys = self._client.keys(root_key + "*")
            return [key.decode() for key in keys]
        except redis.ConnectionError as ce:
            logger.debug(f"Failed to get sub keys. ConnectionError: {ce}")
        except Exception as e:
            logger.error(f"Failed to get sub keys. Error: {e}")
            return []

    def get_all_hash(self, root_key: str):
        """Get all fields and values from a hash."""
        if not self._client:
            return {}
        try:
            hash_dict = self._client.hgetall(root_key)
            return {k.decode(): v.decode() for k, v in hash_dict.items()}
        except redis.ConnectionError as ce:
            logger.debug(f"Failed to get all hash. ConnectionError: {ce}")
        except Exception as e:
            logger.error(f"Failed to get all hash. Error: {e}")
            return {}

    def get_subscribe(self, ignore_subscribe_messages=True):
        """Get a pubsub object for subscribing to channels."""
        if not self._client:
            return None
        try:
            return self._client.pubsub(ignore_subscribe_messages=ignore_subscribe_messages)
        except redis.ConnectionError as ce:
            logger.debug(f"Failed to get subscribe. ConnectionError: {ce}")
        except Exception as e:
            logger.error(f"Failed to get subscribe. Error: {e}")
            return None

    def publish_message(self, channel, message, ttl: int = 0):
        """Publish a message to a channel."""
        if not self._client:
            return None
        try:
            result = self._client.publish(channel, message)
            if ttl > 0:
                self._client.expire(channel, ttl)
            return result
        except redis.ConnectionError as ce:
            logger.debug(f"Failed to publish message. ConnectionError: {ce}")
        except Exception as e:
            logger.error(f"Failed to publish message. Error: {e}")
            return None

    def delete_key(self, key):
        """Delete a key."""
        if not self._client:
            return None
        try:
            return self._client.delete(key)
        except redis.ConnectionError as ce:
            logger.debug(f"Failed to delete key. ConnectionError: {ce}")
        except Exception as e:
            logger.error(f"Failed to delete key. Error: {e}")
            return None

# End of file