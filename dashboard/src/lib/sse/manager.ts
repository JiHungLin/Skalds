import { SkaldEvent, TaskEvent } from '../../types'

type EventCallback<T> = (event: T) => void
type ConnectionStateCallback = (connected: boolean) => void

class SSEManager {
  private skaldEventSource: EventSource | null = null
  private taskEventSource: EventSource | null = null
  private skaldCallbacks = new Map<string, EventCallback<SkaldEvent>[]>()
  private taskCallbacks = new Map<string, EventCallback<TaskEvent>[]>()
  private connectionCallbacks: ConnectionStateCallback[] = []
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private connected = false
  private lastError: Error | null = null

  constructor(private baseUrl: string = '/api/events') {}

  // Connection management
  connect(): void {
    this.connectSkaldEvents()
    this.connectTaskEvents()
  }

  disconnect(): void {
    this.disconnectSkaldEvents()
    this.disconnectTaskEvents()
    this.connected = false
    this.notifyConnectionState(false)
  }

  reconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
    
    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`)
    
    setTimeout(() => {
      this.disconnect()
      this.connect()
    }, delay)
  }

  // Skald events
  private connectSkaldEvents(): void {
    try {
      this.skaldEventSource = new EventSource(`${this.baseUrl}/skalds`)
      
      this.skaldEventSource.onopen = () => {
        console.log('Skald SSE connection opened')
        this.reconnectAttempts = 0
        this.connected = true
        this.lastError = null
        this.notifyConnectionState(true)
      }

      this.skaldEventSource.onmessage = (event) => {
        try {
          const skaldEvent: SkaldEvent = JSON.parse(event.data)
          this.handleSkaldEvent(skaldEvent)
        } catch (error) {
          console.error('Error parsing Skald event:', error)
        }
      }

      this.skaldEventSource.onerror = (error) => {
        console.error('Skald SSE error:', error)
        this.lastError = new Error('Skald SSE connection error')
        this.connected = false
        this.notifyConnectionState(false)
        
        if (this.skaldEventSource?.readyState === EventSource.CLOSED) {
          this.reconnect()
        }
      }
    } catch (error) {
      console.error('Failed to connect to Skald events:', error)
      this.lastError = error as Error
    }
  }

  private disconnectSkaldEvents(): void {
    if (this.skaldEventSource) {
      this.skaldEventSource.close()
      this.skaldEventSource = null
    }
  }

  // Task events
  private connectTaskEvents(): void {
    try {
      this.taskEventSource = new EventSource(`${this.baseUrl}/tasks`)
      
      this.taskEventSource.onopen = () => {
        console.log('Task SSE connection opened')
      }

      this.taskEventSource.onmessage = (event) => {
        try {
          const taskEvent: TaskEvent = JSON.parse(event.data)
          this.handleTaskEvent(taskEvent)
        } catch (error) {
          console.error('Error parsing Task event:', error)
        }
      }

      this.taskEventSource.onerror = (error) => {
        console.error('Task SSE error:', error)
        this.lastError = new Error('Task SSE connection error')
        
        if (this.taskEventSource?.readyState === EventSource.CLOSED) {
          this.reconnect()
        }
      }
    } catch (error) {
      console.error('Failed to connect to Task events:', error)
      this.lastError = error as Error
    }
  }

  private disconnectTaskEvents(): void {
    if (this.taskEventSource) {
      this.taskEventSource.close()
      this.taskEventSource = null
    }
  }

  // Event subscriptions
  subscribeToSkald(skaldId: string, callback: EventCallback<SkaldEvent>): () => void {
    if (!this.skaldCallbacks.has(skaldId)) {
      this.skaldCallbacks.set(skaldId, [])
    }
    this.skaldCallbacks.get(skaldId)!.push(callback)

    // Return unsubscribe function
    return () => {
      const callbacks = this.skaldCallbacks.get(skaldId)
      if (callbacks) {
        const index = callbacks.indexOf(callback)
        if (index > -1) {
          callbacks.splice(index, 1)
        }
        if (callbacks.length === 0) {
          this.skaldCallbacks.delete(skaldId)
        }
      }
    }
  }

  subscribeToTask(taskId: string, callback: EventCallback<TaskEvent>): () => void {
    if (!this.taskCallbacks.has(taskId)) {
      this.taskCallbacks.set(taskId, [])
    }
    this.taskCallbacks.get(taskId)!.push(callback)

    // Return unsubscribe function
    return () => {
      const callbacks = this.taskCallbacks.get(taskId)
      if (callbacks) {
        const index = callbacks.indexOf(callback)
        if (index > -1) {
          callbacks.splice(index, 1)
        }
        if (callbacks.length === 0) {
          this.taskCallbacks.delete(taskId)
        }
      }
    }
  }

  subscribeToConnection(callback: ConnectionStateCallback): () => void {
    this.connectionCallbacks.push(callback)
    
    // Return unsubscribe function
    return () => {
      const index = this.connectionCallbacks.indexOf(callback)
      if (index > -1) {
        this.connectionCallbacks.splice(index, 1)
      }
    }
  }

  // Event handling
  private handleSkaldEvent(event: SkaldEvent): void {
    const callbacks = this.skaldCallbacks.get(event.skaldId)
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(event)
        } catch (error) {
          console.error('Error in Skald event callback:', error)
        }
      })
    }
  }

  private handleTaskEvent(event: TaskEvent): void {
    const callbacks = this.taskCallbacks.get(event.taskId)
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(event)
        } catch (error) {
          console.error('Error in Task event callback:', error)
        }
      })
    }
  }

  private notifyConnectionState(connected: boolean): void {
    this.connectionCallbacks.forEach(callback => {
      try {
        callback(connected)
      } catch (error) {
        console.error('Error in connection state callback:', error)
      }
    })
  }

  // Connection state
  isConnected(): boolean {
    return this.connected
  }

  getLastError(): Error | null {
    return this.lastError
  }

  // Mock events for development
  startMockEvents(): void {
    if (import.meta.env.DEV) {
      this.startMockSkaldEvents()
      this.startMockTaskEvents()
    }
  }

  private startMockSkaldEvents(): void {
    const mockSkaldIds = ['skald-node-001', 'skald-node-002', 'skald-edge-001']
    
    setInterval(() => {
      const skaldId = mockSkaldIds[Math.floor(Math.random() * mockSkaldIds.length)]
      const event: SkaldEvent = {
        type: 'skald_heartbeat',
        skaldId,
        data: {
          heartbeat: Math.floor(Math.random() * 100)
        }
      }
      this.handleSkaldEvent(event)
    }, 5000)
  }

  private startMockTaskEvents(): void {
    const mockTaskIds = ['task-001', 'task-002', 'task-003', 'task-004', 'task-005']
    
    setInterval(() => {
      const taskId = mockTaskIds[Math.floor(Math.random() * mockTaskIds.length)]
      const event: TaskEvent = {
        type: 'task_heartbeat',
        taskId,
        data: {
          heartbeat: Math.floor(Math.random() * 200)
        }
      }
      this.handleTaskEvent(event)
    }, 3000)
  }
}

export const sseManager = new SSEManager()