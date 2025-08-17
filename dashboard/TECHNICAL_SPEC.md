# Skald Dashboard Technical Specification

## Data Structures

### Core Types

```typescript
// Skald Types
interface Skald {
  id: string;
  type: 'node' | 'edge';
  status: 'online' | 'offline';
  lastHeartbeat: string;
  supportedTasks: string[];
  currentTasks: string[];
}

// Task Types
interface Task {
  id: string;
  type: string;
  status: TaskLifecycleStatus;
  executor?: string;
  createDateTime: string;
  updateDateTime: string;
  attachments: Record<string, any>;
  heartbeat: number;
  error?: string;
  exception?: string;
}

type TaskLifecycleStatus =
  | 'Created'
  | 'Assigning'
  | 'Running'
  | 'Paused'
  | 'Finished'
  | 'Failed'
  | 'Cancelled';

// SSE Event Types
interface SkaldEvent {
  type: 'skald_status' | 'skald_heartbeat';
  skaldId: string;
  data: {
    status?: string;
    heartbeat?: number;
    tasks?: string[];
  };
}

interface TaskEvent {
  type: 'task_heartbeat' | 'task_error' | 'task_exception';
  taskId: string;
  data: {
    heartbeat?: number;
    error?: string;
    exception?: string;
  };
}
```

## API Endpoints

### Skald Management

```typescript
// GET /api/skalds
interface GetSkaldsResponse {
  items: Skald[];
  total: number;
}

// GET /api/skalds/{id}
type GetSkaldResponse = Skald;
```

### Task Management

```typescript
// GET /api/tasks
interface GetTasksRequest {
  page: number;
  pageSize: number;
  lifecycleStatus?: TaskLifecycleStatus;
  className?: string;
  executor?: string;
}

interface GetTasksResponse {
  items: Task[];
  total: number;
  page: number;
  pageSize: number;
}

// GET /api/tasks/{id}
type GetTaskResponse = Task;

// PUT /api/tasks/{id}/status
interface UpdateTaskStatusRequest {
  status: 'Created' | 'Cancelled';
}

// PUT /api/tasks/{id}/attachments
interface UpdateTaskAttachmentsRequest {
  attachments: Record<string, any>;
}
```

## Real-time Events

### SSE Channels

1. Skald Events Channel
   ```typescript
   // GET /api/events/skalds
   // Events: SkaldEvent[]
   ```

2. Task Events Channel
   ```typescript
   // GET /api/events/tasks
   // Events: TaskEvent[]
   ```

### Event Handling

The frontend will implement an SSE manager class to handle event subscriptions:

```typescript
class SSEManager {
  // Connection management
  connect(): void;
  disconnect(): void;
  reconnect(): void;

  // Event subscriptions
  subscribeToSkald(skaldId: string, callback: (event: SkaldEvent) => void): void;
  subscribeToTask(taskId: string, callback: (event: TaskEvent) => void): void;
  
  // Event handling
  private handleSkaldEvent(event: SkaldEvent): void;
  private handleTaskEvent(event: TaskEvent): void;
  
  // Connection state
  isConnected(): boolean;
  getLastError(): Error | null;
}
```

## State Management

The application will use React Query for API data management and a custom state store for SSE events:

```typescript
// API Queries
const useSkalds = () => useQuery(['skalds'], fetchSkalds);
const useTask = (id: string) => useQuery(['task', id], () => fetchTask(id));

// SSE State Store
interface SSEState {
  skaldStatuses: Record<string, SkaldStatus>;
  taskStatuses: Record<string, TaskLifecycleStatus>;
  heartbeats: Record<string, number>;
  errors: Record<string, string>;
}
```

## Component Architecture

### Key Components

1. DataGrid
   - Reusable table component for both Skalds and Tasks
   - Built on TanStack Table
   - Supports sorting, filtering, and pagination

2. StatusIndicator
   - Visual indicator for Skald and Task status
   - Different colors for different states
   - Animated heartbeat indicator

3. TaskDetailModal
   - Full task information display
   - Attachment editor
   - Action buttons for task control

4. SkaldCard
   - Visual representation of Skald status
   - Shows current tasks and capabilities
   - Real-time status updates

### Layout Components

1. MainLayout
   - Header with system stats
   - Navigation sidebar
   - Main content area
   - Toast notifications

2. DashboardLayout
   - Summary cards
   - Quick action buttons
   - Recent activity feed

This technical specification serves as a foundation for implementing the Skald Dashboard frontend. It defines the core data structures, API interfaces, and component architecture needed to build a robust and maintainable application.