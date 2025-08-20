---
sidebar_position: 1
sidebar_label: Monitor
---

# SystemController Monitor 模組技術說明

SystemController 的 **Monitor** 模組是 Skalds 分散式任務調度系統的核心監控組件，負責即時追蹤 Skalds（Task Generator）與 TaskWorker 的狀態、心跳、任務執行狀態、資源使用率等，並透過 Dashboard 與 SSE（Server-Sent Events）提供全方位的系統可觀測性。Monitor 模組可獨立運作（monitor mode），也可作為 Dispatcher 的基礎，支援高可用、可擴展的分散式任務管理。

---

## 1. 架構定位與核心職責

Monitor 模組在 Skalds 架構中的定位如下：

- **即時監控**：持續監聽 Redis 中 Skalds 與 TaskWorker 的所有訊息（心跳、狀態、錯誤、異常）。
- **狀態同步**：將即時監控資訊同步至內部記憶體 Store，供 API、Dashboard、SSE 查詢。
- **指標收集**：統計 Skalds/TaskWorker 數量、狀態分布、任務分配、資源利用率等。
- **異常偵測**：自動判斷離線、失敗、異常任務，並觸發狀態更新。
- **Dashboard 與 SSE**：提供前端 Dashboard 及 SSE 事件流，支援即時監控與通知。

> Monitor 是 SystemController 的子模組，與 Dispatcher、API 服務協同運作，確保系統穩定與高可用。

---

## 2. 架構與資料流

Monitor 模組的架構設計如下：

- **資料來源**：
  - **Redis**：所有 Skalds/TaskWorker 的心跳、狀態、錯誤、異常訊息。
  - **MongoDB**：任務詳細資料（TaskMonitor 需用於任務狀態比對）。
- **核心組件**：
  - **SkaldMonitor**：定期（預設每 5 秒）從 Redis 取得所有 Skalds 狀態、心跳、任務分配資訊，判斷線上/離線、類型（node/edge）、支援任務等。
  - **TaskMonitor**：定期（預設每 3 秒）從 MongoDB 取得需監控任務，查詢 Redis 心跳、錯誤、異常，判斷任務狀態（Running/Failed/Cancelled/Finished）。
  - **Store（SkaldStore/TaskStore）**：記憶體快取所有監控資訊，供 API/Dashboard 查詢。
- **資料流**：
  1. SkaldMonitor 與 TaskMonitor 持續從 Redis/MongoDB 拉取狀態資訊。
  2. 監控結果同步至內部 Store，API 與 Dashboard 直接查詢 Store 取得即時資料。
  3. 異常/中斷任務自動更新狀態，必要時透過 Kafka 發送取消事件。

---

## 3. 監控內容與指標

### 3.1 Skalds 監控

- **線上/離線判斷**：根據心跳時間與 Redis 資料，超過閾值視為離線。
- **類型分辨**：node/edge 分類，僅 node 可被指派任務。
- **支援任務類型**：每個 Skalds 支援的任務類型列表。
- **當前任務**：每個 Skalds 正在執行的任務 ID 與類型。

![Skalds List](/img/skald_list.png)

### 3.2 TaskWorker 監控

- **心跳狀態**：0~199 為正常，-1 為異常，-2 為取消，200 為完成。
- **錯誤訊息**：運行時錯誤（不會中斷任務）。
- **異常訊息**：致命例外，會中斷任務並標記為 Failed。
- **自動狀態更新**：連續多次心跳不變自動判斷中斷，更新任務狀態。

![TaskWorker List](/img/taskworker_list.png)

### 3.3 任務詳細監控

- **任務基本資訊**：ID、類型、執行者、建立/更新時間、優先權等。
- **即時心跳與狀態**：歷史心跳、當前狀態、錯誤/異常訊息。
- **Attachments**：任務參數內容。
- **狀態控制**：可透過 API 取消/恢復任務，或更新參數。

![TaskWorker Detail](/img/taskwork_detail.png)

---

## 4. Dashboard 與 API 功能

### 4.1 Dashboard 特色

