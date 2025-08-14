import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../lib/api/client'
import DataGrid from '../../components/ui/DataGrid'
import StatusIndicator from '../../components/ui/StatusIndicator'
import { Skald, DataGridColumn } from '../../types'

export default function SkaldsPage() {
  const { data: skalds, isLoading } = useQuery({
    queryKey: ['skalds'],
    queryFn: () => apiClient.getSkalds(),
  })

  const columns: DataGridColumn<Skald>[] = [
    {
      key: 'id',
      header: 'Skald ID',
      sortable: true,
    },
    {
      key: 'type',
      header: 'Type',
      sortable: true,
      render: (value) => (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
          value === 'node' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'
        }`}>
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
      key: 'supportedTasks',
      header: 'Supported Tasks',
      sortable: false,
      render: (value: string[]) => (
        <div className="flex flex-wrap gap-1">
          {value.slice(0, 3).map((task, index) => (
            <span key={index} className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-800">
              {task}
            </span>
          ))}
          {value.length > 3 && (
            <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-800">
              +{value.length - 3} more
            </span>
          )}
        </div>
      )
    },
    {
      key: 'currentTasks',
      header: 'Current Tasks',
      sortable: true,
      render: (value: string[]) => (
        <span className="text-sm text-gray-900">{value.length}</span>
      )
    }
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Skalds</h1>
        <p className="mt-1 text-sm text-gray-500">
          Monitor and manage your Skald workers
        </p>
      </div>

      <DataGrid
        data={skalds?.items || []}
        columns={columns}
        loading={isLoading}
      />
    </div>
  )
}