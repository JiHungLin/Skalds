# 快速入門

本章節以「Edge 模式 + YAML 配置」為主軸，帶你在本機快速體驗 Skalds 框架如何以 YAML 管理並運行 TaskWorker。  
本教學範例完整原始碼可參考：[GitHub 範例程式](https://github.com/JiHungLin/Skalds/tree/main/examples/single_task_worker_define)

---
## 安裝套件

根據你的需求，請選擇安裝一般版或包含後端功能的進階版：

### 1. 一般安裝（僅需基本功能/Edge 模式）

適用於只需本地運算、YAML 配置與 TaskWorker 的使用者。

```bash
pip install skalds
```

### 2. 進階安裝（需後端整合，如 System Controller、API、監控等）

skalds[backend] 為分割出來的套件，包含所有後端相依元件（如 FastAPI，Monitor，Dispatcher 等）。

```bash
pip install "skalds[backend]"
```
---

## 1. 什麼是 Edge 模式？為何用 YAML？

- **Edge 模式**：Skalds 支援 Edge/Node 架構，本範例以 Edge 模式為例，適合單機或邊緣運算場景。
- **YAML 配置**：所有 TaskWorker 實例與參數集中於 YAML 檔，方便管理、熱更新與多 Worker 配置。

---

## 2. 定義你的 Task Worker（建議可獨立運行）

Skalds 透過「Task Worker」執行任務。建議每個 Worker 檔案都加上 `if __name__ == "__main__"`，可單獨測試邏輯，確保正確性。

**`my_simple_worker.py`**
```python
from skalds.worker.baseclass import BaseTaskWorker, run_before_handler, run_main_handler
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
        for _ in range(30):
            logger.info(f"Running main logic for MyWorker")
            logger.info(f"RTSP URL: {self.rtsp_url}, Fix Frame: {self.fix_frame}")
            time.sleep(1)

if __name__ == "__main__":
    # 建議：可直接執行本檔案，單獨測試 Worker 邏輯
    my_data = MySimpleDataModel(rtsp_url="rtsp://example.com/stream", fix_frame=10)
    my_worker = MySimpleWorker()
    my_worker.initialize(my_data)
    my_worker.start()
```
**說明：**
- `if __name__ == "__main__"` 讓你可直接 `python my_simple_worker.py` 測試 Worker 行為，無需啟動整個 Skalds 系統。
- 實際運行時，Skalds 會自動注入 YAML 參數。

---

## 3. 用 YAML 配置 TaskWorker

所有 Worker 實例與啟動參數集中於 YAML 檔，方便管理與批次調整。

**`all_workers.yml`**
```yaml
TaskWorkers:
  TaskWorker1:
    attachments:
      fix_frame: 10
      rtsp_url: rtsp://192.168.1.1/camera1
    className: MySimpleWorker
```
**說明：**
- `TaskWorkers` 下可定義多個 worker 實例。
- `attachments` 對應資料模型欄位，將自動注入至 worker。
- `className` 指定對應的 Python Worker 類別。

---

## 4. Edge 主程式：啟動 Skalds 並載入 YAML

**`skald_edge.py`**
```python
from skalds import Skald
from skalds.config.skald_config import SkaldConfig
from examples.single_task_worker_define.my_simple_worker import MySimpleWorker

config = SkaldConfig(
    skald_mode="edge",  # 必須設為 "edge"
    yaml_file="all_workers.yml",  # 指定 YAML 檔案路徑（建議用絕對或相對路徑）
    log_split_with_worker_id=True, # 可將TaskWorer的Log檔案獨立出來，便於debug
    # 以下為選用，依需求決定是否連接
    redis_host="localhost",
    redis_port=6379,
    kafka_host="127.0.0.1",
    kafka_port=9092,
    mongo_host="mongodb://root:root@localhost:27017/",
    log_level="DEBUG",
)

app = Skald(config)
app.register_task_worker(MySimpleWorker)

if __name__ == "__main__":
    app.run()
```
**說明與注意事項：**
- `skald_mode="edge"` 必須，代表本機/邊緣運算模式。
- `yaml_file` 必須，請確認路徑正確（可用絕對路徑或與主程式同目錄）。
- `redis_host`、`kafka_host`、`mongo_host` 為選用：
  - **Redis**：啟用後可同步心跳、任務狀態到 Redis，便於監控與多端協作。
  - **MongoDB**：可將 YAML 配置同步至資料庫，支援查詢與持久化。
  - **Kafka**：可接收來自 Kafka 的 Attachment 更新事件，實現動態參數熱更新。
- 若未提供這些服務，Skalds 仍可單機運行，但無法跨節點同步狀態。

---

## 5. 執行範例

1. 確認三個檔案（`my_simple_worker.py`、`all_workers.yml`、`skald_edge.py`）皆在同一目錄下，或調整路徑正確。
2. 若需狀態同步、事件流等功能，請先啟動 Redis、Kafka、MongoDB 等服務。
3. 執行啟動檔：

```bash
python skald_edge.py
```

你將在終端機看到 Worker 執行的日誌輸出，代表任務已成功啟動並運作。

---

## 6. 進階應用

- 可依需求擴充資料模型與執行邏輯，或定義多個 Worker。
- 更多 YAML 配置與進階功能，請參考[完整文件](./documents)與[範例程式](./examples)。
- 本教學完整原始碼：[GitHub 範例程式](https://github.com/JiHungLin/Skalds/tree/main/examples/single_task_worker_define)

---

Skalds 讓你以最少的程式碼，快速打造高效能、可擴展的分散式任務平台！
