from skalds.proxy.kafka import KafkaConfig, KafkaProxy, KafkaTopic
from my_simple_worker import MySimpleDataModel, MySimpleWorker
from skalds.model.task import Task
from skalds.model.event import TaskEvent
from skalds.proxy.mongo import MongoConfig, MongoProxy
from skalds.repository.repository import TaskRepository


# 建立 Kafka 代理
kafka_config = KafkaConfig(
    host="127.0.0.1",
    port=9092,
)

kafka_proxy = KafkaProxy(kafka_config)

# 建立 MongoDB 代理
mongo_config = MongoConfig(
    host="mongodb://root:root@localhost:27017/",
)
mongo_proxy = MongoProxy(mongo_config=mongo_config)
task_rep = TaskRepository(mongo_proxy)

# 建立 Task 事件
task_attachment = MySimpleDataModel(
    rtspUrl="rtsp://example.com/stream",
    fixFrame=10
)
task = Task(
    id="task_123",
    class_name=MySimpleWorker.__name__,
    source="TestingScript",
    attachments=task_attachment
)

# 寫入 MongoDB
try:
    task_rep.create_task(task)
except Exception as e:
    print(e)

# 更新 executor
skald_id = "skald_123"
task_rep.update_executor(task.id, skald_id)

# 建立 Task 事件
task_event = TaskEvent(task_ids=[task.id])

# 發送 Task 事件
kafka_proxy.produce(KafkaTopic.TASK_ASSIGN, key=task.id, value=task_event.model_dump_json())