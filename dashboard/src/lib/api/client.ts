import {
  GetSkaldsResponse,
  GetTasksRequest,
  GetTasksResponse,
  Task,
  Skald,
  UpdateTaskStatusRequest,
  UpdateTaskAttachmentsRequest,
  DashboardSummary
} from '../../types/index'

// Mock data for development
const mockSkalds: Skald[] = [
  {
    id: 'skald-node-001',
    type: 'node',
    status: 'online',
    lastHeartbeat: new Date().toISOString(),
    supportedTasks: ['data_processing', 'ml_training', 'file_conversion'],
    currentTasks: ['task-001', 'task-003']
  },
  {
    id: 'skald-node-002',
    type: 'node',
    status: 'online',
    lastHeartbeat: new Date(Date.now() - 30000).toISOString(),
    supportedTasks: ['data_processing', 'image_processing'],
    currentTasks: ['task-002']
  },
  {
    id: 'skald-edge-001',
    type: 'edge',
    status: 'offline',
    lastHeartbeat: new Date(Date.now() - 300000).toISOString(),
    supportedTasks: ['sensor_data', 'edge_computing'],
    currentTasks: []
  }
]

const mockTasks: Task[] = [
  {
    id: 'task-001',
    className: 'data_processing',
    lifecycleStatus: 'Running',
    executor: 'skald-node-001',
    createDateTime: new Date(Date.now() - 3600000).toISOString(),
    updateDateTime: new Date(Date.now() - 1800000).toISOString(),
    attachments: { inputFile: 'data.csv', outputPath: '/tmp/processed' },
    heartbeat: 150,
    error: undefined,
    exception: undefined
  },
  {
    id: 'task-002',
    className: 'ml_training',
    lifecycleStatus: 'Running',
    executor: 'skald-node-002',
    createDateTime: new Date(Date.now() - 7200000).toISOString(),
    updateDateTime: new Date(Date.now() - 900000).toISOString(),
    attachments: { model: 'neural_network', dataset: 'training_data.json' },
    heartbeat: 75,
    error: undefined,
    exception: undefined
  },
  {
    id: 'task-003',
    className: 'file_conversion',
    lifecycleStatus: 'Finished',
    executor: 'skald-node-001',
    createDateTime: new Date(Date.now() - 1800000).toISOString(),
    updateDateTime: new Date(Date.now() - 300000).toISOString(),
    attachments: { sourceFile: 'document.pdf', targetFormat: 'docx' },
    heartbeat: 200,
    error: undefined,
    exception: undefined
  },
  {
    id: 'task-004',
    className: 'data_processing',
    lifecycleStatus: 'Failed',
    executor: 'skald-node-002',
    createDateTime: new Date(Date.now() - 5400000).toISOString(),
    updateDateTime: new Date(Date.now() - 3600000).toISOString(),
    attachments: { inputFile: 'corrupted_data.csv' },
    heartbeat: -1,
    error: 'File format not supported',
    exception: 'ValueError: Invalid data format'
  },
  {
    id: 'task-005',
    className: 'image_processing',
    lifecycleStatus: 'Created',
    executor: undefined,
    createDateTime: new Date(Date.now() - 600000).toISOString(),
    updateDateTime: new Date(Date.now() - 600000).toISOString(),
    attachments: { images: ['img1.jpg', 'img2.jpg'], filter: 'blur' },
    heartbeat: 0,
    error: undefined,
    exception: undefined
  }
]

// Simulate API delay (removed unused function)
// const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

class ApiClient {
  private baseUrl: string
  private useMockData: boolean = false

  constructor() {
    // Use current origin as base URL for API calls
    this.baseUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin    
    
    // Enable mock data only in development if API is not available
    this.useMockData = import.meta.env.DEV && import.meta.env.VITE_USE_MOCK_DATA === 'true'
    
    console.log(`API Client initialized - Base URL: ${this.baseUrl}, Mock Data: ${this.useMockData}`)
  }

