---
sidebar_position: 5
sidebar_label: EventQueue
---

# 事件佇列（EventQueue）

Skalds 系統中的 **EventQueue** 是實現模組間鬆耦合、高效能通訊的關鍵元件。它基於 **Kafka 3.9.0+**，採用發佈/訂閱（Pub/Sub）機制，負責 System Controller、Task Generator（Skald）、Task Worker 之間的事件傳遞與狀態同步。EventQueue 具備高吞吐量、可靠性與彈性擴展能力，是分散式任務調度的核心通訊樞紐。

---

## 設計理念

- **事件驅動**：所有任務建立、更新、取消等操作皆以事件形式流轉，確保狀態即時同步。
- **鬆耦合架構**：模組間僅透過事件佇列互動，降低耦合度，提升系統可維護性與擴展性。
- **高可用與高效能**：Kafka 支援多副本、分區與自動容錯，適合大規模分散式場景。
- **無需 Zookeeper**：採用 Kafka 3.9.0+，簡化部署與維護。

---

## 架構與角色

EventQueue 主要負責以下模組間的事件通訊：

- **System Controller**：發佈任務建立、更新、取消等事件，監控任務狀態。
- **Task Generator（Skald）**：接收並處理與自身 ID 相關的事件，分配任務給 Task Worker。
- **Task Worker**：監聽自身任務 ID 的事件，動態調整運作參數或終止任務。

事件流示意：

```
[System Controller] <-> [EventQueue (Kafka)] <-> [Skald] <-> [Task Worker]
```

---

## 事件格式與資料結構

