# SystemController API Documentation

This document provides detailed information about the SystemController REST API endpoints.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, the API does not require authentication. For production deployments, consider implementing API key or JWT-based authentication.

## Response Format

All API responses follow a consistent JSON format:

### Success Response
```json
{
  "data": {...},
  "message": "Success message",
  "timestamp": 1640995200000
}
```

### Error Response
```json
{
  "error": "Error message",
  "detail": "Detailed error information",
  "code": "ERROR_CODE",
  "timestamp": 1640995200000
}
```

## Endpoints

### System Endpoints

#### GET /
Get basic system information.

**Response:**
```json
{
  "name": "Skald SystemController",
  "version": "1.0.0",
  "mode": "dispatcher",
  "status": "running",
  "endpoints": {
    "api": "/api",
    "docs": "/api/docs",
    "dashboard": "/dashboard"
  }
}
```

#### GET /api/system/health
Health check endpoint for monitoring.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": 1640995200000,
  "services": {
    "skald_store": "healthy",
    "task_store": "healthy",
    "redis": "healthy",
    "mongodb": "healthy"
  }
}
```

#### GET /api/system/status
Get detailed system status.

**Response:**
```json
{
  "mode": "dispatcher",
  "components": [
    {
      "name": "SkaldMonitor",
      "running": true,
      "details": {
        "interval": 5,
        "monitored_skalds": 3
      }
    }
  ],
  "uptime": 3600,
  "version": "1.0.0"
}
```

#### GET /api/system/dashboard/summary
Get dashboard summary statistics.

**Response:**
```json
{
  "totalSkalds": 5,
  "onlineSkalds": 4,
  "totalTasks": 12,
  "runningTasks": 8,
  "completedTasks": 3,
  "failedTasks": 1,
  "assigningTasks": 0,
  "cancelledTasks": 0,
  "nodeSkalds": 3,
  "edgeSkalds": 2
}
```

#### GET /api/system/metrics
Get detailed system metrics.

**Response:**
```json
{
  "timestamp": 1640995200000,
  "skalds": {
    "total": 5,
    "online": 4,
    "offline": 1,
    "nodes": 3,
    "edges": 2,
    "availableNodes": 3,
    "busyNodes": 2,
    "idleNodes": 1
  },
  "tasks": {
    "monitored": 12,
    "running": 8,
    "failed": 1,
    "completed": 3,
    "cancelled": 0,
    "assigning": 0,
    "totalAssigned": 8
  },
  "performance": {
    "averageTasksPerSkald": 2.67,
    "taskDistribution": {
      "skald-001": 3,
      "skald-002": 2,
      "skald-003": 3
    },
    "systemLoad": {
      "skaldUtilization": 80.0,
      "nodeUtilization": 66.67
    }
  }
}
```

### Task Management

#### GET /api/tasks
Get paginated list of tasks with optional filters.

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `pageSize` (int): Items per page (default: 20, max: 100)
- `status` (string): Filter by task status
- `type` (string): Filter by task type/className
- `executor` (string): Filter by executor Skald ID

**Response:**
```json
{
  "items": [
    {
      "id": "task-001",
      "type": "DataProcessingTask",
      "status": "Running",
      "executor": "skald-001",
      "createDateTime": "1640995200000",
      "updateDateTime": "1640995260000",
      "attachments": {},
      "heartbeat": 150,
      "error": null,
      "exception": null,
      "priority": 5
    }
  ],
  "total": 50,
  "page": 1,
  "pageSize": 20
}
```

#### GET /api/tasks/{task_id}
Get specific task by ID.

**Response:**
```json
{
  "id": "task-001",
  "type": "DataProcessingTask",
  "status": "Running",
  "executor": "skald-001",
  "createDateTime": "1640995200000",
  "updateDateTime": "1640995260000",
  "attachments": {
    "inputFile": "data.csv",
    "outputPath": "/tmp/output"
  },
  "heartbeat": 150,
  "error": null,
  "exception": null,
  "priority": 5
}
```

#### PUT /api/tasks/{task_id}/status
Update task status (only Created or Cancelled allowed).

**Request Body:**
```json
{
  "status": "Cancelled"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Task status updated to Cancelled",
  "data": {
    "taskId": "task-001",
    "status": "Cancelled"
  }
}
```

#### PUT /api/tasks/{task_id}/attachments
Update task attachments.

**Request Body:**
```json
{
  "attachments": {
    "inputFile": "new_data.csv",
    "outputPath": "/tmp/new_output",
    "config": {
      "batchSize": 1000
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Task attachments updated successfully",
  "data": {
    "taskId": "task-001",
    "attachments": {...}
  }
}
```

#### GET /api/tasks/{task_id}/heartbeat
Get real-time heartbeat information for a task.

**Response:**
```json
{
  "taskId": "task-001",
  "heartbeat": 150,
  "status": "Running",
  "isAlive": true,
  "isAssigning": false,
  "error": null,
  "exception": null,
  "lastUpdate": 1640995260000,
  "heartbeatHistory": [145, 146, 148, 149, 150]
}
```

### Skald Management

#### GET /api/skalds
Get list of all Skalds with optional filters.

**Query Parameters:**
- `type` (string): Filter by Skald type (node/edge)
- `status` (string): Filter by status (online/offline)

**Response:**
```json
{
  "items": [
    {
      "id": "skald-001",
      "type": "node",
      "status": "online",
      "lastHeartbeat": "1640995260000",
      "supportedTasks": ["DataProcessingTask", "ImageTask"],
      "currentTasks": ["task-001", "task-002"],
      "heartbeat": 12345,
      "taskCount": 2
    }
  ],
  "total": 5
}
```

#### GET /api/skalds/{skald_id}
Get specific Skald by ID.

**Response:**
```json
{
  "id": "skald-001",
  "type": "node",
  "status": "online",
  "lastHeartbeat": "1640995260000",
  "supportedTasks": ["DataProcessingTask", "ImageTask"],
  "currentTasks": ["task-001", "task-002"],
  "heartbeat": 12345,
  "taskCount": 2
}
```

#### GET /api/skalds/{skald_id}/tasks
Get all tasks assigned to a specific Skald.

**Response:**
```json
{
  "skaldId": "skald-001",
  "tasks": [
    {
      "id": "task-001",
      "className": "DataProcessingTask",
      "assignedAt": 1640995200000
    },
    {
      "id": "task-002",
      "className": "ImageTask",
      "assignedAt": 1640995230000
    }
  ],
  "totalTasks": 2
}
```

#### GET /api/skalds/{skald_id}/status
Get detailed status information for a Skald.

**Response:**
```json
{
  "skaldId": "skald-001",
  "status": "online",
  "type": "node",
  "heartbeat": 12345,
  "lastUpdate": 1640995260000,
  "taskCount": 2,
  "isOnline": true,
  "uptime": null,
  "details": {
    "canAcceptTasks": true,
    "lastHeartbeatAge": 5000,
    "tasks": [
      {
        "id": "task-001",
        "className": "DataProcessingTask"
      }
    ]
  }
}
```

#### GET /api/skalds/summary/statistics
Get summary statistics for all Skalds.

**Response:**
```json
{
  "totalSkalds": 5,
  "onlineSkalds": 4,
  "offlineSkalds": 1,
  "nodeSkalds": 3,
  "edgeSkalds": 2,
  "availableNodes": 3,
  "totalRunningTasks": 8,
  "averageTasksPerSkald": 2.0,
  "details": {
    "onlineNodes": 3,
    "onlineEdges": 1,
    "busyNodes": 2,
    "idleNodes": 1
  }
}
```

### Real-time Events (Server-Sent Events)

#### GET /api/events/skalds
Stream Server-Sent Events for Skald status and heartbeat updates.

**Query Parameters:**
- `skald_id` (string): Filter events for specific Skald ID

**Event Format:**
```
data: {"type":"skald_status","skaldId":"skald-001","data":{"status":"online","taskCount":2},"timestamp":1640995260000}

data: {"type":"skald_heartbeat","skaldId":"skald-001","data":{"heartbeat":12346,"status":"online","tasks":["task-001","task-002"]},"timestamp":1640995261000}
```

#### GET /api/events/tasks
Stream Server-Sent Events for Task heartbeat, error, and exception updates.

**Query Parameters:**
- `task_id` (string): Filter events for specific Task ID

**Event Format:**
```
data: {"type":"task_heartbeat","taskId":"task-001","data":{"heartbeat":151,"status":"Running"},"timestamp":1640995261000}

data: {"type":"task_error","taskId":"task-001","data":{"error":"Connection timeout","status":"Running"},"timestamp":1640995262000}

data: {"type":"task_exception","taskId":"task-001","data":{"exception":"NetworkException: Connection lost","status":"Failed"},"timestamp":1640995263000}
```

#### GET /api/events/status
Get SSE connection status and statistics.

**Response:**
```json
{
  "connectedClients": 3,
  "timestamp": 1640995260000,
  "status": "active"
}
```

## Error Codes

### HTTP Status Codes

- `200` - Success
- `400` - Bad Request (validation error)
- `404` - Not Found
- `500` - Internal Server Error
- `503` - Service Unavailable

### Custom Error Codes

- `VALIDATION_ERROR` - Request validation failed
- `TASK_NOT_FOUND` - Task not found
- `SKALD_NOT_FOUND` - Skald not found
- `SERVICE_UNAVAILABLE` - Required service not available
- `INVALID_STATUS` - Invalid status transition

## Rate Limiting

Currently, no rate limiting is implemented. For production deployments, consider implementing rate limiting based on:

- IP address
- API key
- User authentication

## Pagination

List endpoints support pagination with the following parameters:

- `page`: Page number (1-based, default: 1)
- `pageSize`: Items per page (default: 20, max: 100)

Response includes pagination metadata:

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "pageSize": 20
}
```

## Filtering

Many endpoints support filtering via query parameters:

### Task Filters
- `status`: Task status (Created, Assigning, Running, etc.)
- `type`: Task type/className
- `executor`: Executor Skald ID

### Skald Filters
- `type`: Skald type (node, edge)
- `status`: Skald status (online, offline)

## WebSocket Alternative

For real-time updates, the API provides Server-Sent Events (SSE) instead of WebSockets. SSE is simpler to implement and debug, and works well for one-way communication from server to client.

To connect to SSE streams:

```javascript
// JavaScript example
const eventSource = new EventSource('/api/events/tasks');

eventSource.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Received event:', data);
};

eventSource.onerror = function(event) {
  console.error('SSE error:', event);
};
```

## API Versioning

The current API is version 1.0. Future versions will be accessible via:

- URL versioning: `/api/v2/tasks`
- Header versioning: `Accept: application/vnd.skald.v2+json`

## OpenAPI Documentation

Interactive API documentation is available at:

- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- OpenAPI JSON: `http://localhost:8000/api/openapi.json`

## SDK and Client Libraries

Currently, no official SDKs are provided. The API follows REST conventions and can be consumed by any HTTP client.

Example using Python requests:

```python
import requests

# Get tasks
response = requests.get('http://localhost:8000/api/tasks')
tasks = response.json()

# Update task status
response = requests.put(
    'http://localhost:8000/api/tasks/task-001/status',
    json={'status': 'Cancelled'}
)
```

Example using curl:

```bash
# Get system health
curl http://localhost:8000/api/system/health

# Get tasks with filters
curl "http://localhost:8000/api/tasks?status=Running&page=1&pageSize=10"

# Update task attachments
curl -X PUT http://localhost:8000/api/tasks/task-001/attachments \
  -H "Content-Type: application/json" \
  -d '{"attachments": {"key": "value"}}'