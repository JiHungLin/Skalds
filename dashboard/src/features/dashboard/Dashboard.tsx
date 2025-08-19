import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../../lib/api/client'
import StatusIndicator from '../../components/ui/StatusIndicator'
import {
  ServerIcon,
  ClipboardDocumentListIcon,
  CheckCircleIcon,
  XCircleIcon
} from '@heroicons/react/24/outline'

export default function Dashboard() {
  const navigate = useNavigate()
  const { data: summary, isLoading, error } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => apiClient.getDashboardSummary(),
    retry: 2,
    retryDelay: 1000,
  })

  // Log API call status for debugging
  useEffect(() => {
    console.log('Dashboard component mounted - API call status:', { isLoading, error, summary })
  }, [isLoading, error, summary])

  if (error) {
    console.error('Dashboard API error:', error)
    return (
      <div className="space-y-6">
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <XCircleIcon className="h-5 w-5 text-red-400" />
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                API Connection Error
              </h3>
              <div className="mt-2 text-sm text-red-700">
                <p>Failed to load dashboard data. Please check:</p>
                <ul className="list-disc list-inside mt-1">
                  <li>SystemController backend is running</li>
                  <li>API endpoints are accessible</li>
                  <li>Network connectivity</li>
                </ul>
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
      name: 'Finished Tasks',
      value: summary?.finishedTasks || 0,
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
          Overview of your Skalds system status and performance
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

      {/* System Status */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">System Status</h3>
          </div>
          <div className="card-content space-y-4">
            {/* Skalds Connectivity with detailed status */}
            <div className="flex items-center justify-between">
              <div className="flex flex-col">
                <span className="text-sm font-medium text-gray-900">Skalds Connectivity</span>
                <span className="text-xs text-gray-500">
                  {summary?.onlineSkalds || 0} of {summary?.totalSkalds || 0} skalds online
                </span>
              </div>
              <div className="flex items-center space-x-2">
                {(() => {
                  const onlineRatio = summary?.totalSkalds ? (summary.onlineSkalds / summary.totalSkalds) : 0;
                  if (onlineRatio === 1) {
                    return (
                      <div title="Status: Online - All Skalds nodes are connected and operational">
                        <StatusIndicator status="online" animated />
                      </div>
                    );
                  } else if (onlineRatio >= 0.7) {
                    return (
                      <span
                        className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1.5 text-sm bg-warning-100 text-warning-800 border-warning-200 cursor-help"
                        title={`Status: Partial - ${Math.round(onlineRatio * 100)}% of skalds online (≥70% threshold met, but not all nodes available)`}
                      >
                        <div className="w-3 h-3 rounded-full bg-warning-500 animate-pulse" />
                        Partial
                      </span>
                    );
                  } else if (onlineRatio > 0) {
                    return (
                      <span
                        className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1.5 text-sm bg-danger-100 text-danger-800 border-danger-200 cursor-help"
                        title={`Status: Degraded - Only ${Math.round(onlineRatio * 100)}% of skalds online (<70% threshold, system performance may be impacted)`}
                      >
                        <div className="w-3 h-3 rounded-full bg-danger-500 animate-pulse" />
                        Degraded
                      </span>
                    );
                  } else {
                    return (
                      <div title="Status: Offline - No Skalds nodes are currently connected">
                        <StatusIndicator status="offline" animated />
                      </div>
                    );
                  }
                })()}
              </div>
            </div>

            {/* Task Processing with detailed metrics */}
            <div className="flex items-center justify-between">
              <div className="flex flex-col">
                <span className="text-sm font-medium text-gray-900">Task Processing</span>
                <span className="text-xs text-gray-500">
                  {(() => {
                    const running = summary?.runningTasks || 0;
                    const finished = summary?.finishedTasks || 0;
                    const failed = summary?.failedTasks || 0;
                    if (running === 0 && finished === 0 && failed > 0) {
                      return `0 running, 0 finished, all failed`;
                    }
                    return `${running} running, ${finished} finished`;
                  })()}
                </span>
              </div>
              <div className="flex items-center space-x-2">
                {(() => {
                  const runningTasks = summary?.runningTasks || 0;
                  const failedTasks = summary?.failedTasks || 0;
                  
                  if (runningTasks > 0) {
                    return (
                      <div title={`Status: Running - ${runningTasks} task(s) currently being processed`}>
                        <StatusIndicator status="Running" animated />
                      </div>
                    );
                  } else if (failedTasks === 0) {
                    return (
                      <div title="Status: Finished - No active tasks, all previous tasks finished successfully">
                        <StatusIndicator status="Finished" />
                      </div>
                    );
                  } else {
                    return (
                      <span
                        className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1.5 text-sm bg-warning-100 text-warning-800 border-warning-200 cursor-help"
                        title={`Status: Idle - No tasks running, but ${failedTasks} failed task(s) require attention`}
                      >
                        <div className="w-3 h-3 rounded-full bg-warning-500" />
                        Idle
                      </span>
                    );
                  }
                })()}
              </div>
            </div>

            {/* System Health with error details */}
            <div className="flex items-center justify-between">
              <div className="flex flex-col">
                <span className="text-sm font-medium text-gray-900">System Health</span>
                <span className="text-xs text-gray-500">
                  {summary?.failedTasks || 0} failed tasks detected
                </span>
              </div>
              <div className="flex items-center space-x-2">
                {(() => {
                  const failedTasks = summary?.failedTasks || 0;
                  const totalTasks = summary?.totalTasks || 0;
                  const failureRate = totalTasks > 0 ? failedTasks / totalTasks : 0;
                  
                  if (failedTasks === 0) {
                    return (
                      <span
                        className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1.5 text-sm bg-success-100 text-success-800 border-success-200 cursor-help"
                        title="Status: Healthy - No failed tasks detected, system operating normally"
                      >
                        <div className="w-3 h-3 rounded-full bg-success-500" />
                        Healthy
                      </span>
                    );
                  } else if (failureRate < 0.1) {
                    return (
                      <span
                        className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1.5 text-sm bg-warning-100 text-warning-800 border-warning-200 cursor-help"
                        title={`Status: Warning - ${failedTasks} failed task(s), failure rate ${Math.round(failureRate * 100)}% (<10% threshold, monitor closely)`}
                      >
                        <div className="w-3 h-3 rounded-full bg-warning-500 animate-pulse" />
                        Warning
                      </span>
                    );
                  } else {
                    return (
                      <span
                        className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1.5 text-sm bg-danger-100 text-danger-800 border-danger-200 cursor-help"
                        title={`Status: Critical - ${failedTasks} failed task(s), failure rate ${Math.round(failureRate * 100)}% (≥10% threshold, immediate attention required)`}
                      >
                        <div className="w-3 h-3 rounded-full bg-danger-500 animate-pulse" />
                        Critical
                      </span>
                    );
                  }
                })()}
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">Quick Actions</h3>
          </div>
          <div className="card-content space-y-3">
            <button
              className="btn btn-primary btn-md w-full"
              onClick={() => navigate('/tasks')}
            >
              View All Tasks
            </button>
            <button
              className="btn btn-primary btn-md w-full"
              onClick={() => navigate('/skalds')}
            >
              Monitor Skalds
            </button>
            <button
              className="btn btn-primary btn-md w-full"
              onClick={() => alert('System Logs feature coming soon!')}
            >
              System Logs
            </button>
          </div>
        </div>
      </div>

      {/* Status Legend */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-gray-900">Status Legend</h3>
          <p className="text-sm text-gray-500 mt-1">Understanding system status indicators and their logic</p>
        </div>
        <div className="card-content">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 font-medium text-gray-900">Category</th>
                  <th className="text-left py-3 font-medium text-gray-900">Status</th>
                  <th className="text-left py-3 font-medium text-gray-900">Logic & Conditions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {/* Skalds Connectivity */}
                <tr>
                  <td rowSpan={4} className="py-3 font-medium text-gray-900 align-top border-r border-gray-100">
                    Skalds Connectivity
                  </td>
                  <td className="py-3">
                    <span className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs bg-success-100 text-success-800 border-success-200">
                      <div className="w-2 h-2 rounded-full bg-success-500" />
                      Online
                    </span>
                  </td>
                  <td className="py-3 text-gray-600">All Skalds nodes are connected and operational (100% online)</td>
                </tr>
                <tr>
                  <td className="py-3">
                    <span className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs bg-warning-100 text-warning-800 border-warning-200">
                      <div className="w-2 h-2 rounded-full bg-warning-500" />
                      Partial
                    </span>
                  </td>
                  <td className="py-3 text-gray-600">≥70% of skalds online, but not all nodes are available</td>
                </tr>
                <tr>
                  <td className="py-3">
                    <span className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs bg-danger-100 text-danger-800 border-danger-200">
                      <div className="w-2 h-2 rounded-full bg-danger-500" />
                      Degraded
                    </span>
                  </td>
                  <td className="py-3 text-gray-600">&lt;70% of skalds online, system performance may be impacted</td>
                </tr>
                <tr>
                  <td className="py-3">
                    <span className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs bg-gray-100 text-gray-800 border-gray-200">
                      <div className="w-2 h-2 rounded-full bg-gray-500" />
                      Offline
                    </span>
                  </td>
                  <td className="py-3 text-gray-600">No Skalds nodes are currently connected (0% online)</td>
                </tr>
                
                {/* Task Processing */}
                <tr>
                  <td rowSpan={3} className="py-3 font-medium text-gray-900 align-top border-r border-gray-100">
                    Task Processing
                  </td>
                  <td className="py-3">
                    <span className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs bg-primary-100 text-primary-800 border-primary-200">
                      <div className="w-2 h-2 rounded-full bg-primary-500" />
                      Running
                    </span>
                  </td>
                  <td className="py-3 text-gray-600">One or more tasks are currently being processed</td>
                </tr>
                <tr>
                  <td className="py-3">
                    <span className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs bg-success-100 text-success-800 border-success-200">
                      <div className="w-2 h-2 rounded-full bg-success-500" />
                      Finished
                    </span>
                  </td>
                  <td className="py-3 text-gray-600">No active tasks, all previous tasks finished successfully</td>
                </tr>
                <tr>
                  <td className="py-3">
                    <span className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs bg-warning-100 text-warning-800 border-warning-200">
                      <div className="w-2 h-2 rounded-full bg-warning-500" />
                      Idle
                    </span>
                  </td>
                  <td className="py-3 text-gray-600">No tasks currently running, but failed tasks exist and require attention</td>
                </tr>
                
                {/* System Health */}
                <tr>
                  <td rowSpan={3} className="py-3 font-medium text-gray-900 align-top border-r border-gray-100">
                    System Health
                  </td>
                  <td className="py-3">
                    <span className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs bg-success-100 text-success-800 border-success-200">
                      <div className="w-2 h-2 rounded-full bg-success-500" />
                      Healthy
                    </span>
                  </td>
                  <td className="py-3 text-gray-600">No failed tasks detected, system operating normally (0% failure rate)</td>
                </tr>
                <tr>
                  <td className="py-3">
                    <span className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs bg-warning-100 text-warning-800 border-warning-200">
                      <div className="w-2 h-2 rounded-full bg-warning-500" />
                      Warning
                    </span>
                  </td>
                  <td className="py-3 text-gray-600">Task failure rate &lt;10%, system should be monitored closely</td>
                </tr>
                <tr>
                  <td className="py-3">
                    <span className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs bg-danger-100 text-danger-800 border-danger-200">
                      <div className="w-2 h-2 rounded-full bg-danger-500" />
                      Critical
                    </span>
                  </td>
                  <td className="py-3 text-gray-600">Task failure rate ≥10%, immediate attention and intervention required</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}