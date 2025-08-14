import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../lib/api/client'
import StatusIndicator from '../../components/ui/StatusIndicator'
import { 
  ServerIcon, 
  ClipboardDocumentListIcon,
  CheckCircleIcon,
  XCircleIcon
} from '@heroicons/react/24/outline'

export default function Dashboard() {
  const { data: summary, isLoading } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => apiClient.getDashboardSummary(),
  })

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="card">
                <div className="card-content">
                  <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                  <div className="h-8 bg-gray-200 rounded w-1/2"></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  const stats = [
    {
      name: 'Total Skalds',
      value: summary?.totalSkalds || 0,
      subValue: `${summary?.onlineSkalds || 0} online`,
      icon: ServerIcon,
      color: 'text-primary-600',
      bgColor: 'bg-primary-100'
    },
    {
      name: 'Total Tasks',
      value: summary?.totalTasks || 0,
      subValue: `${summary?.runningTasks || 0} running`,
      icon: ClipboardDocumentListIcon,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100'
    },
    {
      name: 'Completed Tasks',
      value: summary?.completedTasks || 0,
      subValue: 'Successfully finished',
      icon: CheckCircleIcon,
      color: 'text-success-600',
      bgColor: 'bg-success-100'
    },
    {
      name: 'Failed Tasks',
      value: summary?.failedTasks || 0,
      subValue: 'Need attention',
      icon: XCircleIcon,
      color: 'text-danger-600',
      bgColor: 'bg-danger-100'
    }
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Overview of your Skald system status and performance
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <div key={stat.name} className="card">
            <div className="card-content">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className={`p-3 rounded-lg ${stat.bgColor}`}>
                    <stat.icon className={`h-6 w-6 ${stat.color}`} />
                  </div>
                </div>
                <div className="ml-4 flex-1">
                  <div className="text-sm font-medium text-gray-500">{stat.name}</div>
                  <div className="text-2xl font-bold text-gray-900">{stat.value}</div>
                  <div className="text-xs text-gray-400">{stat.subValue}</div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">System Status</h3>
          </div>
          <div className="card-content space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Skald Connectivity</span>
              <StatusIndicator 
                status={summary?.onlineSkalds === summary?.totalSkalds ? 'online' : 'offline'} 
                animated 
              />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Task Processing</span>
              <StatusIndicator 
                status={summary?.runningTasks && summary.runningTasks > 0 ? 'Running' : 'Completed'} 
                animated 
              />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">System Health</span>
              <StatusIndicator 
                status={summary?.failedTasks === 0 ? 'online' : 'offline'} 
                animated 
              />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">Quick Actions</h3>
          </div>
          <div className="card-content space-y-3">
            <button className="btn btn-primary btn-md w-full">
              View All Tasks
            </button>
            <button className="btn btn-secondary btn-md w-full">
              Monitor Skalds
            </button>
            <button className="btn btn-secondary btn-md w-full">
              System Logs
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}