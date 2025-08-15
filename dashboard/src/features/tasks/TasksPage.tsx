import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../lib/api/client'
import DataGrid from '../../components/ui/DataGrid'
import StatusIndicator from '../../components/ui/StatusIndicator'
import { Task, DataGridColumn, TaskStatus } from '../../types'
import { format } from 'date-fns'
import { XCircleIcon } from '@heroicons/react/24/outline'

export default function TasksPage() {
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<TaskStatus | undefined>()
  const pageSize = 10

  const { data: tasks, isLoading, error } = useQuery({
    queryKey: ['tasks', page, statusFilter],
    queryFn: () => apiClient.getTasks({
      page,
      pageSize,
      status: statusFilter
    }),
    retry: 2,
    retryDelay: 1000,
  })

  // Log API call status for debugging
  useEffect(() => {
    console.log('TasksPage component mounted - API call status:', { isLoading, error, tasks, page, statusFilter })
  }, [isLoading, error, tasks, page, statusFilter])

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
      key: 'type',
      header: 'Type',
      sortable: true,
      render: (value) => (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
          {value}
        </span>
      )
    },
    {
      key: 'status',
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
      key: 'createdAt',
      header: 'Created',
      sortable: true,
      render: (value) => (
        <span className="text-sm text-gray-500">
          {format(new Date(value), 'MMM dd, HH:mm')}
        </span>
      )
    },
    {
      key: 'updatedAt',
      header: 'Updated',
      sortable: true,
      render: (value) => (
        <span className="text-sm text-gray-500">
          {format(new Date(value), 'MMM dd, HH:mm')}
        </span>
      )
    }
  ]

  const statusOptions: (TaskStatus | undefined)[] = [
    undefined,
    'Created',
    'Assigning', 
    'Running',
    'Completed',
    'Failed',
    'Canceled'
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
          <select
            value={statusFilter || ''}
            onChange={(e) => setStatusFilter(e.target.value as TaskStatus || undefined)}
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
        data={tasks?.items || []}
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