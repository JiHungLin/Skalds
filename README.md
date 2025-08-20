# Skalds


[![Python Version](https://img.shields.io/pypi/pyversions/skalds)](https://www.python.org/downloads/)
[![PyPI Version](https://img.shields.io/pypi/v/skalds)](https://pypi.org/project/skalds/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/JiHungLin/skalds/blob/main/LICENSE)
[![Documentation](https://img.shields.io/badge/docs-latest-brightgreen)](https://jihunglin.github.io/skalds/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/JiHungLin/skalds)


**一個事件驅動的模組化分散式任務調度與執行系統。**

靈感來自北歐神話中的 Skalds（吟遊詩人與使者），Skalds 專為高併發後端任務管理而設計，透過事件驅動的通訊機制與靈活的資源配置，實現高效能、可擴展的任務調度與執行。

---

## 主要特色

- **模組化架構**
  將系統劃分為三大核心模組（Skald、Monitor、Dispatcher）及其支援模組，各司其職，實現高效能的分散式任務處理。

- **事件驅動通訊**
  採用發佈/訂閱（Pub/Sub）機制的事件佇列，實現模組間的鬆耦合互動，提高系統的彈性與可擴展能力。

- **智能資源調度**
  結合 Task Generator (Skald) 與 Dispatcher 的優勢，實現基於資源感知的智能任務分配，支援容器化平台的自動擴容。

- **完整的監控與管理**
  透過 Monitor 模組提供全方位的系統監控，搭配健全的任務生命週期管理，確保系統穩定運行與資源最佳利用。

---

## 系統模組總覽

### 系統架構圖

![Skalds Architecture](architecture.jpg)

### 模組說明

| 模組               | 功能說明                                                                                            |
| ------------------ | ------------------------------------------------------------------------------------------------- |
| **System Controller** | 系統核心控制器，整合以下功能：<br>- RESTful API 介面：提供任務建立與控制<br>- 系統監控 (Monitor)：追蹤系統效能與資源使用<br>- 任務調度 (Dispatcher)：智能分配任務與負載平衡<br>- 心跳監控：追蹤 Task Generator 與 Worker 狀態<br>- 狀態管理：統一管理任務狀態與系統配置 |
| **└─ Monitor**     | System Controller 的監控模組，負責：<br>- 系統效能監控與指標收集<br>- 任務執行狀態追蹤<br>- 資源使用率分析<br>- 警報觸發與通知管理 |
| **└─ Dispatcher**  | System Controller 的調度模組，負責：<br>- 智能任務分配策略<br>- 動態負載平衡<br>- 資源使用優化<br>- 緊急任務優先處理 |
| **Task Generator(Skald)**    | 核心任務生成與調度系統。支援邊緣(Edge)與節點(Node)兩種運行模式，通過事件驅動機制實現任務的動態分配與資源管理。特色功能包括：<br>- 彈性配置：支援 YAML 檔案配置工作者(Worker)參數<br>- 自動註冊：簡化的工作者註冊機制，支援多種任務類型<br>- 狀態追蹤：整合 Redis 與 MongoDB 實現任務狀態的可靠追蹤<br>- 錯誤處理：提供任務重試機制與完整的錯誤處理流程 |
| **Task Worker**       | 使用獨立資源（CPU、RAM）執行具體任務，擷取媒體資料來源含 RTSP、快取記憶體(Cache Memory)、磁碟(Storage)，並將結果存入快取或磁碟中。支援：<br>- 多階段任務執行<br>- 自動重試機制<br>- 彈性配置選項 |
| **Event Queue**       | 基於 Kafka 3.9.0+ 的事件通訊系統，運用 Pub/Sub 機制實現 System Controller、Task Generator 與 Task Worker 間的消息傳遞，具備高吞吐量和可靠性。無需 Zookeeper，簡化部署與維護。                      |
| **Cache Memory**      | 採用 Redis 8+ 作為快取引擎，儲存高頻率讀寫的數據以提升系統效能。支援進階特性如每個雜湊欄位的 TTL 控制，實現精細的數據生命週期管理。                                                             |
| **Disk Storage**      | 使用 MongoDB 7.0+ 進行持久化資料存儲，包括統計數據、復原資料及錄製資料。提供強大的查詢能力、自動分片，以及容錯與資料耐久性保障。                                          |

## System Controller 啟動說明

System Controller 為系統核心控制器，啟動前請先依下列步驟設定環境變數並啟動服務。

### 1. 設定環境變數

請參考專案根目錄的 `.env.example`，複製為 `.env` 並根據實際需求調整內容：

```bash
cp .env.example .env
```

#### 主要環境變數說明

- **System Controller 設定**
  - `SYSTEM_CONTROLLER_MODE`：運行模式（如 MONITOR）

- **基本設定**
  - `LOG_LEVEL`：日誌等級（如 DEBUG、INFO）
  - `LOG_RETENTION`：日誌保留天數
  - `LOG_ROTATION_MB`：單一日誌檔案最大容量（MB）

- **Redis 設定**
  - `REDIS_HOST`、`REDIS_PORT`、`REDIS_PASSWORD`、`REDIS_SYNC_PERIOD`

- **Kafka 設定**
  - `KAFKA_HOST`、`KAFKA_PORT`、`KAFKA_USERNAME`、`KAFKA_PASSWORD`
  - `KAFKA_TOPIC_PARTITIONS`、`KAFKA_REPLICATION_FACTOR`

- **Mongo 設定**
  - `MONGO_HOST`：MongoDB 連線字串
  - `DB_NAME`：資料庫名稱

> 詳細參數請參閱 `.env.example`。

### 2. 啟動 System Controller

安裝好相依套件與設定好 `.env` 後，於專案根目錄執行下列指令啟動服務：

```bash
python -m skalds.system_controller.main
```

服務啟動後，將自動載入 `.env` 設定並啟動 RESTful API、監控與調度等功能。
啟動完成後，可於瀏覽器開啟 [http://127.0.0.1:8000/](http://127.0.0.1:8000/) 進行操作與管理。

---
## 模組互動

系統三大核心模組（Skalds、Monitor、Dispatcher）協同運作，構建完整的任務生命週期：

1. **Skalds (Task Generator)**
   - 負責任務的初始化與生成
   - 管理工作者（Worker）的註冊與配置
   - 透過事件佇列與其他模組通訊

2. **Monitor**
   - 持續監控系統狀態與效能
   - 收集並分析資源使用情況
   - 觸發必要的警報與通知

3. **Dispatcher**
   - 基於 Monitor 提供的系統資訊進行智能調度
   - 實現動態負載平衡
   - 處理緊急任務優先級

---

## 架構亮點

- **鬆耦合設計**  
  各模組透過事件佇列通訊，強化系統擴展性與維護性。

- **資源感知的排程**  
  Task Generator 依據實時資源狀態動態分配任務，提升使用效率。

- **狀態同步機制**  
  雙向的狀態更新確保任務生命週期的準確追蹤。

- **動態參數更新**  
  支援參數熱更新與熱重載，降低系統重啟時間。

- **高可用設計**  
  事件佇列及存儲採用多副本機制，保障系統在故障時仍保持穩定運行。


---

## 使用範例

### 1. 建立工作者（Worker）

#### 簡單工作者
```python
from skalds.worker.baseclass import BaseTaskWorker, run_before_handler, run_main_handler, update_event_handler
from skalds.utils.logging import logger
from pydantic import BaseModel, Field, ConfigDict
import time

class MyDataModel(BaseModel):
    rtsp_url: str = Field(..., description="RTSP stream URL", alias="rtspUrl")
    fix_frame: int = Field(..., description="Fix frame number", alias="fixFrame")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True
    )

class MyWorker(BaseTaskWorker[MyDataModel]):
    def initialize(self, data: MyDataModel) -> None:
        self.rtsp_url = data.rtsp_url
        self.fix_frame = data.fix_frame

    @run_before_handler
    def before_run(self) -> None:
        logger.info(f"Starting MyWorker with RTSP URL: {self.rtsp_url}")

    @run_main_handler
    def main_run(self) -> None:
        for _ in range(300*10):
            logger.info(f"Running main logic for MyWorker")
            logger.info(f"RTSP URL: {self.rtsp_url}, Fix Frame: {self.fix_frame}")
            time.sleep(1)

    @update_event_handler
    def update_event(self, event_data: MyDataModel) -> None:
        logger.info(f"Updating event for MyWorker with data: {event_data}")
        self.rtsp_url = event_data.rtsp_url
        self.fix_frame = event_data.fix_frame

if __name__ == "__main__":
    my_data = MyDataModel(rtsp_url="rtsp://example.com/stream", fix_frame=10)
    my_worker = MyWorker()
    my_worker.initialize(my_data)
    my_worker.start()
```

> 補充說明：
> - `update_event_handler` 可用於動態更新任務參數。
> - `model_config` 設定可提升 Pydantic 資料模型的彈性。
> - 此範例支援直接以 `python my_worker.py` 執行進行測試。

#### 複雜工作者
```python
class ComplexWorker(BaseTaskWorker[ComplexDataModel]):
    """支援多階段執行、重試機制與特性切換的進階工作者"""
    
    def initialize(self, data: ComplexDataModel) -> None:
        self.job_id = data.job_id
        self.retries = data.retries
        self.sub_tasks = data.sub_tasks

    @run_before_handler
    def before_run(self) -> None:
        # 前置檢查
        if not self.sub_tasks:
            raise RuntimeError("No sub-tasks configured")

    @run_main_handler
    def main_run(self) -> None:
        # 執行子任務並支援重試
        for subtask in self.sub_tasks:
            self._execute_subtask(subtask)
```

### 2. 配置工作者（YAML）

```yaml
TaskWorkers:
  TaskWorker1:
    attachments:
      fixFrame: 30
      rtspUrl: rtsp://192.168.1.1/camera1
    className: MyWorker
  
  TaskWorker2:
    attachments:
      enable_feature_x: true
      jobId: job-12345
      retries: 2
      sub_tasks:
        - name: Download Data
          duration: 1.5
          fail_chance: 0.2
        - name: Process Data
          duration: 2.0
          fail_chance: 0.1
    className: ComplexWorker
```

### 3. 啟動 Skalds 服務

#### Edge 模式（邊緣節點）
```python
from skalds import Skalds
from skalds.config.skald_config import SkaldConfig

config = SkaldConfig(
    skald_mode="edge",
    yaml_file="all_workers.yml",
    log_split_with_worker_id=True,
    redis_host="localhost",
    kafka_host="127.0.0.1",
    mongo_host="mongodb://root:root@localhost:27017/"
)

app = Skalds(config)
app.register_task_worker(MyWorker)
app.register_task_worker(ComplexWorker)
app.run()
```

#### Node 模式（工作節點）
```python
config = SkaldConfig(
    skald_mode="node",
    log_split_with_worker_id=True,
    redis_host="localhost",
    kafka_host="127.0.0.1",
    mongo_host="mongodb://root:root@localhost:27017/"
)

app = Skalds(config)
app.register_task_worker(MyWorker)
app.run()
```

### 4. 建立與分配任務

```python
from skalds.model.task import Task
from skalds.model.event import TaskEvent

# 建立任務
new_task_attachment = MyDataModel(rtsp_url="rtsp://example.com/stream", fix_frame=30)
new_task = Task(
    id="task_1",
    class_name=MyWorker.__name__,
    source="Test",
    attachments=new_task_attachment
)

# 儲存任務
task_rep.create_task(new_task)

# 觸發任務分配
task_event = TaskEvent(task_ids=[new_task.id])
kafka_proxy.produce(KafkaTopic.TASK_ASSIGN,
    key=new_task.id,
    value=task_event.model_dump_json()
)
```

---

## Getting Started

#### 1. 安裝 Python dependencies

```bash
pip install -e .
```

#### 2. 啟動 Kafka, Redis, and MongoDB (使用 Docker)

You can quickly start all required services using Docker Compose:

```yaml
version: '3.8'
services:
  mongo:
    image: mongo
    restart: always
    ports:
      - "27027:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: {Username}
      MONGO_INITDB_ROOT_PASSWORD: {Password}
    volumes:
      - $HOME/mongodb:/data/db

  kafka-broker:
    image: 'bitnami/kafka:3.9.0'
    restart: always
    ports:
      - "9092:9092"
    environment:
      - KAFKA_CFG_NODE_ID=0
      - KAFKA_CFG_PROCESS_ROLES=controller,broker
      - KAFKA_CFG_LISTENERS=PLAINTEXT://0.0.0.0:9092,CONTROLLER://:9093
      - KAFKA_CFG_ADVERTISED_LISTENERS=PLAINTEXT://127.0.0.1:9092
      - KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
      - KAFKA_CFG_CONTROLLER_QUORUM_VOTERS=0@kafka-broker:9093
      - KAFKA_CFG_CONTROLLER_LISTENER_NAMES=CONTROLLER
      - KAFKA_CFG_INTER_BROKER_LISTENER_NAME=PLAINTEXT
      # Set retention time to 30 minutes
      - KAFKA_CFG_LOG_RETENTION_HOURS=0
      - KAFKA_CFG_LOG_RETENTION_MINUTES=30

  redis:
    image: redis:8
    restart: always
    ports:
      - "6379:6379"
```

> Save this as `docker-compose.yml` and start all services with:
>
> ```bash
> docker-compose up -d
> ```

> **Note:** If you already have Redis, MongoDB, or Kafka installed locally, you can use your existing services. Adjust connection settings as needed.
>
> **Recommended versions:**
> - Redis: 7.4+ (Requires 7.4 or above to support per-hash-field TTL)
> - MongoDB: 7.0
> - Kafka: 3.9.0 (no Zookeeper required)

---

## 適用場景（Use Cases）

- **AI 影像辨識與長時間運算任務**  
  適用於需要大量運算資源且任務執行時間較長的工作，比如影像分析、視訊流處理、深度學習推論等。

- **高併發後端服務**  
  支援動態擴展的後端服務架構，適合負載波動大且需快速調整資源的場景，如大型 Web 服務、數據處理流水線。

- **即時任務管理**  
  提供靈活的任務控制能力，支持任務的暫停、取消與動態更新，滿足需要即時調度與變更的業務需求。

---

## License

MIT License

Copyright (c) 2025 JiHungLin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## 關於名稱（About the Name）

本專案名稱 **Skalds** 源自北歐神話中的「吟遊詩人」（Skalds）。  
在古代北歐文化中，Skalds 扮演著故事傳述者與使者的角色，負責保存知識並傳達資訊。

這個命名正好呼應了系統核心的設計理念：  
透過**事件驅動的通訊機制**，在分散式架構中負責**任務調度與資訊流轉**，如同 Skalds 一樣靈活且高效地承載並傳遞任務狀態與資料。

---

For more details, see the documentation for each service:
- [Redis Quick Start](https://hub.docker.com/_/redis)
- [MongoDB Quick Start](https://hub.docker.com/_/mongo)
- [Kafka Quick Start](https://hub.docker.com/r/bitnami/kafka)
