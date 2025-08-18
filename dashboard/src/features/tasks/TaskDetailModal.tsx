import { useState } from 'react'
import { Task, TaskLifecycleStatus } from '../../types'
import { apiClient } from '../../lib/api/client'

interface TaskDetailModalProps {
  task: Task
  onClose: () => void
  onUpdated?: (task: Task) => void
}

export default function TaskDetailModal({ task, onClose, onUpdated }: TaskDetailModalProps) {
  const [attachments, setAttachments] = useState<Record<string, any>>({ ...task.attachments })
  const [status, setStatus] = useState<TaskLifecycleStatus>(task.lifecycleStatus)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Recursive editor for nested attachments
  function AttachmentEditor({
    value,
    onChange,
    path = []
  }: {
    value: any
    onChange: (val: any) => void
    path?: (string | number)[]
  }) {
    // Add new key for object
    const handleAddField = () => {
      if (Array.isArray(value)) {
        onChange([...value, ''])
      } else if (typeof value === 'object' && value !== null) {
        onChange({ ...value, '': '' })
      }
    }

    // Remove key for object/array
    const handleRemoveField = (key: string | number) => {
      if (Array.isArray(value)) {
        onChange(value.filter((_: any, idx: number) => idx !== key))
      } else if (typeof value === 'object' && value !== null) {
        const { [key]: _, ...rest } = value
        onChange(rest)
      }
    }

    // Change key for object
    const handleKeyChange = (oldKey: string, newKey: string) => {
      if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
        const { [oldKey]: val, ...rest } = value
        onChange({ ...rest, [newKey]: val })
      }
    }

    if (Array.isArray(value)) {
      return (
        <div className="ml-4 border-l-2 border-gray-200 pl-2 space-y-2">
          {value.map((item, idx) => (
            <div key={idx} className="flex items-start space-x-2">
              <AttachmentEditor
                value={item}
                onChange={v => onChange(value.map((it, i) => (i === idx ? v : it)))}
                path={[...path, idx]}
              />
              <button
                className="text-xs text-red-500 hover:text-red-700 px-1"
                onClick={() => handleRemoveField(idx)}
                title="Remove"
                type="button"
              >×</button>
            </div>
          ))}
          <button
            className="text-xs text-blue-600 hover:underline mt-1"
            onClick={handleAddField}
            type="button"
          >+ Add Item</button>
        </div>
      )
    } else if (typeof value === 'object' && value !== null) {
      return (
        <div className="ml-4 border-l-2 border-gray-200 pl-2 space-y-2">
          {Object.entries(value).map(([key, val], idx) => (
            <div key={key + idx} className="flex items-start space-x-2">
              <input
                type="text"
                className="w-1/4 rounded border px-2 py-1 text-xs"
                value={key}
                onChange={e => handleKeyChange(key, e.target.value)}
                placeholder="Key"
              />
              <AttachmentEditor
                value={val}
                onChange={v => onChange({ ...value, [key]: v })}
                path={[...path, key]}
              />
              <button
                className="text-xs text-red-500 hover:text-red-700 px-1"
                onClick={() => handleRemoveField(key)}
                title="Remove"
                type="button"
              >×</button>
            </div>
          ))}
          <button
            className="text-xs text-blue-600 hover:underline mt-1"
            onClick={handleAddField}
            type="button"
          >+ Add Field</button>
        </div>
      )
    } else {
      // Primitive value
      return (
        <input
          type="text"
          className="w-2/3 rounded border px-2 py-1 text-xs"
          value={value === null || value === undefined ? '' : String(value)}
          onChange={e => {
            let v: any = e.target.value
            // Try to parse as number or boolean
            if (v === 'true') v = true
            else if (v === 'false') v = false
            else if (!isNaN(Number(v)) && v.trim() !== '') v = Number(v)
            onChange(v)
          }}
          placeholder="Value"
        />
      )
    }
  }

  // Update attachments API
  const handleUpdateAttachments = async () => {
    setLoading(true)
    setError(null)
    setSuccess(null)
    try {
      const updated = await apiClient.updateTaskAttachments(task.id, { attachments })
      setSuccess('Attachments updated successfully')
      if (onUpdated) onUpdated(updated)
    } catch (e: any) {
      setError(e.message || 'Failed to update attachments')
    } finally {
      setLoading(false)
    }
  }

  // Change status API
  const handleChangeStatus = async (newStatus: 'Created' | 'Cancelled') => {
    setLoading(true)
    setError(null)
    setSuccess(null)
    try {
      // API returns: { success, message, data: { taskId, status } }
      // Accept any response type to avoid TS error from apiClient
      const response = await apiClient.updateTaskStatus(task.id, { lifecycleStatus: newStatus }) as any;

      // Merge updated status into the existing task object, cast status to TaskLifecycleStatus
      const updatedTask = {
        ...task,
        id: response.data.taskId,
        lifecycleStatus: response.data.status as TaskLifecycleStatus,
        updateDateTime: new Date().toISOString(),
      };

      setStatus(response.data.status as TaskLifecycleStatus);
      setSuccess(response.message || `Status changed to ${response.data.status}`);
      if (onUpdated) onUpdated(updatedTask);
    } catch (e: any) {
      setError(e.message || 'Failed to update status');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
      <div className="bg-white rounded-xl shadow-2xl p-0 w-full max-w-2xl relative flex flex-col" style={{ maxHeight: '90vh' }}>
        <button
          className="absolute top-3 right-3 text-gray-400 hover:text-gray-700 text-2xl"
          onClick={onClose}
          style={{ lineHeight: 1 }}
        >
          ×
        </button>
        <div className="px-8 pt-7 pb-2 border-b border-gray-100">
          <h2 className="text-2xl font-bold mb-1 text-gray-900">Task Details</h2>
          <div className="flex flex-wrap gap-x-8 gap-y-1 text-xs text-gray-500 mb-1">
            <div>Task ID: <span className="font-mono">{task.id}</span></div>
            <div>Type: {task.className}</div>
            <div>Executor: {task.executor || 'Unassigned'}</div>
            <div>Status: <span className="font-mono">{status}</span></div>
          </div>
        </div>
        <div className="overflow-y-auto px-8 py-4 flex-1" style={{ minHeight: 200 }}>
          <div className="mb-6">
            <h3 className="font-semibold text-sm mb-2">Attachments</h3>
            <AttachmentEditor
              value={attachments}
              onChange={setAttachments}
            />
            <button
              className="mt-3 px-4 py-1.5 rounded bg-primary-500 text-white text-sm font-medium shadow hover:bg-primary-600 transition"
              onClick={handleUpdateAttachments}
              disabled={loading}
              type="button"
            >
              {loading ? 'Updating...' : 'Update Attachments'}
            </button>
          </div>
          <div className="mb-4">
            <h3 className="font-semibold text-sm mb-2">Change Status</h3>
            <div className="flex space-x-2">
              <button
                className={`flex items-center gap-2 px-5 py-2 rounded-lg text-base font-semibold shadow transition
                  ${status === 'Cancelled' ? 'bg-yellow-200 text-yellow-600 cursor-not-allowed opacity-60' : 'bg-yellow-400 text-white hover:bg-yellow-500 scale-105 border-2 border-yellow-500'}
                `}
                onClick={() => handleChangeStatus('Cancelled')}
                disabled={loading || status === 'Cancelled'}
                type="button"
                title={status === 'Cancelled' ? 'Already Cancelled' : 'Set status to Cancelled'}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                Set Cancelled
              </button>
              <button
                className={`flex items-center gap-2 px-5 py-2 rounded-lg text-base font-semibold shadow transition
                  ${status === 'Created' ? 'bg-green-200 text-green-600 cursor-not-allowed opacity-60' : 'bg-green-500 text-white hover:bg-green-600 scale-105 border-2 border-green-600'}
                `}
                onClick={() => handleChangeStatus('Created')}
                disabled={loading || status === 'Created'}
                type="button"
                title={status === 'Created' ? 'Already Created' : 'Set status to Created'}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Set Created
              </button>
            </div>
          </div>
          {error && <div className="text-xs text-red-600 mb-2">{error}</div>}
          {success && <div className="text-xs text-green-600 mb-2">{success}</div>}
        </div>
        <div className="px-8 pb-6 pt-2 border-t border-gray-100 flex justify-end">
          <button
            className="px-4 py-1.5 rounded bg-gray-200 text-gray-700 text-sm font-medium shadow hover:bg-gray-300 transition"
            onClick={onClose}
            type="button"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}