# 更新 Attachments 並透過 Kafka 發布給 Skald 範例

本範例展示如何在 Skalds 框架下，動態更新任務的 Attachments，並透過 Kafka 發布更新事件給以 Node 模式運行的 Skald，讓 TaskWorker 能即時接收並應用新參數。  
完整原始碼參考：[GitHub 範例程式](https://github.com/JiHungLin/Skalds/tree/main/examples/update_task_worker_with_skald_node)

---

## 1. 定義支援更新的 TaskWorker

TaskWorker 需實作 `@update_event_handler`，以支援任務參數（Attachments）動態更新。

**`my_simple_worker.py`**
```python
from skalds.worker.baseclass import BaseTaskWorker, run_before_handler, run_main_handler, update_event_handler
from skalds.utils.logging import logger
from pydantic import BaseModel, Field, ConfigDict
import time

class MySimpleDataModel(BaseModel):
    rtsp_url: str = Field(..., description="RTSP stream URL", alias="rtspUrl")
    fix_frame: int = Field(..., description="Fix frame number", alias="fixFrame")
    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True
    )

class MySimpleWorker(BaseTaskWorker[MySimpleDataModel]):
    def initialize(self, data: MySimpleDataModel) -> None:
        self.rtsp_url = data.rtsp_url
        self.fix_frame = data.fix_frame

    @run_before_handler
    def before_run(self) -> None:
        logger.info(f"Starting MyWorker with RTSP URL: {self.rtsp_url}")

    @run_main_handler
    def main_run(self) -> None:
        for _ in range(300):
            logger.info(f"Running main logic for MyWorker")
            logger.info(f"RTSP URL: {self.rtsp_url}, Fix Frame: {self.fix_frame}")
            time.sleep(1)

    @update_event_handler
    def update_event(self, data: MySimpleDataModel) -> None:
        logger.info(f"Updating MyWorker with RTSP URL: {data.rtsp_url}, Fix Frame: {data.fix_frame}")
        self.rtsp_url = data.rtsp_url
        self.fix_frame = data.fix_frame

if __name__ == "__main__":
    my_data = MySimpleDataModel(rtsp_url="rtsp://example.com/stream", fix_frame=10)
    my_worker = MySimpleWorker()
    my_worker.initialize(my_data)
    my_worker.start()
```
**說明：**
- `@update_event_handler` 的 input 型別必須與 TaskWorker 當初定義的 Model 完全一致（本例為 `MySimpleDataModel`），格式需相符。
- 可直接執行本檔案，單獨測試 Worker 行為，但無法順利接收更新事件，更新需要先經過Skald確定有TaskWorker正在執行。

---

## 2. 啟動 Node 模式 Skald

**`skald_node.py`**
```python
from skalds import Skald
from skalds.config.skald_config import SkaldConfig
from my_simple_worker import MySimpleWorker

config = SkaldConfig(
    skald_mode="node",
    skald_id="skald_123", # 節點唯一識別碼
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
```
**說明：**
- `skald_mode="node"` 必須，代表本節點由外部指派與更新任務。
- **必須正確設定 MongoDB，因為 Skald 會以 Mongo 內的 Attachments 為主，進行任務參數的同步與更新。**
- 需正確設定 Kafka、MongoDB、Redis 等服務參數。

---

## 3. 建立任務（create_task_script.py）

先建立一個任務並寫入 MongoDB，再分配給指定 Node。

**`create_task_script.py`**
```python
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
```
**說明：**
- 先將任務資料寫入 MongoDB，再指定目標 Node（`skald_id`）。
- 透過 Kafka 發送 `TASK_ASSIGN` 事件，Node 端 Skald 會自動接收並執行任務。

---

## 4. 更新 Attachments 並發布（update_task_script.py）

可隨時更新任務 Attachments，並透過 Kafka 通知 Node 端 Worker 動態套用新參數。

**`update_task_script.py`**
```python
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

# 建立新的 Attachments（格式必須與 TaskWorker 的 Model 完全一致）
task_attachment = MySimpleDataModel(
    rtspUrl="rtsp://example.com/new_stream",
    fixFrame=60
)
task_id = "task_123"

# 更新 MongoDB
try:
    task_rep.update_attachments(task_id, task_attachment)
except Exception as e:
    print(e)

# 建立 Task 更新事件
task_event = TaskEvent(task_ids=[task_id])

# 發送更新事件
kafka_proxy.produce(KafkaTopic.TASK_UPDATE_ATTACHMENT, key=task_id, value=task_event.model_dump_json())
```
**說明：**
- **更新 Attachments 時，格式必須與 TaskWorker 的 Model 完全一致（如 MySimpleDataModel），否則 Worker 不會正確接收。**
- Skald 會以 MongoDB 內的 Attachments 為主，進行任務參數的同步與更新，**必須確保 Node 端 Skald 已正確連上 MongoDB**。

---

## 5. 執行流程與注意事項

1. 啟動 Kafka、MongoDB、Redis 等必要服務。
2. 啟動 Node 節點：
   ```bash
   python skald_node.py
   ```
3. 建立任務並分配：
   ```bash
   python create_task_script.py
   ```
4. 任務執行中，隨時可更新 Attachments：
   ```bash
   python update_task_script.py
   ```
5. 觀察 Node 節點終端機，應可看到 Worker 動態更新參數的日誌。

**注意事項：**
- `task_id` 必須一致，才能正確更新目標任務。
- Worker 必須實作 `@update_event_handler`，且 input 型別必須與 Model 完全一致。
- **Skald 會以 MongoDB 內的 Attachments 為主，請務必確認 Node 端 Skald 已正確連上 MongoDB，否則無法取得最新參數。**

---

## 6. 延伸閱讀

- [本範例完整原始碼](https://github.com/JiHungLin/Skalds/tree/main/examples/update_task_worker_with_skald_node)
- [單一任務指派 Node 範例](./single_task_worker_with_skald_node.md)
- [快速入門：Edge 模式](../quickstart.md)
- [Skalds 架構與設計理念](../intro.md)

---

Skalds 讓你輕鬆實現任務參數熱更新，打造高彈性、可擴展的分散式任務平台！