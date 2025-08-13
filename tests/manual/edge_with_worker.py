from skald import Skald
from skald.config.skald_config import SkaldConfig
from my_worker import MyWorker

config = SkaldConfig(
    log_level="DEBUG",
    redis_host="localhost",
    redis_port=6379,
    kafka_host="192.168.1.110",
    kafka_port=9092,
    mongo_host="mongodb://root:root@localhost:27017/",
    skald_mode="edge",
    yaml_file="/home/jihung/Projects/dev/Skald/tests/manual/all_workers.yml"
)

app = Skald(config)

app.register_task_worker(MyWorker)

if __name__ == "__main__":
    app.run()