  private async fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    
    console.log(`Making API call to: ${url}`)
    
    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
        ...options,
      })

      if (!response.ok) {
        console.error(`API call failed: ${response.status} ${response.statusText}`)
        throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`)
      }

      const data = await response.json()
      console.log(`API call successful for ${endpoint}:`, data)
      return data
    } catch (error) {
      console.error(`API call failed for ${endpoint}:`, error)
      
      // Use mock data as fallback in development when API fails
      if (import.meta.env.DEV) {
        console.warn(`API failed, using mock data for ${endpoint}`)
        try {
          return this.getMockData<T>(endpoint)
        } catch (mockError) {
          console.error(`Mock data also failed for ${endpoint}:`, mockError)
          throw error
        }
      }
      
      throw error
    }
  }

  private getMockData<T>(endpoint: string): T {
    // Return mock data based on endpoint
    if (endpoint.includes('/api/skalds')) {
      return {
        items: mockSkalds,
        total: mockSkalds.length
      } as T
    } else if (endpoint.includes('/api/tasks')) {
      return {
        items: mockTasks,
        total: mockTasks.length,
        page: 1,
        pageSize: 20
      } as T
    } else if (endpoint.includes('/api/system/dashboard/summary')) {
      return {
        totalSkalds: mockSkalds.length,
        onlineSkalds: mockSkalds.filter(s => s.status === 'online').length,
        totalTasks: mockTasks.length,
        runningTasks: mockTasks.filter(t => t.lifecycleStatus === 'Running').length,
        finishedTasks: mockTasks.filter(t => t.lifecycleStatus === 'Finished').length,
        failedTasks: mockTasks.filter(t => t.lifecycleStatus === 'Failed').length
      } as T
    }
    
    throw new Error(`No mock data available for ${endpoint}`)
  }

  // Skald endpoints
  async getSkalds(): Promise<GetSkaldsResponse> {
    return this.fetchApi<GetSkaldsResponse>('/api/skalds/')
  }

  async getSkald(id: string): Promise<Skald> {
    return this.fetchApi<Skald>(`/api/skalds/${id}`)
  }

  // Task endpoints
  async getTasks(params: GetTasksRequest & { id?: string }): Promise<GetTasksResponse> {
    const searchParams = new URLSearchParams({
      page: params.page.toString(),
      pageSize: params.pageSize.toString(),
    })

    if (params.lifecycleStatus) {
      searchParams.append('lifecycleStatus', params.lifecycleStatus)
    }
    if (params.className) {
      searchParams.append('className', params.className)
    }
    if (params.executor) {
      searchParams.append('executor', params.executor)
    }
    if (params.id) {
      searchParams.append('id', params.id)
    }
    
    return this.fetchApi<GetTasksResponse>(`/api/tasks/?${searchParams.toString()}`)
  }

  async getTaskClassNames(): Promise<string[]> {
    return this.fetchApi<string[]>('/api/tasks/classnames')
  }

  async getTask(id: string): Promise<Task> {
    return this.fetchApi<Task>(`/api/tasks/${id}`)
  }

  async updateTaskStatus(id: string, request: UpdateTaskStatusRequest): Promise<Task> {
    return this.fetchApi<Task>(`/api/tasks/${id}/status`, {
      method: 'PUT',
      body: JSON.stringify(request),
    })
  }

  async updateTaskAttachments(id: string, request: UpdateTaskAttachmentsRequest): Promise<Task> {
    return this.fetchApi<Task>(`/api/tasks/${id}/attachments`, {
      method: 'PUT',
      body: JSON.stringify(request),
    })
  }

  // Dashboard summary
  async getDashboardSummary(): Promise<DashboardSummary> {
    return this.fetchApi<DashboardSummary>('/api/system/dashboard/summary')
  }
}

export const apiClient = new ApiClient()