# SystemController Deployment Guide

This guide covers how to deploy and run the Skald SystemController in different modes.

## Overview

The SystemController can run in three different modes:
- **controller**: Basic API server only
- **monitor**: API server + monitoring + dashboard
- **dispatcher**: Full system (API + monitoring + dispatching)

## Prerequisites

### Required Services

1. **Redis 7.4+** (required for monitoring and dispatching)
2. **MongoDB 7.0+** (required for task management)
3. **Kafka 3.9.0+** (required for dispatching mode)

### Python Dependencies

```bash
pip install fastapi uvicorn pydantic pymongo redis kafka-python
```

## Configuration

### Environment Variables

```bash
# SystemController Configuration
SYSTEM_CONTROLLER_MODE=dispatcher  # controller|monitor|dispatcher
SYSTEM_CONTROLLER_HOST=0.0.0.0
SYSTEM_CONTROLLER_PORT=8000

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# MongoDB Configuration
MONGO_HOST=mongodb://localhost:27017/
DB_NAME=skald

# Kafka Configuration (required for dispatcher mode)
KAFKA_HOST=localhost
KAFKA_PORT=9092
KAFKA_USERNAME=
KAFKA_PASSWORD=

# Monitor Settings
MONITOR_SKALD_INTERVAL=5           # seconds
MONITOR_TASK_INTERVAL=3            # seconds  
MONITOR_HEARTBEAT_TIMEOUT=5        # failed heartbeat threshold

# Dispatcher Settings
DISPATCHER_INTERVAL=5              # seconds
DISPATCHER_STRATEGY=least_tasks    # least_tasks|round_robin|random

# Dashboard
DASHBOARD_STATIC_PATH=skald/system_controller/static/dashboard

# Logging
LOG_LEVEL=INFO
LOG_PATH=logs
```

## Deployment Modes

### 1. Controller Mode (API Only)

Minimal deployment with just the REST API:

```bash
# Set environment
export SYSTEM_CONTROLLER_MODE=controller
export SYSTEM_CONTROLLER_HOST=0.0.0.0
export SYSTEM_CONTROLLER_PORT=8000

# Run SystemController
python -m skald.system_controller.main
```

**Features:**
- REST API endpoints
- Basic health checks
- No monitoring or dispatching

### 2. Monitor Mode (API + Monitoring + Dashboard)

Includes monitoring and dashboard:

```bash
# Set environment
export SYSTEM_CONTROLLER_MODE=monitor
export REDIS_HOST=localhost
export MONGO_HOST=mongodb://localhost:27017/

# Build dashboard (if not already built)
cd dashboard
npm install
npm run build
cd ..

# Run SystemController
python -m skald.system_controller.main
```

**Features:**
- All controller mode features
- Skald and Task monitoring
- Real-time dashboard
- SSE event streams

### 3. Dispatcher Mode (Full System)

Complete system with task dispatching:

```bash
# Set environment
export SYSTEM_CONTROLLER_MODE=dispatcher
export REDIS_HOST=localhost
export MONGO_HOST=mongodb://localhost:27017/
export KAFKA_HOST=localhost

# Run SystemController
python -m skald.system_controller.main
```

**Features:**
- All monitor mode features
- Automatic task assignment
- Load balancing strategies
- Kafka event publishing

## Docker Deployment

### Docker Compose Example

```yaml
version: '3.8'
services:
  system-controller:
    build: .
    ports:
      - "8000:8000"
    environment:
      - SYSTEM_CONTROLLER_MODE=dispatcher
      - REDIS_HOST=redis
      - MONGO_HOST=mongodb://mongo:27017/
      - KAFKA_HOST=kafka
    depends_on:
      - redis
      - mongo
      - kafka
    volumes:
      - ./logs:/app/logs

  redis:
    image: redis:8
    ports:
      - "6379:6379"

  mongo:
    image: mongo:7.0
    ports:
      - "27017:27017"
    environment:
      - MONGO_INITDB_ROOT_USERNAME=admin
      - MONGO_INITDB_ROOT_PASSWORD=password
    volumes:
      - mongo_data:/data/db

  kafka:
    image: bitnami/kafka:3.9.0
    ports:
      - "9092:9092"
    environment:
      - KAFKA_CFG_NODE_ID=0
      - KAFKA_CFG_PROCESS_ROLES=controller,broker
      - KAFKA_CFG_LISTENERS=PLAINTEXT://0.0.0.0:9092,CONTROLLER://:9093
      - KAFKA_CFG_ADVERTISED_LISTENERS=PLAINTEXT://127.0.0.1:9092
      - KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
      - KAFKA_CFG_CONTROLLER_QUORUM_VOTERS=0@kafka:9093
      - KAFKA_CFG_CONTROLLER_LISTENER_NAMES=CONTROLLER
      - KAFKA_CFG_INTER_BROKER_LISTENER_NAME=PLAINTEXT

volumes:
  mongo_data:
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Build dashboard
RUN cd dashboard && npm install && npm run build

# Expose port
EXPOSE 8000

# Run SystemController
CMD ["python", "-m", "skald.system_controller.main"]
```

