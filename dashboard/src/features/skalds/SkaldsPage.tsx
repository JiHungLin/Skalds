import { useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../lib/api/client'
import DataGrid from '../../components/ui/DataGrid'
import StatusIndicator from '../../components/ui/StatusIndicator'
import { Skald, DataGridColumn } from '../../types'
import { XCircleIcon, WifiIcon } from '@heroicons/react/24/outline'
import { useSSE } from '../../contexts/SSEContext'

export default function SkaldsPage() {
  const { data: skalds, isLoading, error } = useQuery({
    queryKey: ['skalds'],
    queryFn: () => apiClient.getSkalds(),
    retry: 2,
    retryDelay: 1000,
  })

  // Get SSE context for real-time updates
  const { skalds: sseSkalds, isConnected, lastError: sseError, updateSkald } = useSSE()

  // Merge API data with SSE updates
  const mergedSkalds = useMemo(() => {
    if (!skalds?.items) return []
    
    return skalds.items.map(skald => {
      const sseSkald = sseSkalds.get(skald.id)
      if (sseSkald) {
        // Merge API data with SSE updates, prioritizing SSE for real-time fields
        return {
          ...skald,
          ...sseSkald,
          // Keep original API data for fields that SSE doesn't update
          supportedTasks: skald.supportedTasks,
          type: skald.type
        }
      }
      return skald
    })
  }, [skalds?.items, sseSkalds])

  // Subscribe to SSE events for all skalds
  useEffect(() => {
    if (!skalds?.items) return

    const unsubscribers: (() => void)[] = []

    skalds.items.forEach(skald => {
      // Initialize skald in SSE context if not already present
      if (!sseSkalds.has(skald.id)) {
        updateSkald(skald.id, skald)
      }
    })

    return () => {
      unsubscribers.forEach(unsub => unsub())
    }
  }, [skalds?.items, sseSkalds, updateSkald])

  // Log API call status and SSE connection for debugging
  useEffect(() => {
    console.log('SkaldsPage status:', {
      isLoading,
      error,
      skalds: skalds?.items?.length || 0,
      sseConnected: isConnected,
      sseError,
      sseSkalds: sseSkalds.size
    })
  }, [isLoading, error, skalds, isConnected, sseError, sseSkalds])

  if (error) {
    console.error('Skalds API error:', error)
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Skalds</h1>
          <p className="mt-1 text-sm text-gray-500">
            Monitor and manage your Skald workers
          </p>
        </div>
        
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <XCircleIcon className="h-5 w-5 text-red-400" />
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                Failed to Load Skalds
              </h3>
              <div className="mt-2 text-sm text-red-700">
                <p>Unable to fetch Skald data from the API.</p>
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Skalds</h1>
          <p className="mt-1 text-sm text-gray-500">
            Monitor and manage your Skald workers
          </p>
        </div>
        
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
      </div>

      <DataGrid
        data={mergedSkalds}
        columns={columns}
        loading={isLoading}
      />
    </div>
  )
}