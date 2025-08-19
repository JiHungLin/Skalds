import { useState, useCallback } from 'react'
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

  // JSON text editor for attachments
  const [attachmentsText, setAttachmentsText] = useState(() =>
    JSON.stringify(attachments, null, 2)
  )
  const [jsonError, setJsonError] = useState<string | null>(null)

  const handleAttachmentsTextChange = useCallback((text: string) => {
    setAttachmentsText(text)
    try {
      const parsed = JSON.parse(text)
      setAttachments(parsed)
      setJsonError(null)
    } catch (e) {
      setJsonError('Invalid JSON format')
    }
  }, [])

  // Update text when attachments change from outside
  const handleAttachmentsChange = useCallback((newAttachments: Record<string, any>) => {
    setAttachments(newAttachments)
    setAttachmentsText(JSON.stringify(newAttachments, null, 2))
    setJsonError(null)
  }, [])

  // Update attachments API
  const handleUpdateAttachments = async () => {
    setLoading(true)
    setError(null)
    setSuccess(null)
    
    try {
      const updated = await apiClient.updateTaskAttachments(task.id, { attachments })
      updated.attachments = attachments
      const updatedTask = {
        ...task,
        attachments: updated.attachments,
      };
      setSuccess('Attachments updated successfully')
      if (onUpdated) onUpdated(updatedTask)
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
            <div className="space-y-2">
              <textarea
                className="w-full h-48 p-3 border rounded-md font-mono text-xs resize-y"
                value={attachmentsText}
                onChange={(e) => handleAttachmentsTextChange(e.target.value)}
                placeholder="Enter JSON data for attachments..."
                spellCheck={false}
              />
              {jsonError && (
                <div className="text-xs text-red-600 bg-red-50 p-2 rounded">
                  {jsonError}
                </div>
              )}
              <div className="flex space-x-2">
                <button
                  className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded border"
                  onClick={() => {
                    try {
                      const formatted = JSON.stringify(JSON.parse(attachmentsText), null, 2)
                      setAttachmentsText(formatted)
                    } catch (e) {
                      // Ignore formatting errors
                    }
                  }}
                  type="button"
                >
                  Format JSON
                </button>
                <button
                  className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded border"
                  onClick={() => handleAttachmentsChange({})}
                  type="button"
                >
                  Clear
                </button>
              </div>
            </div>
            <button
              className="mt-3 px-4 py-1.5 rounded bg-primary-500 text-white text-sm font-medium shadow hover:bg-primary-600 transition"
              onClick={handleUpdateAttachments}
              disabled={loading || !!jsonError}
              type="button"
            >
              {loading ? 'Updating...' : 'Update Attachments'}
            </button>
          </div>
          {task.mode === 'Passive' && (
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
          )}
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