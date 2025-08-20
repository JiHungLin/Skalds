---
sidebar_position: 2
sidebar_label: Dispatcher
---

# Dispatcher（任務調度模組）技術說明

Dispatcher 是 System Controller 的**智能任務分派核心模組**，負責根據即時資源狀態與策略，將待分派任務自動分配給最合適的 Skald 節點。其設計目標為動態負載平衡、資源最佳化與高可用性，確保分散式任務調度系統能高效運作。

---

## 1. 架構定位與角色

Dispatcher 隸屬於 System Controller，與 Monitor、API 服務等模組協同運作。其主要職責如下：

- **自動分派任務**：定期從資料庫（MongoDB）抓取待分派任務，根據策略選擇合適 Skald 節點。
- **動態負載平衡**：根據 Skald 當前負載（任務數量）與狀態，實現最少任務優先、輪詢、隨機等多種分派策略。
- **事件驅動**：分派後，透過 Kafka 發布任務分配事件，驅動 Skald 節點建立 Task Worker。
- **狀態同步**：即時更新任務執行者（executor）與狀態，確保系統狀態一致。

> 參考架構與模組說明：[System Controller 技術說明](./system_controller.md)、[Skalds 架構介紹](../../intro.md)

---

## 2. 運作流程

Dispatcher 的核心運作流程如下：

1. **定時輪詢**：每隔固定秒數（預設 5 秒），自動執行分派流程。
2. **篩選待分派任務**：從 MongoDB 取得所有狀態為「未分派」的任務（排除 Running、Assigning、Cancelled、Paused、Finished）。
3. **取得可用 Skald 節點**：僅選擇線上且類型為 node 的 Skald，並取得其當前任務數量。
4. **分派策略選擇**：根據設定的策略（如最少任務、輪詢、隨機）決定分派對象。
5. **更新任務狀態**：將任務的 executor 欄位設為選定 Skald ID，狀態改為 Assigning。
6. **發布分派事件**：透過 Kafka 發布 `task.assign` 事件，通知 Skald 節點建立 Task Worker。
7. **監控與重試**：若分派失敗或 Skald 不可用，會自動重試並記錄日誌。

> 詳細流程與狀態轉換請參考：[任務生命週期](../task_lifecycle.md)

---

## 3. 分派策略

Dispatcher 支援多種分派策略，可依據實際需求調整：

- **最少任務（LEAST_TASKS）**：優先分派給當前任務數最少的 Skald，實現負載均衡（預設）。
- **輪詢（ROUND_ROBIN）**：依序分派，確保任務平均分布。
- **隨機（RANDOM）**：隨機選擇可用 Skald，適合任務負載差異不大時。

可於環境變數或設定檔調整策略：

```bash
# .env 或部署環境變數
DISPATCHER_STRATEGY=LEAST_TASKS  # 可選 LEAST_TASKS|ROUND_ROBIN|RANDOM
```

