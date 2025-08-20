# System Controller（系統核心控制器）技術說明

---

## 1. 模組定位與架構角色

System Controller 是 Skalds 分散式任務調度系統的**核心控制模組**，負責整合 API 服務、系統監控（Monitor）、任務調度（Dispatcher）、心跳監控與狀態管理。它作為系統的中樞，協調 Skald（Task Generator）、Task Worker、Event Queue、Cache Memory 等模組，確保任務生命週期的完整流轉與系統資源的最佳化利用。

**主要職責：**
- 提供 RESTful API 介面，支援任務建立、查詢、控制等操作
- 整合系統監控（Monitor）與任務調度（Dispatcher）功能
- 追蹤 Skald 與 Task Worker 的心跳與狀態
- 統一管理任務狀態、系統配置與資源分配

---

## 2. 設計理念

- **模組化與鬆耦合**：System Controller 與其他模組（Skald、Task Worker、Event Queue、Cache Memory）透過事件佇列與快取進行通訊，降低耦合度，提升維護性與擴展性。
- **事件驅動**：所有任務操作（建立、更新、取消）皆以事件流方式驅動，確保狀態同步與高效調度。
- **智能調度與監控**：結合 Monitor 與 Dispatcher，根據即時資源狀態進行任務分配與負載平衡。
- **高可用與可觀測性**：支援多副本部署、日誌分割、指標收集與異常告警。

---

## 3. 架構與核心組件

System Controller 主要包含以下子模組：

- **API 服務**：提供 RESTful API，支援任務管理、系統查詢、狀態控制等功能。參見 [skalds/system_controller/api/server.py (GitHub)](https://github.com/JiHungLin/skalds/blob/main/skalds/system_controller/api/server.py)。
- **Monitor（監控模組）**：負責系統效能監控、資源指標收集、任務狀態追蹤與警報通知。詳見 [`monitor.md`](./monitor.md)。
- **Dispatcher（調度模組）**：根據 Monitor 提供的資訊進行智能任務分配與動態負載平衡。詳見 [`dispatcher.md`](./dispatcher.md)。
- **狀態管理**：統一管理 Skald、Task Worker、任務等狀態，並與 Redis（Cache Memory）同步。
- **事件處理**：與 Event Queue（Kafka）整合，發佈/訂閱任務相關事件，驅動任務生命週期。

---

## 4. 啟動與配置

### 4.0 安裝方式

System Controller 需透過下列指令安裝，請務必使用 **pip install skalds[backend]**，這是獨立分割出來的套件，確保所有後端相依元件皆正確安裝：

```bash
pip install "skalds[backend]"
```

### 4.1 環境變數設定

請參考專案根目錄的 [`.env.example (GitHub)`](https://github.com/JiHungLin/skalds/blob/main/.env.example)，複製為 `.env` 並根據需求調整：

```bash
cp .env.example .env
```

**主要環境變數：**
- `SYSTEM_CONTROLLER_MODE`：運行模式（如 MONITOR）
- `LOG_LEVEL`、`LOG_RETENTION`、`LOG_ROTATION_MB`
- `REDIS_HOST`、`REDIS_PORT`、`REDIS_PASSWORD`、`REDIS_SYNC_PERIOD`
- `KAFKA_HOST`、`KAFKA_PORT`、`KAFKA_USERNAME`、`KAFKA_PASSWORD`
- `MONGO_HOST`、`DB_NAME`

> 詳細參數請參閱 [`.env.example (GitHub)`](https://github.com/JiHungLin/skalds/blob/main/.env.example)。

### 4.2 啟動服務

安裝好相依套件與設定好 `.env` 後，於專案根目錄執行：

```bash
python -m skalds.system_controller.main
```

啟動後將自動載入設定，啟動 API、監控與調度功能。可於瀏覽器開啟 [http://127.0.0.1:8000/](http://127.0.0.1:8000/) 進行操作與管理。

---

## 5. 主要功能與流程

### 5.1 任務生命週期管理

System Controller 負責任務的**建立、更新、取消**三大核心流程，並確保狀態於各模組間即時同步。詳細流程請參考 [`task_lifecycle.md`](../task_lifecycle.md)。

- **建立任務**：接收外部請求，產生任務 ID，存入資料庫，發佈事件至 Event Queue，Skald 監聽並建立 Task Worker。
- **更新任務**：接收更新請求，更新資料庫，發佈事件，Skald 轉發至對應 Task Worker，支援動態參數熱更新。
- **取消任務**：接收取消請求，標記任務狀態，廣播事件，Skald 關閉對應 Task Worker。

### 5.2 系統監控（Monitor）

- 持續監控 Skald、Task Worker、系統資源狀態
- 收集效能指標、資源使用率
- 觸發警報與通知
- 詳細說明請參見 [`monitor.md`](./monitor.md)

### 5.3 任務調度（Dispatcher）

- 根據 Monitor 提供的即時資訊進行智能任務分配
- 動態負載平衡、資源優化、緊急任務優先處理
- 詳細說明請參見 [`dispatcher.md`](./dispatcher.md)

### 5.4 狀態同步與心跳監控

- 與 Redis（Cache Memory）整合，追蹤 Skald、Task Worker 的心跳與狀態
- 支援每個節點/任務的即時狀態查詢與異常偵測
- 參考 [`cache_memory.md`](../cache_memory.md)

### 5.5 事件流與模組互動

- 與 Event Queue（Kafka）整合，發佈/訂閱任務事件
- 保證任務狀態、參數、錯誤等資訊的即時流轉
- 參考 [`event_queue.md`](../event_queue.md)

---

## 6. 典型應用場景

- **高併發任務管理**：支援大量任務的即時建立、分配、監控與終止
- **AI/影像分析等長時間運算**：確保任務狀態與資源使用的即時同步
- **動態資源調度**：根據系統負載自動調整任務分配
- **多租戶/多節點協同**：支援多 Skald 節點與 Task Worker 的協同運作

---

## 7. 效能優化與最佳實踐

- **合理設定心跳與狀態 TTL**，避免資料殘留與資源浪費
- **多副本部署**，提升高可用性與容錯能力
- **日誌分割與保留策略**，便於追蹤與除錯
- **結合監控工具**（如 Prometheus、Grafana）進行指標收集與告警
- **與 Redis/Kafka/MongoDB 整合**，確保資料一致性與高效通訊

---

## 8. 進階特性

- **參數熱更新與熱重載**：支援任務執行中即時調整參數，降低系統重啟成本
- **型別安全**：所有任務資料與事件皆採用 Pydantic BaseModel，確保資料結構嚴謹
- **高可用設計**：支援多副本、分片、故障自動恢復
- **自動化 API 文件**：API 介面自動生成說明，便於整合與擴展

---

## 9. 參考文件與延伸閱讀

- [Skalds 架構與模組細節](../intro.md)
- [任務生命週期與事件流](../task_lifecycle.md)
- [Monitor 監控模組](./monitor.md)
- [Dispatcher 調度模組](./dispatcher.md)
- [Cache Memory 快取說明](../cache_memory.md)
- [EventQueue 事件佇列說明](../event_queue.md)
- [TaskWorker 詳細說明](../task_worker.md)
- [YAML 配置說明](../yaml_config.md)

---

System Controller 是 Skalds 分散式任務調度系統的中樞，正確配置與善用可大幅提升系統的穩定性、彈性與可維護性。