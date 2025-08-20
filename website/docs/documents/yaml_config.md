---
sidebar_position: 3
sidebar_label: YAML 配置
---

# YAML TaskWorker 配置檔說明
**YAML 配置檔主要用於 Skald Edge 節點（`skald_mode="edge"`）**，用來批次定義與註冊多個 TaskWorker。
Edge 節點啟動時會自動載入 YAML 檔案，根據配置內容建立對應的任務工作者，適合大規模、靜態或預先規劃的任務場景。

相較之下，**Skald Node 節點（`skald_mode="node"`）通常不需 YAML 配置**，提供動態產生的 TaskWorker，適合彈性擴展與動態任務分配。

YAML 配置檔是 Skalds 系統中用於批量定義與管理 TaskWorker 的主要方式。透過 YAML 檔案，使用者可靈活設定多個任務工作者的類型、參數、依賴關係與執行細節，實現高度自動化與可維護的任務調度。

---

## 結構與主要欄位

YAML 配置檔的頂層通常包含 `TaskWorkers` 區塊，每個工作者以唯一名稱為 key，對應其詳細設定。

| 欄位         | 型別           | 說明                                         | 範例                         |
|--------------|----------------|----------------------------------------------|------------------------------|
| TaskWorkers  | dict           | 所有工作者定義的集合，key 為工作者名稱        | TaskWorker1, TaskWorker2     |
| attachments  | dict           | 工作者初始化參數，對應 Pydantic 資料模型欄位  | fixFrame, rtspUrl, ...       |
| className    | str            | 對應 Python 中的 TaskWorker 類別名稱          | MyWorker, ComplexWorker      |

---

## 基本範例

> **注意：**  
> YAML 中每個工作者的唯一名稱（如 `TaskWorker1`）會直接對應到該任務的 `Task.id` 欄位。  
> 這使得任務在系統內部的追蹤、狀態查詢與事件分派都能以此名稱為依據，請確保每個名稱全域唯一且具備辨識性。

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

---

## 欄位詳細說明

| 欄位           | 說明                                                         |
|----------------|--------------------------------------------------------------|
| TaskWorker1, TaskWorker2 | 每個工作者的唯一名稱（即任務 ID，對應 Task.id）        |
| attachments    | 初始化參數，需對應該 TaskWorker 類別的 Pydantic 資料模型欄位   |
| className      | 指定 Python 中的 TaskWorker 類別名稱，需已註冊於 Skalds 系統   |
| sub_tasks      | 巢狀參數範例，支援 list/dict 結構，適用於複雜任務             |
| enable_feature_x, jobId, retries | 依 TaskWorker 類型自訂的參數                |

---

## 進階特性

- **巢狀結構支援**：attachments 可包含巢狀 list/dict，對應複雜資料模型。
- **型別對應**：所有參數需符合對應 TaskWorker 的 Pydantic 型別定義，否則初始化會失敗。
- **動態擴充**：可隨時新增/修改/刪除 TaskWorker 配置，系統支援熱重載。

---

## 最佳實踐與注意事項

- attachments 內的 key 必須與對應 TaskWorker 的 Pydantic 欄位名稱（或 alias）一致。
- className 必須為已註冊於 Skalds 的 Python 類別名稱。
- 建議將 YAML 配置檔與程式碼版本控管，確保任務定義可追溯。
- 若有複雜巢狀結構，建議先於 Python 端驗證資料模型正確性。

---

YAML 配置檔讓 Skalds 任務管理更彈性、可維護，適合大規模、動態調度的分散式任務場景。