from skalds import Skalds
from skalds.config.skald_config import SkaldConfig
from my_worker import MyWorker

config = SkaldConfig(
    log_level="DEBUG",
    redis_host="localhost",
    redis_port=6379,
    kafka_host="127.0.0.1",
    kafka_port=9092,
    mongo_host="mongodb://root:root@localhost:27017/",
    skald_mode="node",
    log_split_with_worker_id=True,
)

app = Skalds(config)

app.register_task_worker(MyWorker)

if __name__ == "__main__":
    app.run()