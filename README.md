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

_(Pending implementation details — will be updated upon initial release)_

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
