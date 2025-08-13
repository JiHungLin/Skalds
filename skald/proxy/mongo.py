"""
Mongo Proxy Module

Provides a simple, user-friendly interface for MongoDB connections.
"""

import pymongo
from skald.utils.logging import logger
from skald.config.systemconfig import SystemConfig


class MongoConfig:
    """
    Configuration for MongoDB connection.
    """

    def __init__(self, host: str = "mongodb://localhost:27017/", db_name: str = SystemConfig.DB_NAME) -> None:
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
    
    def init_db_index(self):
        # Create unique index for tasks collection
        self.db.tasks.create_index([("id", pymongo.ASCENDING)], unique=True)

    def close(self):
        """
        Close the MongoDB client connection.
        """
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed.")

# End of file