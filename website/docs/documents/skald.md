---
sidebar_position: 6
sidebar_label: Skald
---

# Skald 節點（Skald Node/Edge）技術說明

Skald 是 Skalds 分散式任務調度系統的**任務生成與調度核心模組**，負責任務的初始化、分配、與 TaskWorker 的管理。Skald 支援兩種運作模式：**Edge（邊緣節點）**與**Node（工作節點）**，可依據應用場景彈性部署，實現高效能、可擴展的任務調度與執行。

---

## 1. Skald 在架構中的定位

Skalds 系統架構如下：

- **System Controller**：系統核心控制器，負責 API、監控、調度與狀態管理。
- **Task Generator（Skald）**：負責任務生成、分配與 TaskWorker 管理，支援 Edge/Node 模式。
- **Task Worker**：實際執行任務的獨立進程。
- **Event Queue**：基於 Kafka 的事件佇列，實現模組間高效通訊。
- **Cache Memory**：Redis 快取，負責任務狀態、心跳等高頻資料同步。
- **Disk Storage**：MongoDB 永久儲存任務資料。

Skald 作為 Task Generator，承上（System Controller/Dispatcher），啟動與管理下游 TaskWorker，並與 Event Queue、Cache Memory 密切互動。

---

## 2. Skald 運作模式

### Edge 模式（skald_mode="edge"）

- 適用於**批量、靜態任務**場景。
- 啟動時自動載入 YAML 配置檔，批次註冊多個 TaskWorker。
- 適合大規模、預先規劃的任務執行。

### Node 模式（skald_mode="node"）

- 適用於**動態任務分配**場景。
- 任務由 System Controller 動態分配，Skald 根據事件建立 TaskWorker。
- 適合彈性擴展、即時任務調度。

---

## 3. 啟動流程與配置

### 3.1 SkaldConfig 參數

