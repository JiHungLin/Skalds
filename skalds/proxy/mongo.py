"""
Mongo Proxy Module

Provides a simple, user-friendly interface for MongoDB connections.
"""

import threading
import time
import pymongo
from skalds.utils.logging import logger
from skalds.config.systemconfig import SystemConfig


class MongoConfig:
    """
    Configuration for MongoDB connection.
    """

    def __init__(self, host: str = "mongodb://localhost:27017/", db_name: str = SystemConfig.DB_NAME) -> None:
        if host is None or host.strip() == "":
            host = "mongodb://localhost:27017/"
        self.host = host
        self.db_name = db_name


class MongoProxy:
    """
    MongoDB Proxy for connecting and accessing a database.

    Usage:
        proxy = MongoProxy(MongoConfig(...))
        db = proxy.db
    """

    def __init__(self, mongo_config: MongoConfig = MongoConfig()) -> None:
        self.host = mongo_config.host
        self.db_name = mongo_config.db_name
        self.client = None
        self.db = None
        try:
            logger.info(f"Connecting to MongoDB: {self.host} ...")
            self.client = pymongo.MongoClient(self.host,
                serverSelectionTimeoutMS=3000,
                connectTimeoutMS=3000,
                socketTimeoutMS=3000    
            )
            self.db = self.client[self.db_name]
            logger.info(f"Connected to MongoDB: {self.host}, using db: {self.db_name}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB at {self.host}: {e}")
            raise
    
    def init_db_index(self, is_block: bool = True) -> None:
        """
        Create unique index for the tasks collection.

        MongoClient connects lazily, so this is typically the first call that
        actually touches the server. If Mongo is unreachable, retry forever
        instead of letting a ServerSelectionTimeoutError escape uncaught -
        otherwise the caller (e.g. Skald.__init__ in node mode) dies with an
        unhandled exception before any retry/reconnect logic ever runs.
        """
        def worker():
            while True:
                try:
                    self.db.tasks.create_index([("id", pymongo.ASCENDING)], unique=True)
                    logger.success(f"MongoDB index initialized on {self.host}.")
                    return
                except Exception as e:
                    logger.error(f"Failed to initialize MongoDB index at {self.host}: {e}. Retrying in 5 seconds...")
                    time.sleep(5)

        if is_block:
            worker()
        else:
            threading.Thread(target=worker, daemon=True).start()

    def close(self):
        """
        Close the MongoDB client connection.
        """
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed.")

# End of file