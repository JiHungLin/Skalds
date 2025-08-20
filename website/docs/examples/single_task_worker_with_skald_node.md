# Skald Node

本範例展示如何在 Skalds 框架下，透過 Kafka 發送任務給以 Node 模式運行的 Skald，並由註冊的 TaskWorker 執行。  
完整原始碼參考：[GitHub 範例程式](https://github.com/JiHungLin/Skalds/tree/main/examples/single_task_worker_with_skald_node)

---

## 1. 定義 TaskWorker（建議可獨立運行）

:::tip 重點
1. **自訂的 DataModel 必須繼承 pydantic 的 `BaseModel`。**
2. **自訂的 TaskWorker 必須繼承 Skalds 的 `BaseTaskWorker`，並將自訂的 DataModel 作為泛型指定。**
3. **根據不同生命週期，請使用對應的 Decorator（`run_before_handler`, `run_main_handler`, `run_after_handler`, `update_event_handler`）來自訂邏輯。**
:::

與 Edge 模式相同，TaskWorker 建議加上 `if __name__ == "__main__"`，方便單獨測試。

**`my_simple_worker.py`**
```python
from skalds.worker.baseclass import BaseTaskWorker, run_before_handler, run_main_handler
from skalds.utils.logging import logger
from pydantic import BaseModel, Field, ConfigDict
import time

# 1. 自訂的 DataModel 必須繼承 pydantic 的 BaseModel
class MySimpleDataModel(BaseModel):
    rtsp_url: str = Field(..., description="RTSP stream URL", alias="rtspUrl")
    fix_frame: int = Field(..., description="Fix frame number", alias="fixFrame")
    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True
    )

# 2. 自訂的 TaskWorker 必須繼承 BaseTaskWorker，並將 DataModel 作為泛型指定
class MySimpleWorker(BaseTaskWorker[MySimpleDataModel]):
    def initialize(self, data: MySimpleDataModel) -> None:
        self.rtsp_url = data.rtsp_url
        self.fix_frame = data.fix_frame

    # 3. 依照不同生命週期，使用對應的 Decorator 來自訂邏輯
    @run_before_handler
    def before_run(self) -> None:
        logger.info(f"Starting MyWorker with RTSP URL: {self.rtsp_url}")

    @run_main_handler
    def main_run(self) -> None:
        for _ in range(30):
            logger.info(f"Running main logic for MyWorker")
            logger.info(f"RTSP URL: {self.rtsp_url}, Fix Frame: {self.fix_frame}")
            time.sleep(1)

if __name__ == "__main__":
    my_data = MySimpleDataModel(rtsp_url="rtsp://example.com/stream", fix_frame=10)
    my_worker = MySimpleWorker()
    my_worker.initialize(my_data)
    my_worker.start()
```

**補充說明：**
- 上述範例中，`MySimpleDataModel` 必須繼承自 `BaseModel`，以確保資料驗證與型別提示。
- `MySimpleWorker` 必須繼承自 `BaseTaskWorker`，並以泛型方式指定對應的 DataModel。
- 依照不同生命週期，請使用對應的 Decorator（如 `@run_before_handler`, `@run_main_handler`）來自訂執行邏輯。

**說明：**
- 可直接執行本檔案，單獨測試 Worker 行為。
- 實際運行時，Skalds 會自動注入任務參數。

---

## 2. 啟動 Node 模式 Skald

Node 模式適合由外部（如 Controller 或腳本）透過 Kafka 指派任務。

**`skald_node.py`**
```python
from skalds import Skald
from skalds.config.skald_config import SkaldConfig
from my_simple_worker import MySimpleWorker

config = SkaldConfig(
    skald_mode="node",  # 必須設為 "node"
    skald_id="skald_123", # 節點唯一識別碼，若省略則自動產生
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
- `skald_mode="node"` 必須，代表本節點由外部指派任務。
- `skald_id` 建議明確指定，便於任務分配與追蹤。
- 需正確設定 Kafka、MongoDB、Redis 等服務參數。

---

## 3. 透過 Kafka 發送任務

可用腳本將任務資料寫入 MongoDB，並透過 Kafka 發送任務事件給 Node。

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

## 4. 執行流程與注意事項

1. 啟動 Kafka、MongoDB、Redis 等必要服務。
2. 啟動 Node 節點：
   ```bash
   python skald_node.py
   ```
3. 執行任務發送腳本：
   ```bash
   python create_task_script.py
   ```
4. 觀察 Node 節點終端機，應可看到 Worker 執行日誌。

**注意事項：**
- `skald_id` 必須與腳本中指定的 executor 一致，否則任務不會被正確分配。
- 任務資料需先寫入 MongoDB，Skald Node 會自動查詢並執行。

---

## 5. 延伸閱讀

- [本範例完整原始碼](https://github.com/JiHungLin/Skalds/tree/main/examples/single_task_worker_with_skald_node)
- [快速入門：Edge 模式](../quickstart.md)
- [Skalds 架構與設計理念](../intro.md)

---

Skalds 讓你輕鬆串接 Kafka 任務流，打造高效能、可擴展的分散式任務平台！