import React, { useState } from 'react'
import { Task, UpdateTaskAttachmentsRequest, TaskLifecycleStatus } from '../../types'
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

  // Handle attachment field change
  const handleAttachmentChange = (key: string, value: any) => {
    setAttachments(prev => ({ ...prev, [key]: value }))
  }

  // Add new attachment key
  const handleAddAttachment = () => {
    setAttachments(prev => ({ ...prev, '': '' }))
  }

  // Remove attachment key
  const handleRemoveAttachment = (key: string) => {
    const { [key]: _, ...rest } = attachments
    setAttachments(rest)
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
  const handleChangeStatus = async (newStatus: 'Created' | 'Canceled') => {
    setLoading(true)
    setError(null)
    setSuccess(null)
    try {
      // Note: backend may expect "Canceled" not "Canceled"
      const updated = await apiClient.updateTaskStatus(task.id, { lifecycleStatus: newStatus })
      setStatus(updated.lifecycleStatus)
      setSuccess(`Status changed to ${updated.lifecycleStatus}`)
      if (onUpdated) onUpdated(updated)
    } catch (e: any) {
      setError(e.message || 'Failed to update status')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-30">
      <div className="bg-white rounded-lg shadow-lg p-6 w-full max-w-lg relative">
        <button
          className="absolute top-2 right-2 text-gray-400 hover:text-gray-700"
          onClick={onClose}
        >
          ×
        </button>
        <h2 className="text-xl font-bold mb-2">Task Details</h2>
        <div className="mb-2">
          <div className="text-xs text-gray-500 mb-1">Task ID: <span className="font-mono">{task.id}</span></div>
          <div className="text-xs text-gray-500 mb-1">Type: {task.className}</div>
          <div className="text-xs text-gray-500 mb-1">Executor: {task.executor || 'Unassigned'}</div>
          <div className="text-xs text-gray-500 mb-1">Status: <span className="font-mono">{status}</span></div>
        </div>
        <div className="mb-4">
          <h3 className="font-semibold text-sm mb-1">Attachments</h3>
          <div className="space-y-2">
            {Object.entries(attachments).map(([key, value], idx) => (
              <div key={key + idx} className="flex items-center space-x-2">
                <input
                  type="text"
                  className="w-1/3 rounded border px-2 py-1 text-xs"
                  value={key}
                  onChange={e => {
                    const newKey = e.target.value
                    setAttachments(prev => {
                      const { [key]: oldValue, ...rest } = prev
                      return { ...rest, [newKey]: value }
                    })
                  }}
                  placeholder="Key"
                />
                <input
                  type="text"
                  className="w-2/3 rounded border px-2 py-1 text-xs"
                  value={value}
                  onChange={e => handleAttachmentChange(key, e.target.value)}
                  placeholder="Value"
                />
                <button
                  className="btn btn-xs btn-danger"
                  onClick={() => handleRemoveAttachment(key)}
                  title="Remove"
                >×</button>
              </div>
            ))}
            <button
              className="btn btn-xs btn-secondary"
              onClick={handleAddAttachment}
            >+ Add Attachment</button>
          </div>
          <button
            className="btn btn-sm btn-primary mt-2"
            onClick={handleUpdateAttachments}
            disabled={loading}
          >
            {loading ? 'Updating...' : 'Update Attachments'}
          </button>
        </div>
        <div className="mb-4">
          <h3 className="font-semibold text-sm mb-1">Change Status</h3>
          <div className="flex space-x-2">
            <button
              className="btn btn-xs btn-warning"
              onClick={() => handleChangeStatus('Canceled')}
              disabled={loading || status === 'Canceled'}
            >Set Canceled</button>
            <button
              className="btn btn-xs btn-success"
              onClick={() => handleChangeStatus('Created')}
              disabled={loading || status === 'Created'}
            >Set Created</button>
          </div>
        </div>
        {error && <div className="text-xs text-red-600 mb-2">{error}</div>}
        {success && <div className="text-xs text-green-600 mb-2">{success}</div>}
        <button
          className="btn btn-sm btn-secondary mt-2"
          onClick={onClose}
        >
          Close
        </button>
      </div>
    </div>
  )
}