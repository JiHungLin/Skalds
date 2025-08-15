import { ReactNode } from 'react';

// Core Skald Types
export interface Skald {
  id: string;
  type: 'node' | 'edge';
  status: 'online' | 'offline';
  lastHeartbeat: string;
  supportedTasks: string[];
  currentTasks: string[];
}

// Task Types
export interface Task {
  id: string;
  className: string;
  lifecycleStatus: TaskStatus;
  executor?: string;
  createDateTime: string;
  updateDateTime: string;
  attachments: Record<string, any>;
  heartbeat: number;
  error?: string;
  exception?: string;
}

export type TaskStatus =
  | 'Created'
  | 'Assigning'
  | 'Running'
  | 'Paused'
  | 'Finished'
  | 'Failed'
  | 'Cancelled';

// SSE Event Types
export interface SkaldEvent {
  type: 'skald_status' | 'skald_heartbeat';
  skaldId: string;
  data: {
    status?: string;
    heartbeat?: number;
    tasks?: string[];
  };
}

export interface TaskEvent {
  type: 'task_heartbeat' | 'task_error' | 'task_exception';
  taskId: string;
  data: {
    heartbeat?: number;
    error?: string;
    exception?: string;
  };
}

// API Response Types
export interface GetSkaldsResponse {
  items: Skald[];
  total: number;
}

export interface GetTasksRequest {
  page: number;
  pageSize: number;
  status?: TaskStatus;
  className?: string;
  executor?: string;
}

export interface GetTasksResponse {
  items: Task[];
  total: number;
  page: number;
  pageSize: number;
}

export interface UpdateTaskStatusRequest {
  status: 'Created' | 'Cancelled';
}

export interface UpdateTaskAttachmentsRequest {
  attachments: Record<string, any>;
}

// Dashboard Summary Types
export interface DashboardSummary {
  totalSkalds: number;
  onlineSkalds: number;
  totalTasks: number;
  runningTasks: number;
  completedTasks: number;
  failedTasks: number;
}

// UI Component Types
export interface StatusIndicatorProps {
  status: 'online' | 'offline' | TaskStatus;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  animated?: boolean;
}

export interface DataGridColumn<T> {
  key: keyof T;
  header: string;
  sortable?: boolean;
  render?: (value: any, row: T) => ReactNode;
}

export interface DataGridProps<T> {
  data: T[];
  columns: DataGridColumn<T>[];
  loading?: boolean;
  pagination?: {
    page: number;
    pageSize: number;
    total: number;
    onPageChange: (page: number) => void;
  };
  onRowClick?: (row: T) => void;
}