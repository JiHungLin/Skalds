from skalds import Skalds
from skalds.config.skald_config import SkaldConfig

config = SkaldConfig(
    log_level="DEBUG",
    redis_host="localhost",
    redis_port=6379,
    kafka_host="192.168.1.110",
    kafka_port=9092,
    mongo_host="mongodb://localhost:27017/",
    skald_mode="edge"
)

app = Skalds(config)

if __name__ == "__main__":
    app.run()