> 策略列舉定義於 [skalds/config/_enum.py (GitHub)](https://github.com/JiHungLin/skalds/blob/main/skalds/config/_enum.py)

---

## 4. 主要程式碼結構

Dispatcher 主要實作於 [skalds/system_controller/monitor/dispatcher.py (GitHub)](https://github.com/JiHungLin/skalds/blob/main/skalds/system_controller/monitor/dispatcher.py)，其核心類別與方法如下：

- `Dispatcher`：單例類別，負責分派主流程與策略選擇。
  - `start()` / `stop()`：啟動與停止分派執行緒。
  - `_dispatch_tasks()`：分派主邏輯，包含任務篩選、Skald 選擇、狀態更新與事件發布。
  - `_calculate_assignments()`：根據策略計算任務分派對應表。
  - `_assign_task_to_skald()`：執行單一任務的分派與事件發布。
  - `set_strategy()`：動態切換分派策略。
  - `get_status()`：取得當前分派狀態與統計資訊。

> 詳細程式碼請參考 [dispatcher.py (GitHub)](https://github.com/JiHungLin/skalds/blob/main/skalds/system_controller/monitor/dispatcher.py)

---

## 5. 配置與啟動方式

### 5.1 啟動 Dispatcher 模式

System Controller 可透過環境變數 `SYSTEM_CONTROLLER_MODE=DISPATCHER` 啟動完整分派功能：

```bash
export SYSTEM_CONTROLLER_MODE=DISPATCHER
python -m skalds.system_controller.main
```

> 需同時啟動 Redis、MongoDB、Kafka 等服務，詳見[部署說明](../../../../skalds/system_controller/DEPLOYMENT.md)

### 5.2 主要環境變數

- `DISPATCHER_INTERVAL`：分派輪詢間隔（秒，預設 5）
- `DISPATCHER_STRATEGY`：分派策略（LEAST_TASKS、ROUND_ROBIN、RANDOM）
- 其他相關設定請參考 [skalds/config/system_controller_config.py (GitHub)](https://github.com/JiHungLin/skalds/blob/main/skalds/config/system_controller_config.py) 與 `.env.example`

---

## 6. API 與監控

Dispatcher 運作時，所有分派狀態與統計資訊可透過 System Controller API 查詢：

- **系統狀態查詢**  
  `GET /api/system/status`  
  回傳當前模式、各組件運作狀態、Dispatcher 詳細資訊。

- **分派狀態查詢**  
  `GET /api/system/metrics`  
  包含 Skalds 狀態、任務分布、分派策略與效能指標。

- **即時事件監控**  
  `GET /api/events/skalds`、`GET /api/events/tasks`  
  透過 SSE 監控 Skalds 與任務的即時狀態、心跳、錯誤等。

> API 詳細說明請參考 [`API.md`](../../../../skalds/system_controller/API.md)

---

## 7. 典型應用場景

- **高併發任務分派**：自動將大量任務分配給最合適的 Skald 節點，提升系統吞吐量。
- **動態負載平衡**：根據 Skald 負載即時調整分派，避免單點過載。
- **多租戶/多節點協同**：支援多 Skald 節點協同運作，適合大規模分散式場景。
- **緊急任務優先處理**：可根據任務優先權進行排序，確保高優先任務即時分派。

---

## 8. 效能優化與最佳實踐

- **合理設定分派間隔**：根據任務量與系統規模調整 `DISPATCHER_INTERVAL`，避免過度輪詢或延遲。
- **策略選擇**：根據實際負載選擇最適合的分派策略，動態切換可提升彈性。
- **監控與日誌**：結合 Monitor 與日誌系統，及時發現分派異常與資源瓶頸。
- **高可用部署**：建議搭配多副本、Redis Cluster、Kafka 分區等高可用架構。

---

## 9. 常見問題與除錯

- **無可用 Skald 節點**：請確認 Skald node 節點已註冊且線上，並檢查 Redis/MongoDB 連線狀態。
- **任務未分派**：檢查任務狀態是否正確（非 Running/Assigning/Cancelled），並確認分派策略與條件設定。
- **Kafka 發布失敗**：確認 Kafka 服務正常運作，並檢查 topic 設定。
- **分派策略異常**：可透過 API 動態查詢與切換策略，並檢查日誌獲取詳細錯誤資訊。

---

## 10. 參考文件與延伸閱讀

- [System Controller 技術說明](./system_controller.md)
- [Monitor 監控模組](./monitor.md)
- [任務生命週期與事件流](../task_lifecycle.md)
- [Skalds 架構與模組細節](../../intro.md)
- [Cache Memory 快取說明](../cache_memory.md)
- [EventQueue 事件佇列說明](../event_queue.md)

---

Dispatcher 是 Skalds 分散式任務調度系統的智能分派核心，正確配置與善用可大幅提升系統的彈性、效能與可維護性。