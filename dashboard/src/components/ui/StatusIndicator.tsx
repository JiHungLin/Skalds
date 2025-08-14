import { StatusIndicatorProps } from '../../types'
import { clsx } from 'clsx'

const statusConfig = {
  online: {
    color: 'status-online',
    label: 'Online',
    dotColor: 'bg-success-500'
  },
  offline: {
    color: 'status-offline',
    label: 'Offline',
    dotColor: 'bg-gray-500'
  },
  Created: {
    color: 'status-created',
    label: 'Created',
    dotColor: 'bg-warning-500'
  },
  Assigning: {
    color: 'status-assigning',
    label: 'Assigning',
    dotColor: 'bg-warning-500'
  },
  Running: {
    color: 'status-running',
    label: 'Running',
    dotColor: 'bg-primary-500'
  },
  Completed: {
    color: 'status-completed',
    label: 'Completed',
    dotColor: 'bg-success-500'
  },
  Failed: {
    color: 'status-failed',
    label: 'Failed',
    dotColor: 'bg-danger-500'
  },
  Canceled: {
    color: 'status-canceled',
    label: 'Canceled',
    dotColor: 'bg-gray-500'
  }
}

const sizeConfig = {
  sm: {
    badge: 'px-2 py-1 text-xs',
    dot: 'w-2 h-2'
  },
  md: {
    badge: 'px-2.5 py-1.5 text-sm',
    dot: 'w-3 h-3'
  },
  lg: {
    badge: 'px-3 py-2 text-base',
    dot: 'w-4 h-4'
  }
}

export default function StatusIndicator({ 
  status, 
  size = 'md', 
  showLabel = true, 
  animated = false 
}: StatusIndicatorProps) {
  const config = statusConfig[status]
  const sizeStyles = sizeConfig[size]

  if (!config) {
    return null
  }

  if (!showLabel) {
    return (
      <div className="flex items-center">
        <div 
          className={clsx(
            'rounded-full',
            sizeStyles.dot,
            config.dotColor,
            animated && (status === 'online' || status === 'Running') && 'animate-pulse'
          )}
        />
      </div>
    )
  }

  return (
    <span 
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full border font-medium',
        config.color,
        sizeStyles.badge
      )}
    >
      <div 
        className={clsx(
          'rounded-full',
          sizeStyles.dot,
          config.dotColor,
          animated && (status === 'online' || status === 'Running') && 'animate-heartbeat'
        )}
      />
      {config.label}
    </span>
  )
}