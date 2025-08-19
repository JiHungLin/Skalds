import { Component, ErrorInfo, ReactNode } from 'react'
import { XCircleIcon } from '@heroicons/react/24/outline'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="max-w-md w-full bg-white shadow-lg rounded-lg p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <XCircleIcon className="h-8 w-8 text-red-400" />
              </div>
              <div className="ml-3">
                <h3 className="text-lg font-medium text-red-800">
                  Something went wrong
                </h3>
                <div className="mt-2 text-sm text-red-700">
                  <p>An unexpected error occurred while rendering this page.</p>
                  {this.state.error && (
                    <p className="mt-2 font-mono text-xs bg-red-100 p-2 rounded">
                      {this.state.error.message}
                    </p>
                  )}
                </div>
                <div className="mt-4">
                  <button
                    onClick={() => window.location.reload()}
                    className="btn btn-sm btn-primary"
                  >
                    Reload Page
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary