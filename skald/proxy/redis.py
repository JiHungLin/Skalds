import base64
import cv2
import numpy as np
import redis
from skald.utils.logging import logger
import threading
import time

class RedisKey:
    ## Format: name_type = {key_name}

    ## Skald
    
    SkaldList_hash = "skald:hash"

    @staticmethod
    def SkaldHeartbeat_key(skald_id):
        return "skald:%s:heartbeat" % skald_id
    
    @staticmethod
    def SkaldAllTask_key(skald_id):
        return "skald:%s:all-task" % skald_id
    
    ## Task

    @staticmethod
    def TaskHasError_key(task_id):
        return "task:%s:has-error" % task_id

    @staticmethod
    def TaskHeartbeat_key(task_id):
        return "task:%s:heartbeat" % task_id

    @staticmethod
    def TaskException_key(task_id):
        return "task:%s:exception" % task_id
    
    # Camera Cache
    @staticmethod
    def TaskMapByCameraId(camera_id):
        return "task-map:%s" % camera_id

class RedisConfig:
    def __init__(self, host:str="localhost", port:int=6379, password: str = ""):
        self.host = host
        self.port = port
        self.password = password

class RedisProxy:
    def __init__(self, redis_config: RedisConfig = RedisConfig(), is_block: bool = True):
        self.host = redis_config.host
        self.port = redis_config.port
        self.is_block = is_block
        logger.info("Connecting to redis at %s:%s" % (redis_config.host, redis_config.port))
        self.__client = None
        self.__redis_config = redis_config
        self.__connection_thread = None
        
        # Start the connection thread
        
        def connection_worker():
            while True:
                try:
                    pool = redis.ConnectionPool(
                    host=self.__redis_config.host,
                    port=self.__redis_config.port,
                    decode_responses=False,
                    password=self.__redis_config.password,
                    health_check_interval=10,
                    socket_timeout=10, socket_keepalive=True,
                    socket_connect_timeout=10, retry_on_timeout=True
                    )
                    client = redis.StrictRedis(connection_pool=pool)
                    client.ping()
                    
                    # Check if it's a cluster
                    if 'cluster_enabled' in client.info() and client.info().get('cluster_enabled', 0) == 1:
                        client = redis.cluster.RedisCluster(
                            host=self.__redis_config.host,
                            port=self.__redis_config.port, 
                            password=self.__redis_config.password
                        )
                        client.ping()
                        
                        # Connection successful
                    self.__client = client
                    self.__connected = True
                    logger.success("Connected to redis at %s:%s" % (self.__redis_config.host, self.__redis_config.port))
                    break
                except Exception as e:
                    logger.error("Failed to connect to redis at %s:%s. Error: %s. Retrying in 5 seconds..." % 
                        (self.__redis_config.host, self.__redis_config.port, str(e)))
                    if self.is_block:
                        raise e
                    time.sleep(5)

        if self.is_block:
            # If blocking mode, run the connection worker directly
            connection_worker()
        else:            
            self.__connection_thread = threading.Thread(target=connection_worker, daemon=True)
            self.__connection_thread.start()
        
        # Initial log message
        logger.info("Redis connection attempt started in background thread")

    def flush_all(self):
        try:
            self.__client.flushall()
        except Exception as e:
            logger.error("Failed to flush all. Error: %s" % str(e))

    def set_hash(self, key: str, field: str, value: str):
        try:
            self.__client.hset(key, field, value)
        except Exception as e:
            logger.error("Failed to set hash. Error: %s" % str(e))

    def get_hash(self, key: str, field: str):
        value = None
        try:
            value = str(self.__client.hget(key, field).decode())
        except Exception as e:
            logger.error("Failed to get hash. Error: %s" % str(e))
        return value

    def push_list(self, key: str, value: str, insert_head: bool = True):
        try:
            if insert_head:
                self.__client.rpush(key, value)
            else:
                self.__client.lpush(key, value)
        except Exception as e:
            logger.error("Failed to push list. Error: %s" % str(e))

    def delete_hash(self, key: str, field: str):
        try:
            self.__client.hdel(key, field)
        except Exception as e:
            logger.error("Failed to delete hash. Error: %s" % str(e))
            
    def set_message(self, key: str, message, expire: int = 0):
        try:
            if expire > 0:
                self.__client.set(key, message, ex=expire)
            else:
                self.__client.set(key, message)
        except Exception as e:
            logger.error("Failed to set message. Error: %s" % str(e))

    def get_message(self, key: str):
        message = None
        try:
            message = self.__client.get(key)
        except Exception as e:
            logger.error("Failed to get message. Error: %s" % str(e))
        return message
    
    def get_sub_keys(self, root_key: str):
        keys = []
        try:
            keys = self.__client.keys(root_key + "*")
        except Exception as e:
            logger.error("Failed to get sub keys. Error: %s" % str(e))
        keys = [key.decode() for key in keys]
        return keys
    
    def get_all_hash(self, root_key: str):
        hash_dict = {}
        try:
            hash_dict = self.__client.hgetall(root_key)
        except Exception as e:
            logger.error("Failed to get sub hash. Error: %s" % str(e))
        hash_dict = {k.decode(): v.decode() for k, v in hash_dict.items()}
        return hash_dict

    def set_image_base64(self, key: str, frame: np.ndarray, quality = 100):
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        # _, buffer = cv2.imencode('.bmp', frame)
        try:
            self.__client.set(key, base64.b64encode(buffer))
        except  Exception as e:
            logger.error("Failed to set image. Error: %s" % str(e))
            
    def set_image_byte(self, key: str, frame: np.ndarray, quality = 100):
        img_bytes = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])[1].tobytes()
        try:
            self.__client.set(key, img_bytes)
        except  Exception as e:
            logger.error("Failed to set image. Error: %s" % str(e))

    def get_image_base64(self, key: str):
        base64_str = None
        try:
            base64_str = self.__client.get(key)
        except Exception as e:
            logger.error("Failed to get image. Error: %s" % str(e))

        if base64_str is None:
            return None
        else:
            np_arr = np.fromstring(base64.b64decode(base64_str), np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_ANYCOLOR)
            return frame

    def get_image_byte(self, key: str):
        img_bytes = None
        try:
            img_bytes = self.__client.get(key)
        except Exception as e:
            logger.error("Failed to get image. Error: %s" % str(e))

        if img_bytes is None:
            return None
        else:
            np_arr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            return frame
        
    def get_subscribe(self, ignore_subscribe_messages=True):
        try:
            return self.__client.pubsub(ignore_subscribe_messages = ignore_subscribe_messages)
        except Exception as e:
            logger.error("Failed to get subscribe. Error: %s" % str(e))
            return None
        
    def publish_message(self, channel, message):
        try:
            return self.__client.publish(channel, message)
        except Exception as e:
            logger.error("Failed to publish message. Error: %s" % str(e))
            return None
        
    def delete_key(self, key):
        try:
            return self.__client.delete(key)
        except Exception as e:
            logger.error("Failed to delete key. Error: %s" % str(e))
            return None