import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from '@/components/Layout'
import { useAppStore } from '@/store/useStore'

const Dashboard = lazy(() => import('@/pages/Dashboard'))
const Monitor = lazy(() => import('@/pages/Monitor'))
const DataCenter = lazy(() => import('@/pages/DataCenter'))
const ContentHub = lazy(() => import('@/pages/ContentHub'))
const Knowledge = lazy(() => import('@/pages/Knowledge'))
const Competitor = lazy(() => import('@/pages/Competitor'))
const RAGChat = lazy(() => import('@/pages/RAGChat'))
const Settings = lazy(() => import('@/pages/Settings'))
const SSOCallback = lazy(() => import('@/pages/SSOCallback'))
const Profile = lazy(() => import('@/pages/Profile'))
const Semantic = lazy(() => import('@/pages/Semantic'))
const TaskCenter = lazy(() => import('@/pages/TaskCenter'))

const RequireAuth = ({ children }: { children: React.ReactNode }) => {
  const { token } = useAppStore()
  if (!token) return <Navigate to="/sso" replace />
  return <>{children}</>
}

const AppRouter = () => {
  return (
    <Suspense fallback={<div style={{ padding: 40, textAlign: 'center' }}>加载中...</div>}>
      <Routes>
        <Route path="/sso" element={<SSOCallback />} />
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<RequireAuth><Dashboard /></RequireAuth>} />
          <Route path="monitor" element={<RequireAuth><Monitor /></RequireAuth>} />
          <Route path="data" element={<RequireAuth><DataCenter /></RequireAuth>} />
          <Route path="content" element={<RequireAuth><ContentHub /></RequireAuth>} />
          <Route path="create" element={<Navigate to="/content" replace />} />
          <Route path="knowledge" element={<RequireAuth><Knowledge /></RequireAuth>} />
          <Route path="competitor" element={<RequireAuth><Competitor /></RequireAuth>} />
          <Route path="rag" element={<RequireAuth><RAGChat /></RequireAuth>} />
          <Route path="settings" element={<RequireAuth><Settings /></RequireAuth>} />
          <Route path="profile" element={<RequireAuth><Profile /></RequireAuth>} />
          <Route path="semantic" element={<RequireAuth><Semantic /></RequireAuth>} />
          <Route path="tasks" element={<RequireAuth><TaskCenter /></RequireAuth>} />
        </Route>
      </Routes>
    </Suspense>
  )
}

export default AppRouter
