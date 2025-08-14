# Skald Dashboard

## Architecture Overview

The Skald Dashboard is a modern web application built to monitor and manage Skald tasks and workers. This frontend application integrates with the FastAPI backend system and provides real-time monitoring capabilities.

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
│   │   ├── skalds/      # Skald monitoring
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

1. Skald Status Updates
   - Connection status
   - Heartbeat monitoring
   - Current task execution status

2. Task Status Updates
   - Task state changes
   - Heartbeat monitoring
   - Error/Exception reporting

### Core Features

1. **Skald Monitoring**
   - List of all Skalds with status indicators
   - Detailed view of Skald capabilities
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
   - Connected Skald count

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

1. Skald Management
   - GET `/api/skalds` - List all Skalds
   - GET `/api/skalds/{id}` - Get Skald details

2. Task Management
   - GET `/api/tasks` - List tasks (with pagination)
   - GET `/api/tasks/{id}` - Get task details
   - PUT `/api/tasks/{id}/status` - Update task status
   - PUT `/api/tasks/{id}/attachments` - Update task attachments

3. SSE Endpoints
   - GET `/api/events/skalds` - Skald status events
   - GET `/api/events/tasks` - Task status events