EventQueue 所有事件皆以結構化 JSON 格式傳遞，並以 Pydantic 資料模型進行驗證。主要事件格式定義於 [skalds/model/event.py (GitHub)](https://github.com/JiHungLin/skalds/blob/main/skalds/model/event.py)：

### 1. TaskEvent

用於任務分配、更新、取消等事件。

```python
class TaskEvent(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    initiator: Optional[str] = None
    recipient: Optional[str] = None
    create_date_time: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000), alias="createDateTime")
    update_date_time: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000), alias="updateDateTime")
    task_ids: list = Field(..., alias="taskIds")
```

- **id**：事件唯一識別碼（可選）
- **title**：事件標題（可選）
- **initiator**：事件發起者（可選）
- **recipient**：事件接收者（可選）
- **createDateTime**：建立時間（毫秒）
- **updateDateTime**：更新時間（毫秒）
- **taskIds**：受影響的任務 ID 列表（必填）

#### 範例 payload

```json
{
  "id": "evt_001",
  "title": "Assign Task",
  "initiator": "system_controller",
  "recipient": "skalds-1",
  "createDateTime": 1724131200000,
  "updateDateTime": 1724131200000,
  "taskIds": ["task_123"]
}
```

---

### 2. UpdateTaskWorkerEvent

用於 Task Worker 參數熱更新事件。

```python
class UpdateTaskWorkerEvent(BaseModel):
    attachments: Optional[Any] = None  # 必須為 Pydantic BaseModel 實例

    @field_validator("attachments", mode="before")
    def validate_attachments(cls, v):
        if v is None:
            return v
        if not isinstance(v, BaseModel):
            raise ValueError("attachments must be a Pydantic BaseModel instance")
        return v
```

- **attachments**：任務參數（必須為 Pydantic BaseModel 實例，型別安全）

#### 範例 payload

```json
{
  "attachments": {
    "rtspUrl": "rtsp://192.168.1.1/camera1",
    "fixFrame": 30
  }
}
```

> **注意：**  
> attachments 欄位必須符合對應 TaskWorker 的 Pydantic 資料模型，否則初始化或更新會失敗。

---

## 事件生命週期中的角色

EventQueue 在任務生命週期的三大流程中扮演關鍵角色：

### 1. 任務建立

1. System Controller 產生任務後，發佈「新增任務事件」至 EventQueue。
2. Skald 監聽並接收與自身 ID 相符的事件，建立 Task Worker。
3. Task Worker 啟動後，向 Redis 註冊狀態與心跳。

### 2. 任務更新

1. System Controller 發佈「更新任務事件」至 EventQueue。
2. Skald 接收事件，查詢任務細節，並將更新事件轉發給對應 Task Worker。
3. Task Worker 監聽自身任務 ID 的事件，動態調整參數。

> 詳細流程請參考：[任務生命週期](./task_lifecycle.md)

### 3. 任務取消

1. System Controller 發佈「取消任務事件」至 EventQueue，廣播給所有 Skald。
2. Skald 查詢是否有對應 Task Worker，若有則關閉並釋放資源。

---

## 技術選型與 Kafka 架構

- **Kafka 版本需求**：建議 3.9.0+，支援無 Zookeeper 部署。
- **高吞吐量**：適合大量事件流與高併發場景。
- **多副本與分區**：提升容錯與擴展性。
- **Pub/Sub 機制**：支援多消費者群組，靈活分發事件。

---

## 事件主題（Topic）設計

參考 [skalds/proxy/kafka.py (GitHub)](https://github.com/JiHungLin/skalds/blob/main/skalds/proxy/kafka.py)：

- `task.assign`：任務分配事件
- `task.cancel`：任務取消事件
- `task.update.attachment`：任務參數更新事件
- `taskworker.update`：Task Worker 狀態更新事件

> **注意：**  
> 不建議為每個任務動態產生 `task.{task_id}.update` 這類 per-task topic，因為會導致 topic 數量爆炸，嚴重影響 Kafka 效能與管理。  
> 請統一使用共用 topic（如 `task.update.attachment`），並以 message key 或 payload 內的 task_id 做過濾與分流。

---

## Kafka Proxy 介面說明

[skalds/proxy/kafka.py (GitHub)](https://github.com/JiHungLin/skalds/blob/main/skalds/proxy/kafka.py) 提供高階 Kafka 操作介面，常用方法如下：

- `produce(topic_name, key, value)`：發佈事件至指定主題
- `KafkaConfig`：配置 Kafka 連線參數（host、port、topic、群組 ID、認證等）
- `KafkaAdmin`：主題管理（建立、刪除、查詢）

### 典型用法

```python
from skalds.proxy.kafka import KafkaProxy, KafkaConfig, KafkaTopic

# 初始化 Kafka 連線
kafka_proxy = KafkaProxy(KafkaConfig(host="localhost", port=9092))

# 發佈任務分配事件
from skalds.model.event import TaskEvent
event = TaskEvent(taskIds=["task_123"], initiator="system_controller", recipient="skalds-1")
kafka_proxy.produce(KafkaTopic.TASK_ASSIGN, key="task_123", value=event.model_dump_json())

# 發佈任務參數更新事件（共用 topic，key 為 task_id）
from skalds.model.event import UpdateTaskWorkerEvent
update_event = UpdateTaskWorkerEvent(attachments=...)
kafka_proxy.produce(KafkaTopic.TASK_UPDATE_ATTACHMENT, key="task_123", value=update_event.model_dump_json())
```

---

## 典型應用場景

- **任務分配與調度**：System Controller 透過 EventQueue 將任務分配給指定 Skald。
- **動態參數熱更新**：任務執行中，透過 EventQueue 發送參數更新事件，Task Worker 即時調整。
- **任務取消與終止**：廣播取消事件，確保所有相關節點同步終止任務。
- **狀態監控與回報**：Task Worker 可回報狀態至 EventQueue，供 System Controller 監控。

---

## 效能優化與注意事項

- **分區設計**：根據任務量與消費者數量合理設計分區數，提升併發處理能力。
- **主題命名規範**：建議以功能/任務類型區分主題，便於維護與監控。
- **避免 per-task topic**：所有事件請統一發佈至共用主題，避免動態產生大量 topic。
- **連線重試與容錯**：KafkaProxy 內建自動重連與錯誤處理機制，提升穩定性。
- **安全性**：如需雲端部署，建議啟用 SASL/SSL 認證。

---

## 部署建議

- **建議版本**：Kafka 3.9.0+（無需 Zookeeper）
- **多副本部署**：提升高可用性與容錯能力
- **監控工具**：可結合 Kafka Manager、Prometheus 等工具監控主題流量與延遲
- **與 Redis/MongoDB 整合**：事件流僅負責通訊，狀態資料仍建議同步至 Redis/MongoDB

---

## 參考文件與延伸閱讀

- [Kafka 官方文件](https://kafka.apache.org/documentation/)
- [Skalds 架構與模組細節](../intro.md)
- [任務生命週期與事件流](./task_lifecycle.md)
- [Task Worker 詳細說明](./task_worker.md)
- [Cache Memory 快取說明](./cache_memory.md)
- [YAML 配置說明](./yaml_config.md)

---

EventQueue 是 Skalds 分散式任務調度系統的通訊核心，正確設計與善用可大幅提升系統的即時性、彈性與可維護性。