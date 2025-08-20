from skalds import Skald
from skalds.config.skald_config import SkaldConfig
from my_simple_worker import MySimpleWorker

config = SkaldConfig(
    skald_mode="node",
    skald_id="skald_123", # 唯一識別碼, 如果為空，系統會自動產生隨機碼
    log_split_with_worker_id=True,
    log_level="DEBUG",
    redis_host="localhost",
    redis_port=6379,
    kafka_host="127.0.0.1",
    kafka_port=9092,
    mongo_host="mongodb://root:root@localhost:27017/",
)

app = Skald(config)

app.register_task_worker(MySimpleWorker)

if __name__ == "__main__":
    app.run()