import { BrowserRouter } from 'react-router-dom'
import AppRouter from '@/router'
import { useEffect } from 'react'
import { systemApi } from '@/api'
import { useAppStore } from '@/store/useStore'

function App() {
  const { setSystemInfo, setPlatformList, token } = useAppStore()

  useEffect(() => {
    // 未登录时跳过预加载（/platforms 等接口需要JWT，避免无谓的401提示）
    if (!token) return

    // 加载系统信息
    systemApi.getInfo().then((res: any) => {
      setSystemInfo(res.data)
    }).catch(() => {})

    systemApi.getPlatforms().then((res: any) => {
      setPlatformList(res.data)
    }).catch(() => {})
  }, [token])

  return (
    <BrowserRouter basename="/geo">
      <AppRouter />
    </BrowserRouter>
  )
}

export default App
