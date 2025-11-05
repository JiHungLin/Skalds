---
sidebar_position: 2
sidebar_label: 任務工作者（TaskWorker）
---

# 任務工作者（TaskWorker）詳細說明

TaskWorker 是 Skalds 系統中負責實際執行任務的核心元件。每個 TaskWorker 以獨立進程運作，具備彈性的生命週期管理、事件驅動參數更新、與 Kafka/Redis 整合能力。開發者可透過繼承基礎類別與註冊自訂處理器，輕鬆擴充與客製化任務邏輯。

---

## 設計理念與架構

- **獨立進程**：每個 TaskWorker 以 multiprocessing.Process 運作，確保資源隔離與高可靠性。
- **事件驅動**：支援動態參數更新與狀態同步，透過 Kafka/Redis 實現即時通訊與心跳監控。
- **生命週期鉤子**：提供 before、main、after、release 等多階段鉤子，允許自訂任務執行流程。
- **型別安全**：初始化與更新事件皆採用 Pydantic BaseModel，確保資料結構嚴謹。

---

## 核心類別與介面

### 1. 抽象基礎類別

- `AbstractTaskWorker[T]`  
  - 泛型 T 為任務資料型別（繼承自 Pydantic BaseModel）。
  - 主要生命週期方法：
    - `initialize(self, data: T)`: 初始化任務資料。
    - `_run_before(self)`: 任務前置作業。
    - `_run_main(self)`: 任務主邏輯。
    - `_run_after(self)`: 任務結束後處理。
    - `_release(self, *args)`: 資源釋放與終止。
    - `_error_handler(self, exc)`: 例外處理。
  - 支援自訂鉤子註冊（見下方裝飾器）。

### 2. 實作基礎類別

- `BaseTaskWorker[T]`  
  - 實作 Kafka/Redis 整合、心跳監控、訊息消費、錯誤回報等基礎設施。
  - 主要屬性：
    - `task_id`：任務唯一識別碼。
    - `task_type`：任務類型（類別名稱）。
    - `dependencies`：任務依賴列表。
  - 主要方法：
    - `_run_before`：初始化 Kafka/Redis 連線、啟動心跳與訊息消費執行緒。
    - `handle_update_message`：處理來自 Kafka 的任務更新事件，並呼叫自訂 handler。
    - `_run_after`：結束後停止心跳並標記完成。
    - `_error_handler`：錯誤時回報至 Redis 並推送失敗心跳。
    - `_release`：釋放所有資源、關閉連線、處理信號終止。

---

## 生命週期與運作流程

1. **初始化**  
   - Skalds 產生任務，建立 TaskWorker 實體並呼叫 `initialize(data: T)`。
   - 註冊自訂生命週期鉤子（如 @run_main_handler）。

2. **啟動與前置作業**  
   - 執行 `_run_before`，建立 Kafka/Redis 連線，啟動心跳與訊息消費執行緒。

3. **主邏輯執行**  
   - 執行 `_run_main` 或自訂 @run_main_handler，處理實際任務內容。

4. **動態參數更新**  
   - 透過 Kafka 接收更新事件，呼叫 @update_event_handler 處理新資料，實現熱更新。

5. **結束與清理**  
   - 執行 `_run_after`，停止心跳、標記完成。
   - 執行 `_release`，釋放資源、關閉連線、處理信號終止。

6. **錯誤處理**  
   - 任務異常時，執行 `_error_handler`，回報錯誤並推送失敗心跳。

---

## 主要裝飾器（Decorators）

- `@run_before_handler`：註冊前置作業鉤子。
- `@run_main_handler`：註冊主邏輯鉤子（必須實作）。
- `@run_after_handler`：註冊結束後處理鉤子。
- `@release_handler`：註冊資源釋放鉤子。
- `@update_event_handler`：註冊動態參數更新事件處理器，型別安全。

---

## 資料結構與型別

### ModeEnum 執行模式

- `ACTIVE`：透過 YAML 配置主動載入並持續執行的任務，常用於長駐型任務或需要立即啟動的工作。
- `PASSIVE`：由中心調度系統動態分配給最適合的 Skald 節點執行，適合依需求觸發的任務。
- `PASSIVE_PROCESS`：專供單機 `SingleProcess` 模式使用，讓任務在同一個常駐進程中運行並保持狀態，執行狀態與主系統無強制綁定，可另外透過k8、docker等方式自訂。

### Task 定義（來自 [`skalds/model/task.py`](https://github.com/JiHungLin/skalds/blob/main/skalds/model/task.py)）

