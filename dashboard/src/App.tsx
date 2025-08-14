import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout/Layout'
import Dashboard from './features/dashboard/Dashboard'
import SkaldsPage from './features/skalds/SkaldsPage'
import TasksPage from './features/tasks/TasksPage'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/skalds" element={<SkaldsPage />} />
        <Route path="/tasks" element={<TasksPage />} />
      </Routes>
    </Layout>
  )
}

export default App