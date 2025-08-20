# 環境建置指南（Docker Compose）

本文件說明如何使用 Docker Compose 快速建置 Skalds 執行所需的基礎服務（MongoDB、Kafka、Redis），適用於本地開發與測試。

---

## 1. 服務組成

- **MongoDB**：任務與狀態的永久儲存。
- **Kafka**：事件佇列，實現模組間高效 Pub/Sub 通訊。
- **Redis**：快取記憶體，支援高頻資料存取與狀態同步。

---

## 2. docker-compose.yml 範例

將下列內容存為 `docker-compose.yml`，或直接參考 `examples/env_setup/docker-compose.yml`。
[在 GitHub 上檢視 docker-compose.yml](https://github.com/JiHungLin/skalds/blob/main/examples/env_setup/docker-compose.yml)

```yaml
version: '3.8'
services:
  mongo:
    image: mongo
    restart: always
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: root
      MONGO_INITDB_ROOT_PASSWORD: root
    volumes:
      - $PWD/mongodb:/data/db

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
      # 設定保留時間為 30 分鐘
      - KAFKA_CFG_LOG_RETENTION_HOURS=0
      - KAFKA_CFG_LOG_RETENTION_MINUTES=30

  redis:
    image: redis:8
    restart: always
    ports:
      - "6379:6379"
```

---

## 3. 啟動步驟

1. 安裝 [Docker](https://docs.docker.com/get-docker/) 與 [Docker Compose](https://docs.docker.com/compose/install/)。
2. 於專案根目錄執行：

   ```bash
   docker compose -f examples/env_setup/docker-compose.yml up -d
   ```

3. 啟動後，三個服務會分別監聽本機的 27017（MongoDB）、9092（Kafka）、6379（Redis）埠口。

---

## 4. 注意事項

- 預設帳號密碼（MongoDB）：`root` / `root`，可依需求調整。
- Kafka 採用單節點模式，適合開發測試，正式環境請依需求擴充。
- `$PWD/mongodb` 目錄會儲存 MongoDB 資料，請確保有寫入權限。
- 若需自訂網路、密碼或進階設定，請參考 [官方文件](https://hub.docker.com/_/mongo)、[Bitnami Kafka](https://hub.docker.com/r/bitnami/kafka)、[Redis](https://hub.docker.com/_/redis)。

---

## 5. 相關連結

- [快速入門](./quickstart.md)
- [YAML 配置說明](./documents/yaml_config.md)
- [技術文件首頁](./documents.md)
- [範例程式](./examples/)