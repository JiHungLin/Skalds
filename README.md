# Skald

**An event-driven, modular distributed task scheduling and execution system.**

Inspired by the Skald of Norse mythology—storytellers and messengers—Skald is designed to efficiently manage complex AI and high-concurrency backend tasks through event-driven communication, flexible resource allocation, and robust task lifecycle management.

---

## Features

- **Modular architecture:** Clear separation of System Controller, Task Generator, Task Worker, Event Queue, Cache Memory, and Storage.
- **Event-driven communication:** Uses Pub/Sub style event queues to ensure loose coupling and high scalability.
- **Dynamic resource allocation:** Task Generator manages resources and task scheduling supporting auto-scaling in container orchestration platforms like Kubernetes.
- **Robust task lifecycle management:** Centralized monitoring, task state control, pause/resume/cancel functionalities.
- **High performance storage:** Separation of high-frequency cache with persistent disk storage for fault tolerance and efficiency.
- **Extensible and fault-tolerant:** Supports integration with Kafka, RabbitMQ or other message brokers. Designed for high availability and disaster recovery.
- **Security-focused:** Supports authentication and authorization between components ensuring secure task execution and data access.

---

## System Components Overview

| Module              | Description                                                                                     |
| ------------------- | ----------------------------------------------------------------------------------------------- |
| **System Controller** | Provides system access interface. Monitors task states and controls Task Generator.            |
| **Task Generator**    | Allocates resources for tasks. Receives task requests and dispatches to Task Workers.          |
| **Task Worker**       | Executes tasks independently. Handles media resources, caching, and storing results.           |
| **Event Queue**       | Facilitates communication between modules using pub/sub mechanisms.                            |
| **Cache Memory**      | Stores frequently accessed, high-speed read/write data.                                       |
| **Disk Storage**      | Stores statistics, recovery data, recording data for persistence and fault tolerance.          |

---

## Architecture Highlights

- **Loose coupling:** Components communicate through event queues making the system highly extensible and maintainable.
- **Resource-aware scheduling:** Task Generator assigns tasks based on real-time resource availability.
- **Status synchronization:** Bi-directional state updates ensure accurate task lifecycle tracking.
- **Dynamic updates:** Supports dynamic parameter updates and hot reloading capabilities.
- **High availability:** Replicated event queues and storage for fault tolerance.
- **Secure:** Configurable authentication and authorization between components.

---

## Getting Started

### Getting Started

#### 1. Install Python dependencies

```bash
pip install -e .
```

#### 2. Start Kafka, Redis, and MongoDB (using Docker)

You can quickly start all required services using Docker:

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
    image: redis
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

#### 3. Run tests

```bash
pytest
```

For more details, see the documentation for each service:
- [Redis Quick Start](https://hub.docker.com/_/redis)
- [MongoDB Quick Start](https://hub.docker.com/_/mongo)
- [Kafka Quick Start](https://hub.docker.com/r/bitnami/kafka)

---

## Use Cases

- AI image recognition and long-running compute tasks  
- Backend services requiring high concurrency and dynamic scaling  
- Systems needing real-time task management, including pausing, canceling or updating tasks dynamically  

---

## Contribution

Contributions, issues, and feature requests are welcome. Please feel free to check [issues page].

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

## About the Name

The project name **Skald** is inspired by Norse mythology, where Skalds are storytellers and messengers who preserve knowledge and convey information, reflecting the system’s core design philosophy of event-driven communication and task orchestration.
