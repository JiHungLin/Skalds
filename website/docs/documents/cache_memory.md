---
sidebar_position: 4
sidebar_label: CacheMemory
---

# 系統快取、暫存資料（Cache Memory）

Skalds 系統採用 **Redis 8+** 作為核心快取引擎，負責高頻率資料的暫存與同步，顯著提升分散式任務調度的效能與即時性。本文件將說明 Cache Memory 的設計理念、架構、API 介面、典型應用場景、與最佳實踐。

---

## 設計理念

- **高效能快取**：針對任務狀態、心跳、錯誤訊息等高頻存取資料，採用記憶體型快取，減少資料庫 I/O 負擔。
- **精細 TTL 控制**：支援每個雜湊欄位（hash field）獨立 TTL（Time-To-Live），可精確管理資料生命週期，避免過期或殘留。
- **即時同步**：所有任務狀態、心跳、錯誤訊息等皆同步至 Redis，System Controller 可即時監控與調度。
- **高可用性**：Redis 支援多副本、叢集部署，確保系統穩定運行。

---

## 架構與角色

Cache Memory 主要負責以下資料的快取與同步：

- **Skalds（Task Generator）**：註冊自身 ID、心跳、允許任務類型等資訊。
- **Task Worker**：註冊任務狀態、心跳、錯誤訊息，並支援動態參數熱更新。
- **System Controller**：即時查詢所有 Skalds 與 Task Worker 狀態，進行智能調度與監控。

資料流示意：

```
[Task Worker] <-> [Redis Cache] <-> [System Controller]
         ^                ^
         |                |
      任務狀態/心跳     Skalds 註冊/心跳
```

---

## Redis 版本需求

- **建議版本：Redis 8+**
- **最低需求：Redis 7.4+**（需支援 hash field TTL，否則部分功能將無法使用）

> 若遇到 `hexpire` 等指令錯誤，請確認 Redis 版本已升級至 7.4 以上。

---

## 主要資料結構與 Key 設計

參考 [`skalds/proxy/redis.py`](skalds/proxy/redis.py:1)：

### Skalds 相關

- `skalds:hash`：所有 Skalds 節點資訊（hash）
- `skalds:mode:hash`：各 Skalds 節點運行模式（hash）
- `skalds:{skald_id}:heartbeat`：單一 Skald 節點心跳（string）
- `skalds:{skald_id}:allow-task-class-name`：允許任務類型（list）
- `skalds:{skald_id}:all-task`：該 Skald 所有任務 ID（list）

### Task 相關

- `task:{task_id}:heartbeat`：任務心跳（string）
- `task:{task_id}:has-error`：任務錯誤狀態（string/bool）
- `task:{task_id}:exception`：任務例外訊息（string）

---

## RedisProxy 介面說明

[`skalds/proxy/redis.py`](skalds/proxy/redis.py:58) 提供高階 Redis 操作介面，常用方法如下：

- `set_hash(key, field, value, ttl=0)`：設定 hash 欄位，支援單欄位 TTL。
- `get_hash(key, field)`：取得 hash 欄位值。
- `push_list(key, value, insert_head=True, ttl=0)`：推入 list，支援 TTL。
- `get_list(key, start=0, end=-1)`：取得 list 範圍值。
- `set_message(key, message, expire=0, ttl=0)`：設定字串值，支援過期。
- `get_message(key)`：取得字串值。
- `get_all_hash(root_key)`：取得 hash 所有欄位。
- `delete_key(key)`：刪除 key。

> 連線失敗、版本不符等狀況皆有詳細 log 訊息，便於除錯。

---

## 典型應用場景

### 1. 任務狀態與心跳同步

Task Worker 啟動時，會定期將自身狀態、心跳、錯誤訊息等寫入 Redis，System Controller 可即時查詢所有任務狀態，進行調度與監控。

### 2. Skalds 節點註冊與監控

Skalds 啟動時，向 Redis 註冊自身 ID、運行模式與心跳，System Controller 依此分配任務與監控節點健康。

### 3. 動態參數熱更新

支援任務執行中，透過 Redis/Kafka 發送參數更新事件，Task Worker 監聽並即時調整運作參數。

---

## 實作範例

### 設定與使用 RedisProxy

```python
from skalds.proxy.redis import RedisProxy, RedisConfig

# 初始化 Redis 連線
redis_proxy = RedisProxy(RedisConfig(host="localhost", port=6379))

# 設定自訂 key
redis_proxy.set_message("my_custom_key", "custom_value", ttl=60)

# 設定 has_error 狀態（如任務執行失敗）
redis_proxy.set_message("task:task_123:has-error", "true", ttl=120)

# 設定 hash 欄位（如自訂任務屬性），欄位 TTL 180 秒
redis_proxy.set_hash("task_custom_hash", "task_123", "custom_data", ttl=180)

# 查詢所有自訂 hash 欄位
all_custom = redis_proxy.get_all_hash("task_custom_hash")

# 取得 has_error 狀態
has_error = redis_proxy.get_message("task:task_123:has-error")
```

---

## 效能優化與注意事項

- **TTL 機制**：建議所有心跳、狀態、暫存資料皆設定合理 TTL，避免資料殘留與記憶體浪費。
- **版本相容性**：hash 欄位 TTL 僅支援 Redis 7.4+，請確認部署環境。
- **高可用部署**：建議採用 Redis Cluster 或多副本架構，提升容錯與可用性。
- **監控與告警**：可結合 System Controller 監控 Redis 狀態，及時發現異常。

---

## 進階特性

- **每欄位 TTL 控制**：可針對 hash 欄位（如每個任務）單獨設定 TTL，精細管理任務生命週期。
- **即時事件推播**：結合 Redis Pub/Sub，支援任務狀態、參數、錯誤等即時通知。
- **自動清理**：過期資料自動清除，減少人工維護負擔。

---

## 參考文件與延伸閱讀

- [Redis 官方文件](https://redis.io/docs/)
- [Skalds 架構與模組細節](../intro.md)
- [任務生命週期與事件流](./task_lifecycle.md)
- [YAML 配置說明](./yaml_config.md)
- [Task Worker 詳細說明](./task_worker.md)

---

Cache Memory 是 Skalds 分散式任務調度系統的效能核心，正確配置與善用可大幅提升系統即時性、穩定性與可維護性。