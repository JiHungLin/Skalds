# Skald

**一個事件驅動的模組化分散式任務調度與執行系統。**

靈感來自北歐神話中的 Skald（吟遊詩人與使者），Skald 專為高併發後端任務管理而設計，透過事件驅動的通訊機制與靈活的資源配置，實現高效能、可擴展的任務調度與執行。

---

## 主要特色

- **模組化架構**  
  將系統劃分為明確職責的模組，包括 System Controller、Task Generator、Task Worker、Event Queue、Cache Memory 與 Storage，促進系統可維護性與擴展性。

- **事件驅動通訊**  
  採用發佈/訂閱（Pub/Sub）機制的事件佇列，實現模組間的鬆耦合互動，提高系統的彈性與可擴展能力。

- **動態資源調度**  
  Task Generator 根據即時的資源可用性進行任務分配，支援在容器化平台（如 Kubernetes）上的自動擴容與動態調整。

- **健全的任務生命週期管理**  
  中央化監控與控制任務狀態，提供暫停、恢復、取消等操作，確保任務執行的穩定與可靠。

---

## 系統模組總覽

| 模組               | 功能說明                                                                                            |
| ------------------ | ------------------------------------------------------------------------------------------------- |
| **System Controller** | 提供 RESTful 系統介面，負責任務建立與控制，監控 Task Generator 及 Task Worker 的心跳，依此更新任務狀態，並將任務指派給 Task Generator。 |
| **Task Generator(Skald)**    | 管理資源配置，從 System Controller 接收任務請求並負責任務生成與分配。                                                      |
| **Task Worker**       | 使用獨立資源（CPU、RAM）執行具體任務，擷取媒體資料來源含 RTSP、快取記憶體(Cache Memory)、磁碟(Storage)，並將結果存入快取或磁碟中。 |
| **Event Queue**       | 基於 Kafka 3.9.0+ 的事件通訊系統，運用 Pub/Sub 機制實現 System Controller、Task Generator 與 Task Worker 間的消息傳遞，具備高吞吐量和可靠性。無需 Zookeeper，簡化部署與維護。                      |
| **Cache Memory**      | 採用 Redis 8+ 作為快取引擎，儲存高頻率讀寫的數據以提升系統效能。支援進階特性如每個雜湊欄位的 TTL 控制，實現精細的數據生命週期管理。                                                             |
| **Disk Storage**      | 使用 MongoDB 7.0+ 進行持久化資料存儲，包括統計數據、復原資料及錄製資料。提供強大的查詢能力、自動分片，以及容錯與資料耐久性保障。                                          |

---

## 架構亮點

- **鬆耦合設計**  
  各模組透過事件佇列通訊，強化系統擴展性與維護性。

- **資源感知的排程**  
  Task Generator 依據實時資源狀態動態分配任務，提升使用效率。

- **狀態同步機制**  
  雙向的狀態更新確保任務生命週期的準確追蹤。

- **動態參數更新**  
  支援參數熱更新與熱重載，降低系統重啟時間。

- **高可用設計**  
  事件佇列及存儲採用多副本機制，保障系統在故障時仍保持穩定運行。


---

## Getting Started

#### 1. 安裝 Python dependencies

```bash
pip install -e .
```

#### 2. 啟動 Kafka, Redis, and MongoDB (使用 Docker)

You can quickly start all required services using Docker Compose:

```yaml
version: '3.8'
services:
  mongo:
    image: mongo
    restart: always
    ports:
      - "27027:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: {Username}
      MONGO_INITDB_ROOT_PASSWORD: {Password}
    volumes:
      - $HOME/mongodb:/data/db

  kafka-broker:
    image: 'bitnami/kafka:3.9.0'
    restart: always
    ports:
      - "9092:9092"
    environment:
      - KAFKA_CFG_NODE_ID=0
      - KAFKA_CFG_PROCESS_ROLES=controller,broker
      - KAFKA_CFG_LISTENERS=PLAINTEXT://0.0.0.0:9092,CONTROLLER://:9093
      - KAFKA_CFG_ADVERTISED_LISTENERS=PLAINTEXT://127.0.0.1:9092
      - KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
      - KAFKA_CFG_CONTROLLER_QUORUM_VOTERS=0@kafka-broker:9093
      - KAFKA_CFG_CONTROLLER_LISTENER_NAMES=CONTROLLER
      - KAFKA_CFG_INTER_BROKER_LISTENER_NAME=PLAINTEXT
      # Set retention time to 30 minutes
      - KAFKA_CFG_LOG_RETENTION_HOURS=0
      - KAFKA_CFG_LOG_RETENTION_MINUTES=30

  redis:
    image: redis:8
    restart: always
    ports:
      - "6379:6379"
```

> Save this as `docker-compose.yml` and start all services with:
>
> ```bash
> docker-compose up -d
> ```

> **Note:** If you already have Redis, MongoDB, or Kafka installed locally, you can use your existing services. Adjust connection settings as needed.
>
> **Recommended versions:**
> - Redis: 7.4+ (Requires 7.4 or above to support per-hash-field TTL)
> - MongoDB: 7.0
> - Kafka: 3.9.0 (no Zookeeper required)

---

## 適用場景（Use Cases）

- **AI 影像辨識與長時間運算任務**  
  適用於需要大量運算資源且任務執行時間較長的工作，比如影像分析、視訊流處理、深度學習推論等。

- **高併發後端服務**  
  支援動態擴展的後端服務架構，適合負載波動大且需快速調整資源的場景，如大型 Web 服務、數據處理流水線。

- **即時任務管理**  
  提供靈活的任務控制能力，支持任務的暫停、取消與動態更新，滿足需要即時調度與變更的業務需求。

---

## License

MIT License

Copyright (c) 2025 JiHungLin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## 關於名稱（About the Name）

本專案名稱 **Skald** 源自北歐神話中的「吟遊詩人」（Skald）。  
在古代北歐文化中，Skalds 扮演著故事傳述者與使者的角色，負責保存知識並傳達資訊。

這個命名正好呼應了系統核心的設計理念：  
透過**事件驅動的通訊機制**，在分散式架構中負責**任務調度與資訊流轉**，如同 Skald 一樣靈活且高效地承載並傳遞任務狀態與資料。

---

For more details, see the documentation for each service:
- [Redis Quick Start](https://hub.docker.com/_/redis)
- [MongoDB Quick Start](https://hub.docker.com/_/mongo)
- [Kafka Quick Start](https://hub.docker.com/r/bitnami/kafka)
