import { useState, useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../lib/api/client'
import DataGrid from '../../components/ui/DataGrid'
import StatusIndicator from '../../components/ui/StatusIndicator'
import { Task, DataGridColumn, TaskLifecycleStatus } from '../../types'
import { format } from 'date-fns'
import { XCircleIcon, WifiIcon } from '@heroicons/react/24/outline'
import { useSSE } from '../../contexts/SSEContext'

export default function TasksPage() {
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<TaskLifecycleStatus | undefined>()
  const pageSize = 10

  const { data: tasks, isLoading, error } = useQuery({
    queryKey: ['tasks', page, statusFilter],
    queryFn: () => apiClient.getTasks({
      page,
      pageSize,
      lifecycleStatus: statusFilter
    }),
    retry: 2,
    retryDelay: 1000,
  })

  // Get SSE context for real-time updates
  const { tasks: sseTasks, isConnected, lastError: sseError, updateTask, subscribeToTask } = useSSE()

  // Create a stable dependency for sseTasks changes
  const sseTasksVersion = useMemo(() => {
    // Create a hash of all task data to detect changes
    return Array.from(sseTasks.entries())
      .map(([id, task]) => `${id}:${task.heartbeat}:${task.lifecycleStatus}:${task.updateDateTime}`)
      .join('|')
  }, [sseTasks])

  // Merge API data with SSE updates
  const mergedTasks = useMemo(() => {
    if (!tasks?.items) return []
    
    return tasks.items.map(task => {
      const sseTask = sseTasks.get(task.id)
      if (sseTask) {
        // Merge API data with SSE updates, prioritizing SSE for real-time fields
        return {
          ...task,
          ...sseTask,
          // Keep original API data for fields that SSE doesn't update
          className: task.className,
          createDateTime: task.createDateTime
        }
      }
      return task
    })
  }, [tasks?.items, sseTasksVersion])

  // Subscribe to SSE events for all tasks
  useEffect(() => {
    if (!tasks?.items) return

    const unsubscribers: (() => void)[] = []

    tasks.items.forEach(task => {
      // Initialize task in SSE context if not already present
      if (!sseTasks.has(task.id)) {
        updateTask(task.id, task)
      }
      
      // Subscribe to task events for real-time updates
      // const unsubscribe = subscribeToTask(task.id, (event) => {
      //   console.log(`Received event for task ${task.id}:`, event)
      //   // The event will be automatically handled by the SSE context
      //   // which will update the tasks Map and trigger re-renders
      // })
      // unsubscribers.push(unsubscribe)
    })

    return () => {
      unsubscribers.forEach(unsub => unsub())
    }
  }, [tasks?.items, sseTasks, updateTask, subscribeToTask])

  // Log API call status and SSE connection for debugging
  // useEffect(() => {
  //   console.log('TasksPage status:', {
  //     isLoading,
  //     error,
  //     tasks: tasks?.items?.length || 0,
  //     sseConnected: isConnected,
  //     sseError,
  //     sseTasks: sseTasks.size,
  //     page,
  //     statusFilter
  //   })
  // }, [isLoading, error, tasks, isConnected, sseError, sseTasks, page, statusFilter])

  if (error) {
    console.error('Tasks API error:', error)
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Tasks</h1>
            <p className="mt-1 text-sm text-gray-500">
              Monitor and manage task execution
            </p>
          </div>
        </div>
        
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <XCircleIcon className="h-5 w-5 text-red-400" />
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                Failed to Load Tasks
              </h3>
              <div className="mt-2 text-sm text-red-700">
                <p>Unable to fetch task data from the API.</p>
                <p className="mt-2 font-mono text-xs bg-red-100 p-2 rounded">
                  Error: {error instanceof Error ? error.message : 'Unknown error'}
                </p>
              </div>
              <div className="mt-4">
                <button
                  onClick={() => window.location.reload()}
                  className="btn btn-sm btn-primary"
                >
                  Retry
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const columns: DataGridColumn<Task>[] = [
    {
      key: 'id',
      header: 'Task ID',
      sortable: true,
      render: (value) => (
        <span className="font-mono text-sm">{value}</span>
      )
    },
    {
      key: 'className',
      header: 'Type',
      sortable: true,
      render: (value) => (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
          {value}
        </span>
      )
    },
    {
      key: 'lifecycleStatus',
      header: 'Status',
      sortable: true,
      render: (value) => <StatusIndicator status={value} animated />
    },
    {
      key: 'executor',
      header: 'Executor',
      sortable: true,
      render: (value) => (
        <span className="text-sm text-gray-900">
          {value || 'Unassigned'}
        </span>
      )
    },
    {
      key: 'heartbeat',
      header: 'Heartbeat',
      sortable: true,
      render: (value, row) => {
        const sseTask = sseTasks.get(row.id)
        let heartbeat = sseTask?.heartbeat ?? value ?? 0
        // If the task is Finished, display heartbeat as 200
        if (row.lifecycleStatus === 'Finished') {
          heartbeat = 200
        }
        return (
          <span className={`text-sm font-mono ${heartbeat > 0 ? 'text-green-600' : 'text-gray-400'}`}>
            {heartbeat}
          </span>
        )
      }
    },
    {
      key: 'createDateTime',
      header: 'Created',
      sortable: true,
      render: (value) => {
        try {
          const date = new Date(value)
          if (isNaN(date.getTime())) {
            return <span className="text-sm text-gray-400">Invalid date</span>
          }
          return (
            <span className="text-sm text-gray-500">
              {format(date, 'MMM dd, HH:mm')}
            </span>
          )
        } catch (error) {
          console.warn('Invalid date value:', value, error)
          return <span className="text-sm text-gray-400">Invalid date</span>
        }
      }
    },
    {
      key: 'updateDateTime',
      header: 'Updated',
      sortable: true,
      render: (value) => {
        try {
          const date = new Date(value)
          if (isNaN(date.getTime())) {
            return <span className="text-sm text-gray-400">Invalid date</span>
          }
          return (
            <span className="text-sm text-gray-500">
              {format(date, 'MMM dd, HH:mm')}
            </span>
          )
        } catch (error) {
          console.warn('Invalid date value:', value, error)
          return <span className="text-sm text-gray-400">Invalid date</span>
        }
      }
    }
  ]

  const statusOptions: (TaskLifecycleStatus | undefined)[] = [
    undefined,
    'Created',
    'Assigning',
    'Running',
    'Paused',
    'Finished',
    'Failed',
    'Cancelled'
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Tasks</h1>
          <p className="mt-1 text-sm text-gray-500">
            Monitor and manage task execution
          </p>
        </div>
        
        <div className="flex items-center space-x-4">
          {/* SSE Connection Status */}
          <div className="flex items-center space-x-2">
            <WifiIcon
              className={`h-5 w-5 ${isConnected ? 'text-green-500' : 'text-red-500'}`}
            />
            <span className={`text-sm font-medium ${isConnected ? 'text-green-700' : 'text-red-700'}`}>
              {isConnected ? 'Live Updates' : 'Disconnected'}
            </span>
            {sseError && (
              <span className="text-xs text-red-500" title={sseError.message}>
                (Error)
              </span>
            )}
          </div>
          
          <select
            value={statusFilter || ''}
            onChange={(e) => setStatusFilter(e.target.value as TaskLifecycleStatus || undefined)}
            className="block w-40 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
          >
            {statusOptions.map((status) => (
              <option key={status || 'all'} value={status || ''}>
                {status || 'All Status'}
              </option>
            ))}
          </select>
        </div>
      </div>

      <DataGrid
        data={mergedTasks}
        columns={columns}
        loading={isLoading}
        pagination={{
          page,
          pageSize,
          total: tasks?.total || 0,
          onPageChange: setPage
        }}
      />
    </div>
  )
}