# Skalds 完整技術文件總覽

Skalds 是一套**事件驅動的模組化分散式任務調度與執行系統**，靈感來自北歐神話中的吟遊詩人（Skalds），專為高併發、可擴展的後端任務管理而設計。系統以鬆耦合架構、彈性資源調度與完整監控為核心，適用於 AI 運算、影像分析、即時資料處理等多種場景。

本文件為 Skalds 技術文件首頁，提供各核心模組、設計理念、生命週期、配置方式等主題的導覽與說明。建議先閱讀[框架介紹](../intro.md)以掌握整體架構，再依需求深入各章節。

---

## 目錄

- [快取資料（Cache Memory）](./documents/cache_memory.md)  
  介紹系統中快取引擎（Redis 8+）的設計與應用，包含高頻資料存取、TTL 控制等進階特性。

- [事件佇列（Event Queue）](./documents/event_queue.md)  
  說明基於 Kafka 3.9.0+ 的事件通訊機制，如何實現模組間的高效 Pub/Sub 訊息傳遞與鬆耦合互動。

- [任務生命週期（Task Lifecycle）](./documents/task_lifecycle.md)  
  詳細描述任務從生成、分配、執行到完成的全流程，以及狀態同步與錯誤處理機制。

- [任務工作者（Task Worker）](./documents/task_worker.md)  
  介紹工作者的設計、執行流程、多階段任務、重試與動態參數更新等功能。

- [YAML 配置說明（YAML Config）](./documents/yaml_config.md)  
  提供 YAML 格式的工作者與系統配置範例，說明各參數意義與最佳實踐。

- [系統控制器（System Controller）](./documents/system_controller/system_controller.md)  
  詳細說明系統核心控制器的架構、API、監控與調度子模組，並包含[Monitor](./documents/system_controller/monitor.md)、[Dispatcher](./documents/system_controller/dispatcher.md)等子章節。

---

## 進階閱讀建議

- [Skalds 框架介紹](../intro.md)：快速了解設計理念、架構與應用場景。
- [README.md](../../README.md)：專案總覽、安裝與啟動說明、使用範例。
- [更多範例](../examples/)：實際任務與工作者的程式碼範例。

---

Skalds 讓你輕鬆打造高效能、可擴展的分散式任務平台，無論是 AI 運算、資料處理還是即時控制，都能靈活應對。請依照目錄導覽深入各主題章節，獲取完整技術細節。