## API Endpoints

### Core Endpoints

- `GET /` - System information
- `GET /api` - API information
- `GET /api/docs` - OpenAPI documentation
- `GET /api/system/health` - Health check
- `GET /api/system/status` - System status

### Task Management

- `GET /api/tasks` - List tasks (with pagination and filters)
- `GET /api/tasks/{id}` - Get specific task
- `PUT /api/tasks/{id}/status` - Update task status
- `PUT /api/tasks/{id}/attachments` - Update task attachments

### Skald Management

- `GET /api/skalds` - List Skalds
- `GET /api/skalds/{id}` - Get specific Skald
- `GET /api/skalds/{id}/tasks` - Get Skald's tasks
- `GET /api/skalds/summary/statistics` - Skald statistics

### Real-time Events (SSE)

- `GET /api/events/skalds` - Skald status events
- `GET /api/events/tasks` - Task status events

### Dashboard

- `GET /dashboard` - React dashboard (monitor/dispatcher modes)

## Monitoring and Observability

### Health Checks

```bash
# Basic health check
curl http://localhost:8000/api/system/health

# Detailed system status
curl http://localhost:8000/api/system/status

# System metrics
curl http://localhost:8000/api/system/metrics
```

### Logging

Logs are written to the configured `LOG_PATH` directory:

```
logs/
├── system_controller.log
├── skald_monitor.log
├── task_monitor.log
└── dispatcher.log
```

### Metrics

The system provides detailed metrics via `/api/system/metrics`:

- Skald counts and status
- Task distribution and status
- Performance metrics
- System utilization

## Troubleshooting

### Common Issues

1. **Dashboard not loading**
   ```bash
   # Build the dashboard
   cd dashboard
   npm install
   npm run build
   ```

2. **Redis connection failed**
   ```bash
   # Check Redis is running
   redis-cli ping
   
   # Check configuration
   echo $REDIS_HOST
   ```

3. **MongoDB connection failed**
   ```bash
   # Check MongoDB is running
   mongosh --eval "db.adminCommand('ping')"
   
   # Check configuration
   echo $MONGO_HOST
   ```

4. **Kafka connection failed**
   ```bash
   # Check Kafka is running
   kafka-topics.sh --bootstrap-server localhost:9092 --list
   
   # Check configuration
   echo $KAFKA_HOST
   ```

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python -m skald.system_controller.main
```

### Component Status

Check individual component status:

```bash
# System status
curl http://localhost:8000/api/system/status

# SSE connection status
curl http://localhost:8000/api/events/status
```

## Performance Tuning

### Monitor Intervals

Adjust monitoring intervals based on your needs:

```bash
# More frequent monitoring (higher CPU usage)
export MONITOR_SKALD_INTERVAL=2
export MONITOR_TASK_INTERVAL=1

# Less frequent monitoring (lower CPU usage)
export MONITOR_SKALD_INTERVAL=10
export MONITOR_TASK_INTERVAL=5
```

### Dispatcher Strategy

Choose the appropriate dispatching strategy:

- `least_tasks`: Assign to Skald with fewest tasks (default)
- `round_robin`: Rotate assignments evenly
- `random`: Random assignment

### Database Optimization

For MongoDB:
- Create indexes on frequently queried fields
- Use appropriate connection pool sizes
- Monitor query performance

For Redis:
- Configure appropriate memory limits
- Use Redis clustering for high availability
- Monitor memory usage

## Security Considerations

### Network Security

- Use firewalls to restrict access to service ports
- Enable TLS/SSL for production deployments
- Use VPNs or private networks for inter-service communication

### Authentication

The current implementation doesn't include authentication. For production:

- Add API key authentication
- Implement JWT tokens for dashboard access
- Use service-to-service authentication

### Data Protection

- Encrypt sensitive data in MongoDB
- Use Redis AUTH for Redis access
- Secure Kafka with SASL/SSL

## Scaling

### Horizontal Scaling

- Run multiple SystemController instances behind a load balancer
- Use Redis Cluster for high availability
- Use MongoDB replica sets
- Use Kafka partitioning for high throughput

### Vertical Scaling

- Increase memory for larger task/Skald stores
- Use faster storage for MongoDB
- Optimize Redis memory usage

## Backup and Recovery

### MongoDB Backup

```bash
# Create backup
mongodump --host localhost:27017 --db skald --out backup/

# Restore backup
mongorestore --host localhost:27017 --db skald backup/skald/
```

### Redis Backup

```bash
# Create backup
redis-cli BGSAVE

# Copy RDB file
cp /var/lib/redis/dump.rdb backup/
```

### Configuration Backup

- Store environment variables in version control
- Backup dashboard build artifacts
- Document deployment procedures