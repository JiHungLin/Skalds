import React, { useRef } from 'react';
import Layout from '@theme/Layout';
import { useState } from 'react';

const promptText = `
Skalds: Distributed Event-Driven Task Orchestration Framework — LLM Collaboration Prompt

[Project Positioning & Goals]
Skalds is an event-driven, modular, distributed task scheduling and execution system inspired by Norse skalds. It is designed for high-concurrency, scalable backend task management, suitable for AI computation, image analysis, real-time data processing, and more. Skalds emphasizes loose coupling, flexible resource scheduling, comprehensive monitoring, and type safety.

[Core Architecture & Modules]
- System Controller: Core for API, monitoring, scheduling, heartbeat, and state management
- Monitor: Performance monitoring, resource analysis, task tracking, alerting
- Dispatcher: Intelligent task assignment, dynamic load balancing
- Skald (Task Generator): Task creation and scheduling, supports Edge/Node modes
- Task Worker: Independent process for task execution, supports multi-stage, retry, and dynamic parameter hot update
- Event Queue: Kafka-based event queue for efficient Pub/Sub communication
- Cache Memory: Redis cache for high-frequency data and fine-grained TTL control
- Disk Storage: MongoDB for persistent storage, supports query, sharding, and fault tolerance

[Design Principles]
- High concurrency & performance: Supports massive parallel tasks and dynamic resource scheduling
- Modularity & extensibility: Each module is independent, pluggable, and easy to extend/maintain
- Event-driven & loose coupling: Uses Pub/Sub for flexible module interaction
- Type safety: All data structures use Pydantic BaseModel for strict typing

[Development Guidelines & Data Structures]
1. TaskWorker must inherit from BaseTaskWorker[T], where T is a Pydantic BaseModel. All attachments/event data must be type-safe.
2. Lifecycle hooks (Decorators):
   - @run_before_handler: Pre-execution hook
   - @run_main_handler: Main logic (must be implemented)
   - @run_after_handler: Post-execution hook
   - @release_handler: Resource release hook
   - @update_event_handler: Dynamic parameter hot update
3. Event flow & data sync:
   - Task creation, update, and cancellation are all event-driven (Kafka); state/heartbeat/errors are synced to Redis
   - All event data must conform to the corresponding Pydantic type
4. YAML configuration (Edge mode):
   - TaskWorkers:
       TaskWorker1:
         attachments:
           fixFrame: 30
           rtspUrl: rtsp://192.168.1.1/camera1
         className: MyWorker
   - attachments must match the Pydantic fields of the Python class (supports nested structures)
   - className must be a Python class registered in Skalds
5. Task data structure (Task):
   - id: str (unique identifier, matches YAML key)
   - class_name: str (TaskWorker class name)
   - attachments: Pydantic BaseModel (init/update parameters)
   - Other fields: name, description, dependencies, mode, lifecycle_status, priority, timestamps

[Error Handling & Monitoring]
- On task exception, _error_handler reports the error and pushes a failed heartbeat to Redis
- All state, heartbeat, and error messages can be queried and alerted by System Controller/Monitor
- Redis/Kafka connection failures, version mismatches, etc., are all logged in detail

[Example: Custom TaskWorker]
\`\`\`python
from skalds.worker.baseclass import BaseTaskWorker, run_before_handler, run_main_handler, update_event_handler
from pydantic import BaseModel, Field, ConfigDict

class MyDataModel(BaseModel):
    rtsp_url: str = Field(..., alias="rtspUrl")
    fix_frame: int = Field(..., alias="fixFrame")
    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

class MyWorker(BaseTaskWorker[MyDataModel]):
    def initialize(self, data: MyDataModel) -> None:
        self.rtsp_url = data.rtsp_url
        self.fix_frame = data.fix_frame

    @run_before_handler
    def before_run(self) -> None:
        print(f"Starting MyWorker with RTSP URL: {self.rtsp_url}")

    @run_main_handler
    def main_run(self) -> None:
        for _ in range(10):
            print(f"RTSP URL: {self.rtsp_url}, Fix Frame: {self.fix_frame}")

    @update_event_handler
    def update_event(self, event_data: MyDataModel) -> None:
        self.rtsp_url = event_data.rtsp_url
        self.fix_frame = event_data.fix_frame
\`\`\`

[Example: YAML Configuration]
\`\`\`yaml
TaskWorkers:
  TaskWorker1:
    attachments:
      fixFrame: 30
      rtspUrl: rtsp://192.168.1.1/camera1
    className: MyWorker
\`\`\`

[Example: Launching Skalds]
\`\`\`python
from skalds import Skalds
from skalds.config.skald_config import SkaldConfig
from my_worker import MyWorker

config = SkaldConfig(
    skald_mode="edge",  # or "node"
    yaml_file="all_workers.yml",
    redis_host="localhost",
    kafka_host="127.0.0.1",
    mongo_host="mongodb://root:root@localhost:27017/"
)

app = Skalds(config)
app.register_task_worker(MyWorker)
app.run()
\`\`\`

[Best Practices]
- Keys in attachments must match the Pydantic fields (or alias)
- className must be a Python class registered in Skalds
- All event data, task state, heartbeat, and errors must be type-safe and synced in real time
- Do NOT invent custom data structures; always follow official types and interfaces
- It is recommended to version-control YAML configs and code for traceability

`;

export default function PromptPage() {
  const preRef = useRef<HTMLPreElement>(null);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (preRef.current) {
      navigator.clipboard.writeText(promptText);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  };

  return (
    <Layout title="Skalds Prompt">
      <div style={{ maxWidth: 900, margin: '0 auto', padding: '2rem 1rem' }}>
        <h1>Skalds Prompt</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
          <button
            onClick={handleCopy}
            style={{
              padding: '0.5rem 1.2rem',
              fontSize: '1rem',
              cursor: 'pointer',
              background: '#3578e5',
              color: 'white',
              border: 'none',
              borderRadius: 4,
            }}
          >
            Copy All
          </button>
          {copied && (
            <span style={{ color: '#3578e5', fontWeight: 600, fontSize: '1rem' }}>
              Copied!
            </span>
          )}
        </div>
        <pre
          ref={preRef}
          style={{
            background: '#222',
            color: '#fff',
            padding: '1.5rem',
            borderRadius: 8,
            overflowX: 'auto',
            fontSize: '0.95rem',
            lineHeight: 1.5,
            maxHeight: 600,
          }}
        >
          {promptText}
        </pre>
      </div>
    </Layout>
  );
}