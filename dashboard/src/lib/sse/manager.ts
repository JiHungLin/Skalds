import { SkaldEvent, TaskEvent, SkaldEventCallback, TaskEventCallback, ConnectionStateCallback } from '../../types'

/**
 * SSE Manager for handling Server-Sent Events connections
 *
 * This class manages EventSource connections to the backend SSE endpoints
 * and provides subscription mechanisms for real-time updates.
 *
 * Features:
 * - Automatic reconnection with exponential backoff
 * - Event subscription by Skald/Task ID
 * - Connection state monitoring
 * - Mock events for development
 *
 * @example
 * ```typescript
 * import { sseManager } from './lib/sse/manager'
 *
 * // Connect to SSE
 * sseManager.connect()
 *
 * // Subscribe to skald events
 * const unsubscribe = sseManager.subscribeToSkald('skald-001', (event) => {
 *   console.log('Skald event:', event)
 * })
 *
 * // Cleanup
 * unsubscribe()
 * sseManager.disconnect()
 * ```
 */
class SSEManager {
  private skaldEventSource: EventSource | null = null
  private taskEventSource: EventSource | null = null
  private skaldCallbacks = new Map<string, SkaldEventCallback[]>()
  private taskCallbacks = new Map<string, TaskEventCallback[]>()
  private connectionCallbacks: ConnectionStateCallback[] = []
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private connected = false
  private lastError: Error | null = null

  /**
   * Create a new SSE Manager instance
   * @param baseUrl - Base URL for SSE endpoints (default: '/api/events')
   */
  constructor(private baseUrl: string = '/api/events') {}

  // Connection management
  /**
   * Connect to both Skald and Task SSE endpoints
   */
  connect(): void {
    this.connectSkaldEvents()
    this.connectTaskEvents()
  }

  /**
   * Disconnect from all SSE endpoints and clean up resources
   */
  disconnect(): void {
    this.disconnectSkaldEvents()
    this.disconnectTaskEvents()
    this.connected = false
    this.notifyConnectionState(false)
  }

  /**
   * Attempt to reconnect with exponential backoff
   * Will retry up to maxReconnectAttempts times
   */
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
        console.log('Received Task event:', event)
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
  /**
   * Subscribe to events for a specific Skald
   * @param skaldId - The ID of the Skald to subscribe to
   * @param callback - Function to call when events are received
   * @returns Unsubscribe function
   */
  subscribeToSkald(skaldId: string, callback: SkaldEventCallback): () => void {
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

  /**
   * Subscribe to events for a specific Task
   * @param taskId - The ID of the Task to subscribe to
   * @param callback - Function to call when events are received
   * @returns Unsubscribe function
   */
  subscribeToTask(taskId: string, callback: TaskEventCallback): () => void {
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

  /**
   * Subscribe to connection state changes
   * @param callback - Function to call when connection state changes
   * @returns Unsubscribe function
   */
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
  /**
   * Check if SSE connections are active
   * @returns True if connected, false otherwise
   */
  isConnected(): boolean {
    return this.connected
  }

  /**
   * Get the last error that occurred
   * @returns Last error or null if no error
   */
  getLastError(): Error | null {
    return this.lastError
  }

  // Mock events for development
  /**
   * Start generating mock events for development/testing
   * Only works in development mode
   */
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

/**
 * Global SSE Manager instance
 * Use this singleton instance throughout the application
 */
/**
 * 全域 SSE baseUrl，支援 .env 設定
 */
const sseBaseUrl =
  (import.meta.env.VITE_API_BASE_URL || window.location.origin) + '/api/events'

export const sseManager = new SSEManager(sseBaseUrl)