| 欄位名稱             | 型別                    | 說明                                                         | 範例                                                         |
|----------------------|-------------------------|--------------------------------------------------------------|--------------------------------------------------------------|
| id                   | str                     | 任務唯一識別碼                                               | "task_123"                                                   |
| class_name           | str | 對應 TaskWorker 類別名稱                                     | "MyWorker"                                                   |
| source               | str                     | 任務來源（如 YAML、MongoDB）                                 | "YAML"                                                       |
| name                 | Optional[str]           | 任務名稱（可選）                                             | "影像分析任務"                                               |
| description          | Optional[str]           | 任務描述（可選）                                             | "處理 RTSP 影像流"                                           |
| executor             | Optional[str]           | 執行者（如 skalds ID，可選）                                 | "skalds-1"                                                   |
| dependencies         | Optional[List[str]]     | 依賴任務 ID 列表（可選）                                     | ["task_001", "task_002"]                                     |
| mode                 | ModeEnum                | 任務執行模式，對應 `ModeEnum` 三種取值                       | "PassiveProcess"                                             |
| create_date_time     | int | 建立時間（毫秒）                                         | 1724131200000                                                |
| update_date_time     | int | 最後更新時間（毫秒）                                     | 1724131300000                                                |
| deadline_date_time   | int | 截止時間（毫秒）                                       | 1724736000000                                                |
| lifecycle_status     | TaskLifecycleStatus | 任務生命週期狀態 | "Running" |
| is_persistent        | bool                    | 是否為常駐任務，僅在 `single_process` 模式下生效；`true` 表示常駐（類似 Deployment），`false` 表示一次性任務（類似 Job/CronJob） | true                                                         |
| priority             | int                     | 優先權（0~10，預設0）                                        | 5                                                            |
| attachments          | Optional[BaseModel]     | 任務參數（Pydantic BaseModel 實例，依任務類型自訂）           | MyDataModel(rtsp_url="...", fix_frame=10)                    |
#### 任務生命週期狀態（TaskLifecycleStatus）列表

- **Created**：任務已建立，尚未分配
- **Assigning**：任務分配中
- **Running**：任務執行中
- **Paused**：任務暫停
- **Finished**：任務已完成
- **Failed**：任務執行失敗
- **Cancelled**：任務已取消

### TaskWorker 資料流

- 初始化與更新皆以 `attachments` 欄位傳遞，確保型別一致。
- 任務狀態、心跳、錯誤訊息皆同步至 Redis，並可由 System Controller 監控。

---

## 自訂 TaskWorker 實作範例

### 1. 定義資料模型

```python
from pydantic import BaseModel, Field, ConfigDict

class MyDataModel(BaseModel):
    rtsp_url: str = Field(..., description="RTSP stream URL", alias="rtspUrl")
    fix_frame: int = Field(..., description="Fix frame number", alias="fixFrame")
    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)
```

### 2. 實作自訂 TaskWorker

```python
from skalds.worker.baseclass import BaseTaskWorker, run_before_handler, run_main_handler, update_event_handler
from skalds.utils.logging import logger

class MyWorker(BaseTaskWorker[MyDataModel]):
    def initialize(self, data: MyDataModel) -> None:
        self.rtsp_url = data.rtsp_url
        self.fix_frame = data.fix_frame

    @run_before_handler
    def before_run(self) -> None:
        logger.info(f"Starting MyWorker with RTSP URL: {self.rtsp_url}")

    @run_main_handler
    def main_run(self) -> None:
        for _ in range(10):
            logger.info(f"RTSP URL: {self.rtsp_url}, Fix Frame: {self.fix_frame}")
            time.sleep(1)

    @update_event_handler
    def update_event(self, event_data: MyDataModel) -> None:
        logger.info(f"Updating event for MyWorker with data: {event_data}")
        self.rtsp_url = event_data.rtsp_url
        self.fix_frame = event_data.fix_frame
```

### 3. YAML 配置範例

```yaml
TaskWorkers:
  TaskWorker1:
    isPersistent: true
    attachments:
      fixFrame: 30
      rtspUrl: rtsp://192.168.1.1/camera1
    className: MyWorker
```

> `isPersistent` 僅在 `single_process` 模式下生效，決定任務是否常駐（對應 Deployment）或一次性（適合 Job/CronJob）。

### 4. 註冊與啟動

```python
from skalds import Skalds
from skalds.config.skald_config import SkaldConfig

config = SkaldConfig(
    skald_mode="edge",
    yaml_file="all_workers.yml",
    redis_host="localhost",
    kafka_host="127.0.0.1",
    mongo_host="mongodb://root:root@localhost:27017/"
)

app = Skalds(config)
app.register_task_worker(MyWorker)
app.run()
```

---

## 進階特性

- **多階段任務與重試**：可自訂 main handler 支援多階段執行與失敗重試。
- **動態參數熱更新**：@update_event_handler 支援任務執行中即時調整參數。
- **例外與終止處理**：自訂 _error_handler 與 _release 可精細控制異常與資源釋放。
- **依賴管理**：Task 支援 dependencies 欄位，實現任務間依賴與順序控制。

---

## 參考範例

- [`examples/single_task_worker_define/`](../../examples/single_task_worker_define/)
- [`examples/single_task_worker_with_skald_node/`](../../examples/single_task_worker_with_skald_node/)
- [`examples/update_task_worker_with_skald_node/`](../../examples/update_task_worker_with_skald_node/)

---

TaskWorker 架構讓開發者能以最小成本擴充任務邏輯，並享有高可靠、可監控、易維護的分散式任務執行環境。
