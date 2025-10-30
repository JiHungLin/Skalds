# Skalds 框架介紹

Skalds 是一套**事件驅動的模組化分散式任務調度與執行系統**，靈感來自北歐神話中的吟遊詩人（Skalds），專為高併發、可擴展的後端任務管理而設計。Skalds 以鬆耦合架構、彈性資源調度與完整監控為核心，適用於 AI 運算、影像分析、即時資料處理等多種場景。

---

## 設計理念

Skalds 旨在解決現代分散式任務管理的三大挑戰：
- **高併發與高效能**：支援大量任務並行執行，動態調度資源。
- **模組化與可擴展**：各模組獨立、可插拔，易於擴充與維護。
- **事件驅動與鬆耦合**：採用 Pub/Sub 機制，模組間互動靈活，降低耦合度。

---

## 架構總覽

![Skalds Architecture](../../architecture.jpg)

Skalds 系統由三大核心模組與多個支援模組組成：

| 模組 | 主要職責 |
|------|----------|
| **System Controller** | 系統核心控制器，整合 API、監控、調度、心跳與狀態管理 |
| **Monitor** | 系統效能監控、資源分析、任務狀態追蹤、警報通知 |
| **Dispatcher** | 智能任務分配、動態負載平衡、資源優化 |
| **Task Generator (Skald)** | 任務生成與調度，支援 Edge/Node 模式，彈性配置與自動註冊 |
| **Task Worker** | 實際執行任務，支援多階段、重試、動態參數更新 |
| **Event Queue** | 基於 Kafka 的事件佇列，實現高效 Pub/Sub 通訊 |
| **Cache Memory** | Redis 快取，支援高頻資料與精細 TTL 控制 |
| **Disk Storage** | MongoDB 永久儲存，支援查詢、分片與容錯 |

---

## 核心特性

- **模組化架構**：三大核心模組（Skalds、Monitor、Dispatcher）分工明確，易於擴展。
- **事件驅動通訊**：所有模組透過 Kafka 事件佇列進行鬆耦合互動。
- **智能資源調度**：根據即時資源狀態自動分配任務，支援容器化自動擴容。
- **完整監控與管理**：Monitor 模組提供全方位監控與任務生命週期管理。
- **彈性配置與熱更新**：支援 YAML 配置、參數熱重載，降低維運成本。
- **高可用設計**：多副本、分片、故障自動恢復，確保穩定運行。

---

## 典型應用場景

- **AI 影像辨識與長時間運算**：如視訊流分析、深度學習推論等需大量資源的任務。
- **高併發後端服務**：動態擴展、負載波動大的 Web 服務或資料處理流水線。
- **即時任務管理**：需即時調度、暫停、取消或動態更新的業務流程。

---

## 快速範例

### 1. 定義自訂 Worker

```python
from skalds.worker.baseclass import BaseTaskWorker, run_before_handler, run_main_handler, update_event_handler
from pydantic import BaseModel, Field, ConfigDict
import time

class MyDataModel(BaseModel):
    rtsp_url: str = Field(..., alias="rtspUrl")
    fix_frame: int = Field(..., alias="fixFrame")
    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

class MyWorker(BaseTaskWorker[MyDataModel]):
    def initialize(self, data: MyDataModel) -> None:
        self.rtsp_url = data.rtsp_url
        self.fix_frame = data.fix_frame

    @run_before_handler
    def before_run(self) -> None:
        print(f"Starting MyWorker with RTSP URL: {self.rtsp_url}")

    @run_main_handler
    def main_run(self) -> None:
        for _ in range(10):
            print(f"RTSP URL: {self.rtsp_url}, Fix Frame: {self.fix_frame}")
            time.sleep(1)

    @update_event_handler
    def update_event(self, event_data: MyDataModel) -> None:
        self.rtsp_url = event_data.rtsp_url
        self.fix_frame = event_data.fix_frame
```

### 2. YAML 配置多個 Worker

```yaml
TaskWorkers:
  TaskWorker1:
    isPersistent: true
    attachments:
      fix_frame: 10
      rtsp_url: rtsp://192.168.1.1/camera1
    className: MyWorker
  TaskWorker2:
    isPersistent: false
    attachments:
      enable_feature_x: true
      job_id: job-12345
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

> `isPersistent` 旗標僅在 `single_process` 模式生效，協助區分長期常駐任務（Deployment）與一次性任務（Job/CronJob）。

### 3. 啟動 Skalds（Edge/Node）

```python
from skalds import Skalds
from skalds.config.skald_config import SkaldConfig
from my_worker import MyWorker
from complex_worker import ComplexWorker

config = SkaldConfig(
    skald_mode="edge",  # 或 "node"
    yaml_file="all_workers.yml",
    redis_host="localhost",
    kafka_host="127.0.0.1",
    mongo_host="mongodb://root:root@localhost:27017/"
)

app = Skalds(config)
app.register_task_worker(MyWorker)
app.register_task_worker(ComplexWorker)
app.run()
```

---

## 進一步閱讀

- [快速開始](./quickstart.md)
- [系統架構與模組細節](./documents)
- [任務生命週期與事件流](./documents/task_lifecycle.md)
- [YAML 配置範例](./documents/yaml_config.md)

---

Skalds 讓你輕鬆打造高效能、可擴展的分散式任務平台，無論是 AI 運算、資料處理還是即時控制，都能靈活應對。