Skald 啟動時需傳入 [`SkaldConfig`](https://github.com/JiHungLin/skalds/blob/main/skalds/config/skald_config.py) 物件，支援下列主要參數：

- `skald_id`：Skald 節點唯一識別碼
- `skald_mode`：運作模式（"edge" 或 "node"）
- `yaml_file`：YAML 配置檔路徑（Edge 模式需指定）
- `redis_host`、`kafka_host`、`mongo_host`：外部服務連線資訊
- 其他日誌、認證、重試等參數

詳細參數請參考 [`systemconfig.py`](https://github.com/JiHungLin/skalds/blob/main/skalds/config/systemconfig.py) 與 `.env.example`。

### 3.2 啟動範例

#### Edge 節點

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

#### Node 節點

```python
config = SkaldConfig(
    skald_mode="node",
    redis_host="localhost",
    kafka_host="127.0.0.1",
    mongo_host="mongodb://root:root@localhost:27017/"
)

app = Skalds(config)
app.register_task_worker(MyWorker)
app.run()
```

---

## 4. Skald 核心流程與生命週期

### 4.1 任務建立流程

1. Skald 啟動，向 Redis 註冊自身 ID 與心跳。
2. System Controller 監控可用 Skald 節點。
3. 接收任務建立事件（Node 模式由 Event Queue 觸發，Edge 模式由 YAML 載入）。
4. Skald 根據任務細節建立 TaskWorker 實體。
5. TaskWorker 註冊狀態、心跳至 Redis，進入執行狀態。

### 4.2 任務更新與取消

- 任務更新：System Controller 發佈更新事件，Skald 轉發至對應 TaskWorker，支援動態參數熱更新。
- 任務取消：廣播取消事件，Skald 關閉對應 TaskWorker，釋放資源。

詳細流程請參考[任務生命週期](./task_lifecycle.md)。

---

## 5. Skald 主要功能與實作重點

### 5.1 多協定整合

- **Kafka**：事件佇列，負責任務分配、更新、取消等事件流轉。
- **Redis**：快取任務狀態、心跳、錯誤訊息，支援高效監控與調度。
- **MongoDB**：持久化任務資料，支援查詢與統計。

### 5.2 TaskWorker 管理

- 支援多型別 TaskWorker 註冊與動態建立。
- 生命週期管理（啟動、監控、終止、錯誤處理）。
- 支援 YAML 批量配置（Edge）、事件驅動動態分配（Node）。

### 5.3 日誌與監控

- 整合多層級日誌（Loguru），支援自動分割、保留、清理。
- 心跳與活動狀態自動同步至 Redis，便於 System Controller 監控。

---

## 6. YAML 配置說明（Edge 模式）

YAML 配置檔用於 Edge 節點批量定義 TaskWorker，結構如下：

```yaml
TaskWorkers:
  TaskWorker1:
    attachments:
      fixFrame: 30
      rtspUrl: rtsp://192.168.1.1/camera1
    className: MyWorker
  TaskWorker2:
    attachments:
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

- `TaskWorker1`、`TaskWorker2`：每個工作者的唯一名稱（即任務 ID）。
- `attachments`：初始化參數，需對應 Python 類別的 Pydantic 資料模型。
- `className`：對應已註冊於 Skalds 的 Python 類別名稱。

詳細說明請參考[《YAML 配置檔說明》](./yaml_config.md)。

---

## 7. Skald 主要程式碼結構

### 7.1 Skald 主類別

參考 [skalds/skald.py (GitHub)](https://github.com/JiHungLin/skalds/blob/main/skalds/skald.py)：

- `__init__`：初始化各項服務連線、日誌、模式判斷。
- `register_task_worker`：註冊自訂 TaskWorker 類別。
- `run`：主執行流程，包含：
  - 設定心跳與活動註冊（Redis）
  - 啟動 TaskWorkerManager，負責 Kafka 消費與 TaskWorker 管理
  - Edge 模式自動載入 YAML 配置
  - 訊號處理與優雅關閉

### 7.2 配置與環境變數

- [skalds/config/skald_config.py (GitHub)](https://github.com/JiHungLin/skalds/blob/main/skalds/config/skald_config.py)：SkaldConfig 參數定義
- [skalds/config/systemconfig.py (GitHub)](https://github.com/JiHungLin/skalds/blob/main/skalds/config/systemconfig.py)：SystemConfig 預設值與環境變數對應
- [skalds/config/_enum.py (GitHub)](https://github.com/JiHungLin/skalds/blob/main/skalds/config/_enum.py)：模式、環境、日誌等列舉型別

---

## 8. Skald 與其他模組的互動

- **TaskWorker**：Skald 動態建立與管理 TaskWorker，支援多型別與動態參數更新，詳見[TaskWorker 說明](./task_worker.md)。
- **Event Queue**：透過 Kafka 實現任務分配、更新、取消等事件流轉，詳見[EventQueue 說明](./event_queue.md)。
- **Cache Memory**：所有狀態、心跳、錯誤訊息皆同步至 Redis，詳見[Cache Memory 說明](./cache_memory.md)。

---

## 9. 進階特性

- **多階段任務與重試**：TaskWorker 支援多階段執行與失敗重試。
- **動態參數熱更新**：任務執行中可即時調整參數。
- **高可用設計**：支援多副本、分片、故障自動恢復。
- **型別安全**：所有任務資料與事件皆採用 Pydantic BaseModel，確保資料結構嚴謹。

---

## 10. 參考文件與延伸閱讀

- [Skalds 架構與模組細節](../intro.md)
- [任務生命週期與事件流](./task_lifecycle.md)
- [TaskWorker 詳細說明](./task_worker.md)
- [YAML 配置說明](./yaml_config.md)
- [Cache Memory 快取說明](./cache_memory.md)
- [EventQueue 事件佇列說明](./event_queue.md)

---

Skald 節點是 Skalds 分散式任務調度系統的核心，正確配置與善用 Skald 能大幅提升系統的彈性、效能與可維護性。