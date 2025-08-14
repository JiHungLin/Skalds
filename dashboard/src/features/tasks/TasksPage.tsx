import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../lib/api/client'
import DataGrid from '../../components/ui/DataGrid'
import StatusIndicator from '../../components/ui/StatusIndicator'
import { Task, DataGridColumn, TaskStatus } from '../../types'
import { format } from 'date-fns'

export default function TasksPage() {
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<TaskStatus | undefined>()
  const pageSize = 10

  const { data: tasks, isLoading } = useQuery({
    queryKey: ['tasks', page, statusFilter],
    queryFn: () => apiClient.getTasks({
      page,
      pageSize,
      status: statusFilter
    }),
  })

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