- **即時總覽**：顯示 Skalds/TaskWorker 數量、線上/離線分布、任務狀態統計。
- **Skalds 列表**：查詢所有 Skalds 節點、狀態、支援任務、當前任務。
- **TaskWorker 列表**：查詢所有任務、狀態、執行者、心跳、錯誤/異常。
- **任務詳細**：檢視單一任務詳細資訊、心跳歷史、Attachments、錯誤/異常。
- **即時刷新**：所有資料自動輪詢或透過 SSE 即時更新。

> 首頁畫面如下（Dashboard 主要入口）：

![Dashboard 首頁](/img/dashboard.png)

### 4.2 主要 API 端點

Monitor 模式下，API 服務會自動啟用，常用端點如下：

- `GET /api/system/health`：系統健康檢查
- `GET /api/system/status`：系統狀態
- `GET /api/system/dashboard/summary`：Dashboard 統計摘要
- `GET /api/system/metrics`：詳細系統指標
- `GET /api/skalds`：Skalds 節點列表
- `GET /api/skalds/{skald_id}`：單一 Skalds 詳細
- `GET /api/tasks`：任務列表
- `GET /api/tasks/{task_id}`：任務詳細
- `GET /api/tasks/{task_id}/heartbeat`：任務心跳資訊

### 4.3 SSE 事件流

Monitor 提供 Server-Sent Events（SSE）即時推播，支援前端即時監控：

- `GET /api/events/skalds`：Skalds 狀態/心跳事件
- `GET /api/events/tasks`：TaskWorker 心跳、錯誤、異常事件
- `GET /api/events/status`：SSE 連線狀態

**事件格式範例：**
```json
data: {"type":"skald_status","skaldId":"skalds-001","data":{"status":"online","taskCount":2},"timestamp":1640995260000}

data: {"type":"task_heartbeat","taskId":"task-001","data":{"heartbeat":151,"status":"Running"},"timestamp":1640995261000}
```

---

## 5. 配置與部署

### 5.1 啟動 Monitor 模式

Monitor 可獨立運作或作為 Dispatcher 的基礎，啟動方式如下：

#### 1. 設定環境變數

參考 `.env.example`，設定以下主要參數於 `.env`：

```bash
# System Controller 設定
SYSTEM_CONTROLLER_MODE=MONITOR

# 基本設定
LOG_LEVEL=DEBUG
LOG_RETENTION=3
LOG_ROTATION_MB=10

# Redis 設定
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_SYNC_PERIOD=3

# Kafka 設定
KAFKA_HOST=localhost
KAFKA_PORT=9092

# Mongo 設定
MONGO_HOST=mongodb://root:root@localhost:27017/
```

#### 2. 啟動服務

```bash
python -m skalds.system_controller.main
```

啟動後可於瀏覽器開啟 [http://127.0.0.1:8000/dashboard](http://127.0.0.1:8000/dashboard) 進行監控。

---

## 6. 進階特性與最佳實踐

- **高可用設計**：支援多副本部署，Redis/MongoDB 建議採用叢集或副本集。
- **監控間隔可調**：可透過 `MONITOR_SKALD_INTERVAL`、`MONITOR_TASK_INTERVAL` 調整監控頻率。（目前版本建議不更動）
- **自動異常處理**：心跳異常、任務中斷自動標記狀態，減少人工介入。
- **日誌與指標收集**：所有監控事件皆有詳細日誌，便於追蹤與除錯。
- **SSE 實時推播**：前端可直接監聽 SSE 端點，實現無縫即時監控。

---

## 7. 參考文件與延伸閱讀

- [SystemController 技術說明](./system_controller.md)
- [Skalds 架構與模組細節](../../intro.md)
- [Cache Memory 快取說明](../cache_memory.md)
- [EventQueue 事件佇列說明](../event_queue.md)
- [TaskWorker 詳細說明](../task_worker.md)

---

Monitor 模組是 Skalds 系統的可觀測性核心，正確配置與善用可大幅提升系統的穩定性、即時性與維運效率。