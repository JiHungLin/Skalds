import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react'
import { sseManager } from '../lib/sse/manager'
import { Skald, Task, SkaldEvent, TaskEvent } from '../types'

interface SSEContextType {
  // Connection state
  isConnected: boolean
  lastError: Error | null
  
  // Skald state
  skalds: Map<string, Skald>
  updateSkald: (skaldId: string, updates: Partial<Skald>) => void
  
  // Task state  
  tasks: Map<string, Task>
  updateTask: (taskId: string, updates: Partial<Task>) => void
  
  // Subscription methods
  subscribeToSkald: (skaldId: string, callback: (event: SkaldEvent) => void) => () => void
  subscribeToTask: (taskId: string, callback: (event: TaskEvent) => void) => () => void
  
  // Connection management
  connect: () => void
  disconnect: () => void
}

const SSEContext = createContext<SSEContextType | undefined>(undefined)

interface SSEProviderProps {
  children: ReactNode
}

export function SSEProvider({ children }: SSEProviderProps) {
  const [isConnected, setIsConnected] = useState(false)
  const [lastError, setLastError] = useState<Error | null>(null)
  const [skalds, setSkalds] = useState<Map<string, Skald>>(new Map())
  const [tasks, setTasks] = useState<Map<string, Task>>(new Map())

  // Update skald state
  const updateSkald = useCallback((skaldId: string, updates: Partial<Skald>) => {
    setSkalds(prev => {
      const newMap = new Map(prev)
      const existing = newMap.get(skaldId)
      if (existing) {
        newMap.set(skaldId, { ...existing, ...updates })
      } else {
        // Create a new skald entry if it doesn't exist
        newMap.set(skaldId, {
          id: skaldId,
          type: 'node', // Default type, will be updated by events
          status: 'offline',
          lastHeartbeat: new Date().toISOString(),
          supportedTasks: [],
          currentTasks: [],
          ...updates
        } as Skald)
      }
      return newMap
    })
  }, [])

  // Update task state
  const updateTask = useCallback((taskId: string, updates: Partial<Task>) => {
    setTasks(prev => {
      const newMap = new Map(prev)
      const existing = newMap.get(taskId)
      if (existing) {
        newMap.set(taskId, { ...existing, ...updates })
      } else {
        // Create a new task entry if it doesn't exist
        newMap.set(taskId, {
          id: taskId,
          className: 'Unknown',
          lifecycleStatus: 'Created',
          createDateTime: new Date().toISOString(),
          updateDateTime: new Date().toISOString(),
          attachments: {},
          heartbeat: 0,
          ...updates
        } as Task)
      }
      return newMap
    })
  }, [])

  // Handle skald events
  const handleSkaldEvent = useCallback((event: SkaldEvent) => {
    console.log('Received Skald event:', event)
    
    const updates: Partial<Skald> = {}
    
    switch (event.type) {
      case 'skald_status':
        if (event.data.status) {
          updates.status = event.data.status as 'online' | 'offline'
        }
        if (event.data.tasks) {
          updates.currentTasks = event.data.tasks
        }
        break
        
      case 'skald_heartbeat':
        if (event.data.heartbeat !== undefined) {
          updates.lastHeartbeat = new Date().toISOString()
          updates.status = 'online' // Heartbeat implies online
        }
        if (event.data.tasks) {
          updates.currentTasks = event.data.tasks
        }
        break
    }
    
    if (Object.keys(updates).length > 0) {
      updateSkald(event.skaldId, updates)
    }
  }, [updateSkald])

  // Handle task events
  const handleTaskEvent = useCallback((event: TaskEvent) => {
    console.log('Received Task event:', event)
    
    const updates: Partial<Task> = {
      updateDateTime: new Date().toISOString()
    }

    // Always update lifecycleStatus if present in event.data
    if (event.data.lifecycleStatus !== undefined) {
      updates.lifecycleStatus = event.data.lifecycleStatus
    }
    
    switch (event.type) {
      case 'task_heartbeat':
        if (event.data.heartbeat !== undefined) {
          updates.heartbeat = event.data.heartbeat
        }
        break
        
      case 'task_error':
        if (event.data.error) {
          updates.error = event.data.error
          updates.lifecycleStatus = 'Failed'
        }
        break
        
      case 'task_exception':
        if (event.data.exception) {
          updates.exception = event.data.exception
          updates.lifecycleStatus = 'Failed'
        }
        break
    }
    
    updateTask(event.taskId, updates)
  }, [updateTask])

  // Subscribe to skald events
  const subscribeToSkald = useCallback((skaldId: string, callback: (event: SkaldEvent) => void) => {
    return sseManager.subscribeToSkald(skaldId, callback)
  }, [])

  // Subscribe to task events
  const subscribeToTask = useCallback((taskId: string, callback: (event: TaskEvent) => void) => {
    return sseManager.subscribeToTask(taskId, callback)
  }, [])

  // Connection management
  const connect = useCallback(() => {
    sseManager.connect()
  }, [])

  const disconnect = useCallback(() => {
    sseManager.disconnect()
  }, [])

  // Initialize SSE connection and global event handlers
  useEffect(() => {
    // Subscribe to connection state changes
    const unsubscribeConnection = sseManager.subscribeToConnection((connected) => {
      setIsConnected(connected)
      setLastError(connected ? null : sseManager.getLastError())
    })

    // Set up global event handlers for all skald and task events
    const originalHandleSkaldEvent = sseManager['handleSkaldEvent'].bind(sseManager)
    const originalHandleTaskEvent = sseManager['handleTaskEvent'].bind(sseManager)
    
    // Override the event handlers to also update our context state
    sseManager['handleSkaldEvent'] = (event: SkaldEvent) => {
      originalHandleSkaldEvent(event)
      handleSkaldEvent(event)
    }
    
    sseManager['handleTaskEvent'] = (event: TaskEvent) => {
      originalHandleTaskEvent(event)
      handleTaskEvent(event)
    }

    // Connect to SSE
    sseManager.connect()

    // Start mock events in development
    if (import.meta.env.DEV) {
      sseManager.startMockEvents()
    }

    // Cleanup on unmount
    return () => {
      // Restore original handlers
      sseManager['handleSkaldEvent'] = originalHandleSkaldEvent
      sseManager['handleTaskEvent'] = originalHandleTaskEvent
      unsubscribeConnection()
      sseManager.disconnect()
    }
  }, [handleSkaldEvent, handleTaskEvent])

  // Update connection state periodically
  useEffect(() => {
    const interval = setInterval(() => {
      setIsConnected(sseManager.isConnected())
      setLastError(sseManager.getLastError())
    }, 1000)

    return () => clearInterval(interval)
  }, [])

  const contextValue: SSEContextType = {
    isConnected,
    lastError,
    skalds,
    updateSkald,
    tasks,
    updateTask,
    subscribeToSkald,
    subscribeToTask,
    connect,
    disconnect
  }

  return (
    <SSEContext.Provider value={contextValue}>
      {children}
    </SSEContext.Provider>
  )
}

export function useSSE() {
  const context = useContext(SSEContext)
  if (context === undefined) {
    throw new Error('useSSE must be used within an SSEProvider')
  }
  return context
}

// Hook for subscribing to specific skald events
export function useSkaldEvents(skaldId: string) {
  const { subscribeToSkald } = useSSE()
  const [events, setEvents] = useState<SkaldEvent[]>([])

  useEffect(() => {
    const unsubscribe = subscribeToSkald(skaldId, (event) => {
      setEvents(prev => [...prev.slice(-9), event]) // Keep last 10 events
    })

    return unsubscribe
  }, [skaldId, subscribeToSkald])

  return events
}

// Hook for subscribing to specific task events
export function useTaskEvents(taskId: string) {
  const { subscribeToTask } = useSSE()
  const [events, setEvents] = useState<TaskEvent[]>([])

  useEffect(() => {
    const unsubscribe = subscribeToTask(taskId, (event) => {
      setEvents(prev => [...prev.slice(-9), event]) // Keep last 10 events
    })

    return unsubscribe
  }, [taskId, subscribeToTask])

  return events
}