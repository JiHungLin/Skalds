import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout/Layout'
import Dashboard from './features/dashboard/Dashboard'
import SkaldsPage from './features/skalds/SkaldsPage'
import TasksPage from './features/tasks/TasksPage'
import { SSEProvider } from './contexts/SSEContext'

function App() {
  return (
    <SSEProvider>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/skalds" element={<SkaldsPage />} />
          <Route path="/tasks" element={<TasksPage />} />
        </Routes>
      </Layout>
    </SSEProvider>
  )
}

export default App