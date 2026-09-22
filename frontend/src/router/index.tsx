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
const Login = lazy(() => import('@/pages/Login'))
const ForgotPassword = lazy(() => import('@/pages/ForgotPassword'))
const Profile = lazy(() => import('@/pages/Profile'))
const Semantic = lazy(() => import('@/pages/Semantic'))
const TaskCenter = lazy(() => import('@/pages/TaskCenter'))
const Distribution = lazy(() => import('@/pages/Distribution'))
const AssetHub = lazy(() => import('@/pages/AssetHub'))
const AssetDetail = lazy(() => import('@/pages/AssetDetail'))
const PublishedList = lazy(() => import('@/pages/PublishedList'))
const PublishAccounts = lazy(() => import('@/pages/PublishAccounts'))
const UsageDashboard = lazy(() => import('@/pages/UsageDashboard'))
const UsageGovernance = lazy(() => import('@/pages/UsageGovernance'))
const AccountSettings = lazy(() => import('@/pages/AccountSettings'))

const RequireAuth = ({ children }: { children: React.ReactNode }) => {
  const { token } = useAppStore()
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

const AppRouter = () => {
  return (
    <Suspense fallback={<div style={{ padding: 40, textAlign: 'center' }}>加载中...</div>}>
      <Routes>
        <Route path="/sso" element={<SSOCallback />} />
        <Route path="/login" element={<Login />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<RequireAuth><Dashboard /></RequireAuth>} />
          <Route path="monitor" element={<RequireAuth><Monitor /></RequireAuth>} />
          <Route path="data" element={<RequireAuth><DataCenter /></RequireAuth>} />
          <Route path="content" element={<RequireAuth><ContentHub /></RequireAuth>} />
          <Route path="distribution" element={<RequireAuth><Distribution /></RequireAuth>} />
          <Route path="create" element={<Navigate to="/content" replace />} />
          <Route path="knowledge" element={<RequireAuth><Knowledge /></RequireAuth>} />
          <Route path="competitor" element={<RequireAuth><Competitor /></RequireAuth>} />
          <Route path="rag" element={<RequireAuth><RAGChat /></RequireAuth>} />
          <Route path="settings" element={<RequireAuth><Settings /></RequireAuth>} />
          <Route path="profile" element={<RequireAuth><Profile /></RequireAuth>} />
          <Route path="semantic" element={<RequireAuth><Semantic /></RequireAuth>} />
          <Route path="tasks" element={<RequireAuth><TaskCenter /></RequireAuth>} />
          <Route path="asset" element={<RequireAuth><AssetHub /></RequireAuth>} />
          <Route path="asset/:id" element={<RequireAuth><AssetDetail /></RequireAuth>} />
          <Route path="publish-accounts" element={<RequireAuth><PublishAccounts /></RequireAuth>} />
          <Route path="published" element={<RequireAuth><PublishedList /></RequireAuth>} />
          <Route path="usage" element={<RequireAuth><UsageDashboard /></RequireAuth>} />
          <Route path="usage-governance" element={<RequireAuth><UsageGovernance /></RequireAuth>} />
          <Route path="account" element={<RequireAuth><AccountSettings /></RequireAuth>} />
        </Route>
      </Routes>
    </Suspense>
  )
}

export default AppRouter

