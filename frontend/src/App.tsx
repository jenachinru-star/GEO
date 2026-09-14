import { BrowserRouter } from 'react-router-dom'
import AppRouter from '@/router'
import { useEffect } from 'react'
import { systemApi } from '@/api'
import { useAppStore } from '@/store/useStore'

function App() {
  const { setSystemInfo, setPlatformList } = useAppStore()

  useEffect(() => {
    // 加载系统信息
    systemApi.getInfo().then((res: any) => {
      setSystemInfo(res.data)
    }).catch(() => {})

    systemApi.getPlatforms().then((res: any) => {
      setPlatformList(res.data)
    }).catch(() => {})
  }, [])

  return (
    <BrowserRouter basename="/geo">
      <AppRouter />
    </BrowserRouter>
  )
}

export default App
