from skald import Skald
from skald.config.skald_config import SkaldConfig

config = SkaldConfig(
    log_level="DEBUG",
    redis_host="localhost",
    redis_port=6379,
    kafka_host="192.168.1.110",
    kafka_port=9092,
    mongo_host="192.168.1.110",
    mongo_port=27027,
    skald_mode="edge"
)

app = Skald(config)

if __name__ == "__main__":
    app.run()