# https://www.mongodb.com/languages/python

import pymongo
from skald.utils.logging import logger
from skald.config.systemconfig import SystemConfig



class MongoConfig:
    def __init__(self, host="mongodb://localhost:27017/", db_name=SystemConfig.DB_NAME) -> None:
            self.host = host
            self.db_name = db_name

class MongoProxy:
    def __init__(self, mongo_config: MongoConfig = MongoConfig()) -> None:
            try:
                self.host = mongo_config.host
                logger.info(f"Connecting to mongodb: {mongo_config.host} ...")
                self.client = pymongo.MongoClient(self.host)
                self.db = self.client[mongo_config.db_name]
                logger.info(f"Connected to mongodb: {mongo_config.host}, used db: {mongo_config.db_name}")
            except Exception as e:
                logger.error("Failed to connect to mongodb")
                raise e