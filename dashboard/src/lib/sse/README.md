# Server-Sent Events (SSE) Integration

This directory contains the SSE implementation for real-time updates in the Skalds Dashboard.

## Overview

The SSE system provides real-time updates for:
- **Skalds Status**: Connection status, heartbeat, current tasks
- **Task Status**: Heartbeat, errors, exceptions, lifecycle changes

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Components    │    │   SSE Context    │    │   SSE Manager   │
│                 │    │                  │    │                 │
│ SkaldsPage      │◄──►│ Global State     │◄──►│ EventSource     │
│ TasksPage       │    │ Event Handling   │    │ Subscriptions   │
│ Dashboard       │    │ Subscriptions    │    │ Reconnection    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   React State    │    │  Backend SSE    │
                       │   Maps/Updates   │    │   /api/events   │
                       └──────────────────┘    └─────────────────┘
```

## Files

### `manager.ts`
Core SSE manager that handles:
- EventSource connections to `/api/events/skalds` and `/api/events/tasks`
- Event subscription by ID
- Automatic reconnection with exponential backoff
- Mock events for development

### `../contexts/SSEContext.tsx`
React Context that provides:
- Global SSE state management
- Event-driven state updates
- Component subscription hooks
- Connection status monitoring

## Usage

### Basic Setup

1. **Wrap your app with SSEProvider**:
```tsx
import { SSEProvider } from './contexts/SSEContext'

function App() {
  return (
    <SSEProvider>
      {/* Your app components */}
    </SSEProvider>
  )
}
```

2. **Use SSE in components**:
```tsx
import { useSSE } from './contexts/SSEContext'

function MyComponent() {
  const { skalds, tasks, isConnected } = useSSE()
  
  // Access real-time data
  const skaldList = Array.from(skalds.values())
  const taskList = Array.from(tasks.values())
  
  return (
    <div>
      <p>Connection: {isConnected ? 'Connected' : 'Disconnected'}</p>
      {/* Render data */}
    </div>
  )
}
```

### Event Subscription

```tsx
import { useSkaldEvents, useTaskEvents } from './contexts/SSEContext'

function DetailComponent({ skaldId, taskId }) {
  // Subscribe to specific entity events
  const skaldEvents = useSkaldEvents(skaldId)
  const taskEvents = useTaskEvents(taskId)
  
  return (
    <div>
      <h3>Recent Skalds Events: {skaldEvents.length}</h3>
      <h3>Recent Task Events: {taskEvents.length}</h3>
    </div>
  )
}
```

## Event Types

### Skalds Events
```typescript
interface SkaldEvent {
  type: 'skald_status' | 'skald_heartbeat'
  skaldId: string
  data: {
    status?: 'online' | 'offline'
    heartbeat?: number
    tasks?: string[]
  }
}
```

### Task Events
```typescript
interface TaskEvent {
  type: 'task_heartbeat' | 'task_error' | 'task_exception'
  taskId: string
  data: {
    heartbeat?: number
    error?: string
    exception?: string
  }
}
```

## Configuration

### Environment Variables
```bash
# API base URL (default: current origin)
VITE_API_BASE_URL=http://localhost:8000

# Enable mock data in development
VITE_USE_MOCK_DATA=false
```

### SSE Manager Options
```typescript
// Custom base URL
const customManager = new SSEManager('/custom/events')

// Connection settings (in manager.ts)
private maxReconnectAttempts = 5
private reconnectDelay = 1000 // ms
```

## Development

### Mock Events
In development mode, the SSE manager automatically generates mock events:
- Skalds heartbeat events every 5 seconds
- Task heartbeat events every 3 seconds

### Debugging
Enable console logging to see SSE activity:
```typescript
// Events are logged automatically
console.log('Received Skalds event:', event)
console.log('Received Task event:', event)
```

## Error Handling

### Connection Errors
- Automatic reconnection with exponential backoff
- Maximum 5 retry attempts
- Connection state exposed via `isConnected` and `lastError`

### Event Parsing Errors
- Invalid JSON events are logged and ignored
- Component subscriptions are protected with try-catch

### UI Error States
```tsx
const { isConnected, lastError } = useSSE()

if (!isConnected) {
  return <div>Disconnected from live updates</div>
}

if (lastError) {
  return <div>Connection error: {lastError.message}</div>
}
```

## Performance Considerations

### Memory Management
- Event subscriptions are automatically cleaned up on component unmount
- Event history is limited to last 10 events per entity
- Maps are used for O(1) entity lookups

### Network Efficiency
- Single EventSource connection per endpoint
- Events are only processed for subscribed entities
- Reconnection uses exponential backoff to avoid spam

### State Updates
- React state updates are batched
- Only changed fields trigger re-renders
- Memoization prevents unnecessary computations

## Backend Integration

### Expected Endpoints
- `GET /api/events/skalds` - Skalds SSE stream
- `GET /api/events/tasks` - Task SSE stream

### Event Format
Events should be sent as JSON in SSE format:
```
data: {"type": "skald_heartbeat", "skaldId": "skalds-001", "data": {"heartbeat": 42}}

data: {"type": "task_error", "taskId": "task-123", "data": {"error": "Connection failed"}}
```

## Troubleshooting

### Common Issues

1. **SSE not connecting**
   - Check backend SSE endpoints are running
   - Verify CORS settings allow EventSource connections
   - Check browser network tab for connection errors

2. **Events not updating UI**
   - Ensure components are wrapped in SSEProvider
   - Check entity IDs match between API and SSE events
   - Verify event format matches expected interfaces

3. **Memory leaks**
   - Ensure useEffect cleanup functions are called
   - Check for unsubscribed event listeners
   - Monitor component unmount behavior

### Debug Commands
```javascript
// In browser console
window.sseManager = sseManager
sseManager.isConnected()
sseManager.getLastError()
```

## Testing

### Unit Tests
```typescript
// Mock SSE manager for testing
jest.mock('./lib/sse/manager', () => ({
  sseManager: {
    connect: jest.fn(),
    disconnect: jest.fn(),
    subscribeToSkald: jest.fn(() => jest.fn()),
    subscribeToTask: jest.fn(() => jest.fn()),
    isConnected: jest.fn(() => true)
  }
}))
```

### Integration Tests
- Test SSE connection establishment
- Verify event subscription/unsubscription
- Test reconnection behavior
- Validate state updates from events