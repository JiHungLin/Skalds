# Skalds Dashboard

## Architecture Overview

The Skalds Dashboard is a modern web application built to monitor and manage Skalds tasks and workers. This frontend application integrates with the FastAPI backend system and provides real-time monitoring capabilities.

### Tech Stack

- **Framework**: React + TypeScript
  - Type safety and better developer experience
  - Strong ecosystem and community support
  - Excellent performance characteristics
  
- **Build Tool**: Vite
  - Fast development server
  - Optimized production builds
  - Built-in TypeScript support

- **Core Libraries**:
  - `@tanstack/react-query`: Data fetching and cache management
  - `@tanstack/react-table`: Task list management
  - `tailwindcss`: Utility-first CSS framework
  - `@heroicons/react`: UI icons
  - `zod`: Runtime type validation

### Application Structure

```
dashboard/
├── src/
│   ├── components/        # Reusable UI components
│   ├── features/         # Feature-specific components
│   │   ├── skalds/      # Skalds monitoring
│   │   └── tasks/       # Task management
│   ├── hooks/           # Custom React hooks
│   ├── lib/             # Utilities and helpers
│   │   ├── api/        # API client
│   │   └── sse/        # SSE manager
│   ├── store/           # Global state management
│   └── types/           # TypeScript definitions
├── public/              # Static assets
└── vite.config.ts       # Build configuration
```

### Real-time Updates (SSE)

The dashboard implements Server-Sent Events (SSE) for real-time monitoring:

1. **Skalds Status Updates**
   - Connection status (online/offline)
   - Heartbeat monitoring with visual indicators
   - Current task assignments
   - Real-time status changes

2. **Task Status Updates**
   - Task lifecycle status changes
   - Heartbeat monitoring with live counters
   - Error and exception reporting
   - Real-time progress updates

**SSE Integration Features:**
- ✅ Automatic connection management with reconnection
- ✅ Global state management via React Context
- ✅ Component-level event subscriptions
- ✅ Visual connection status indicators
- ✅ Mock events for development
- ✅ TypeScript support with full type safety
- ✅ Memory leak prevention with automatic cleanup

**Usage Example:**
```tsx
import { useSSE } from './contexts/SSEContext'

function MyComponent() {
  const { skalds, tasks, isConnected } = useSSE()
  
  return (
    <div>
      <p>Live Updates: {isConnected ? '🟢 Connected' : '🔴 Disconnected'}</p>
      <p>Skalds: {skalds.size}</p>
      <p>Tasks: {tasks.size}</p>
    </div>
  )
}
```

For detailed SSE documentation, see [`src/lib/sse/README.md`](src/lib/sse/README.md).

### Core Features

1. **Skalds Monitoring**
   - List of all Skalds with status indicators
   - Detailed view of Skalds capabilities
   - Real-time connection status
   - Current task assignments

2. **Task Management**
   - Task list with filtering and pagination
   - Task detail view
   - Task control actions (cancel/resume)
   - Attachment management
   - Real-time status updates

3. **System Overview**
   - Dashboard summary statistics
   - System health indicators
   - Active task count
   - Connected Skalds count

### Development Setup

1. Prerequisites:
   ```bash
   node >= 18.0.0
   npm >= 9.0.0
   ```

2. Installation:
   ```bash
   cd dashboard
   npm install
   ```

3. Development:
   ```bash
   npm run dev
   ```

4. Build:
   ```bash
   npm run build
   ```

### Integration with FastAPI

The built dashboard will be served as static files through the FastAPI server. The build output should be configured to the appropriate directory in the FastAPI project structure.

### API Integration

The dashboard will interact with the following API endpoints:

1. Skalds Management
   - GET `/api/skalds` - List all Skalds
   - GET `/api/skalds/{id}` - Get Skalds details

2. Task Management
   - GET `/api/tasks` - List tasks (with pagination)
   - GET `/api/tasks/{id}` - Get task details
   - PUT `/api/tasks/{id}/status` - Update task status
   - PUT `/api/tasks/{id}/attachments` - Update task attachments

3. SSE Endpoints
   - GET `/api/events/skalds` - Skalds status events
   - GET `/api/events/tasks` - Task status events