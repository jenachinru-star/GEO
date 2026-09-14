import { useEffect, useState, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Spin, Result, Button } from 'antd'
import { authApi } from '@/api'
import { useAppStore } from '@/store/useStore'

const SSOCallback = () => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const setAuth = useAppStore((state) => state.setAuth)
  const [status, setStatus] = useState<'loading' | 'error' | 'success'>('loading')
  const [errorMsg, setErrorMsg] = useState('')
  const exchangedRef = useRef(false)

  useEffect(() => {
    // 防止 React StrictMode 双调用导致 ticket 重复使用（ticket是一次性的）
    if (exchangedRef.current) return
    exchangedRef.current = true

    const ticket = searchParams.get('ticket')
    const error = searchParams.get('error')

    if (error) {
      setStatus('error')
      setErrorMsg(decodeURIComponent(error))
      return
    }

    if (!ticket) {
      // 没有ticket说明是直接访问回调页，自动跳转到IAM登录页
      const redirectToLogin = async () => {
        try {
          const res: any = await authApi.getIamUrl()
          window.location.href = res.data.auth_url
        } catch (e) {
          setStatus('error')
          setErrorMsg('获取登录地址失败，请稍后重试')
        }
      }
      redirectToLogin()
      return
    }

    // 用ticket换取JWT
    const exchange = async () => {
      try {
        const res: any = await authApi.exchangeTicket(ticket)
        const token = res.data.token

        // 获取用户信息
        const userRes: any = await authApi.getUserinfo(token)
        const user = userRes.data

        // 存储登录态
        setAuth(token, user)
        setStatus('success')

        // 延迟跳转首页
        setTimeout(() => {
          navigate('/')
        }, 1000)
      } catch (e: any) {
        setStatus('error')
        setErrorMsg(e.message || '登录失败')
      }
    }

    exchange()
  }, [searchParams, navigate, setAuth])

  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#F8FAFC'
    }}>
      {status === 'loading' && (
        <div style={{ textAlign: 'center' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: '#64748B' }}>正在登录...</div>
        </div>
      )}
      {status === 'success' && (
        <Result
          status="success"
          title="登录成功"
          subTitle="正在跳转到系统首页..."
        />
      )}
      {status === 'error' && (
        <Result
          status="error"
          title="登录失败"
          subTitle={errorMsg}
          extra={
            <Button type="primary" onClick={() => navigate('/')}>
              返回首页
            </Button>
          }
        />
      )}
    </div>
  )
}

export default SSOCallback
