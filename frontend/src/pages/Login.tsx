import { useState, useEffect, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Form, Input, Button, Tabs, message, Typography } from 'antd'
import {
  MailOutlined,
  LockOutlined,
  SafetyOutlined,
  RocketOutlined,
  MonitorOutlined,
  FileTextOutlined,
  SendOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import { localAuthApi, authApi } from '@/api'
import { useAppStore } from '@/store/useStore'

const { Title, Text, Paragraph } = Typography

const Login = () => {
  const navigate = useNavigate()
  const { setAuth } = useAppStore()
  const [activeTab, setActiveTab] = useState('login')
  const [loading, setLoading] = useState(false)
  const [codeLoading, setCodeLoading] = useState(false)
  const [countdown, setCountdown] = useState(0)
  const [emailCheck, setEmailCheck] = useState<{exists: boolean; loading: boolean} | null>(null)
  const [loginForm] = Form.useForm()
  const [registerForm] = Form.useForm()
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // 倒计时
  useEffect(() => {
    if (countdown > 0) {
      timerRef.current = setTimeout(() => setCountdown(countdown - 1), 1000)
    }
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [countdown])

  // 检查邮箱是否已注册（失焦时触发）
  const handleCheckEmail = async (email: string) => {
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setEmailCheck(null)
      return
    }
    try {
      setEmailCheck({ exists: false, loading: true })
      const res: any = await localAuthApi.checkEmail(email)
      setEmailCheck({ exists: res.data.exists, loading: false })
    } catch {
      setEmailCheck(null)
    }
  }

  // 发送验证码
  const handleSendCode = async () => {
    try {
      const email = registerForm.getFieldValue('email')
      if (!email) {
        message.warning('请先输入邮箱')
        return
      }
      setCodeLoading(true)
      await localAuthApi.sendCode(email, 'register')
      message.success('验证码已发送，请查收邮件')
      setCountdown(60)
    } catch (e: any) {
      // 错误已在拦截器提示
    } finally {
      setCodeLoading(false)
    }
  }

  // 登录
  const handleLogin = async (values: any) => {
    try {
      setLoading(true)
      const res: any = await localAuthApi.login(values.email, values.password)
      const { token, user } = res.data
      setAuth(token, user)
      message.success('登录成功')
      navigate('/dashboard')
    } catch (e: any) {
      // 错误已在拦截器提示
    } finally {
      setLoading(false)
    }
  }

  // 注册
  const handleRegister = async (values: any) => {
    try {
      setLoading(true)
      const res: any = await localAuthApi.register(values.email, values.code, values.password)
      const { token, user } = res.data
      setAuth(token, user)
      message.success('注册成功，已自动登录')
      navigate('/dashboard')
    } catch (e: any) {
      // 错误已在拦截器提示
    } finally {
      setLoading(false)
    }
  }

  // 企业登录（IAM）
  const handleIamLogin = async () => {
    try {
      const res: any = await authApi.getIamUrl()
      window.location.href = res.data.auth_url
    } catch (e: any) {
      message.error('获取企业登录地址失败')
    }
  }

  const features = [
    { icon: <RocketOutlined />, title: 'AI 语义库自动延伸', desc: '基于 LLM 自动生成患者提问变体' },
    { icon: <MonitorOutlined />, title: 'GEO/AEO 效果监测', desc: '实时追踪 AI 搜索平台排名变化' },
    { icon: <FileTextOutlined />, title: '智能文章一键生成', desc: 'AI 辅助生成高质量医疗科普文章' },
    { icon: <SendOutlined />, title: '多平台内容分发', desc: '一键分发到主流医疗内容平台' },
  ]

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      background: 'linear-gradient(135deg, #e6f4ff 0%, #f0f5ff 50%, #f9f0ff 100%)',
    }}>
      {/* 左侧品牌展示区 */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        padding: '60px 80px',
        background: 'linear-gradient(135deg, #1677ff 0%, #4096ff 50%, #69b1ff 100%)',
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* 装饰圆形 */}
        <div style={{
          position: 'absolute',
          width: 400,
          height: 400,
          borderRadius: '50%',
          background: 'rgba(255,255,255,0.08)',
          top: -100,
          right: -100,
        }} />
        <div style={{
          position: 'absolute',
          width: 300,
          height: 300,
          borderRadius: '50%',
          background: 'rgba(255,255,255,0.06)',
          bottom: -80,
          left: -80,
        }} />

        <div style={{ position: 'relative', zIndex: 1 }}>
          {/* Logo */}
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 40 }}>
            <div style={{
              width: 48,
              height: 48,
              borderRadius: 12,
              background: 'rgba(255,255,255,0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginRight: 12,
              fontSize: 24,
              color: '#fff',
            }}>
              <TeamOutlined />
            </div>
            <div>
              <div style={{ fontSize: 24, fontWeight: 700, color: '#fff' }}>GEO 创作者中心</div>
              <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.7)' }}>Generative Engine Optimization</div>
            </div>
          </div>

          {/* 主标题 */}
          <Title level={1} style={{ color: '#fff', marginBottom: 16, fontSize: 42, fontWeight: 700 }}>
            医生个人品牌<br />AI 引擎
          </Title>
          <Paragraph style={{ color: 'rgba(255,255,255,0.85)', fontSize: 16, marginBottom: 48, lineHeight: 1.8 }}>
            面向医生的 AI 搜索引擎优化平台，<br />
            帮助您在 AI 搜索时代建立专业影响力。
          </Paragraph>

          {/* 功能亮点 */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
            {features.map((f, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'flex-start' }}>
                <div style={{
                  width: 40,
                  height: 40,
                  borderRadius: 10,
                  background: 'rgba(255,255,255,0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginRight: 12,
                  fontSize: 18,
                  color: '#fff',
                  flexShrink: 0,
                }}>
                  {f.icon}
                </div>
                <div>
                  <div style={{ color: '#fff', fontSize: 15, fontWeight: 600, marginBottom: 4 }}>{f.title}</div>
                  <div style={{ color: 'rgba(255,255,255,0.7)', fontSize: 13 }}>{f.desc}</div>
                </div>
              </div>
            ))}
          </div>

          {/* 底部数据 */}
          <div style={{ marginTop: 60, display: 'flex', gap: 48 }}>
            <div>
              <div style={{ color: '#fff', fontSize: 28, fontWeight: 700 }}>500+</div>
              <div style={{ color: 'rgba(255,255,255,0.7)', fontSize: 13 }}>服务医生</div>
            </div>
            <div>
              <div style={{ color: '#fff', fontSize: 28, fontWeight: 700 }}>10000+</div>
              <div style={{ color: 'rgba(255,255,255,0.7)', fontSize: 13 }}>生成文章</div>
            </div>
            <div>
              <div style={{ color: '#fff', fontSize: 28, fontWeight: 700 }}>98%</div>
              <div style={{ color: 'rgba(255,255,255,0.7)', fontSize: 13 }}>用户满意度</div>
            </div>
          </div>
        </div>
      </div>

      {/* 右侧登录表单区 */}
      <div style={{
        width: 520,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 40,
      }}>
        <div style={{
          width: '100%',
          maxWidth: 420,
          background: '#fff',
          borderRadius: 16,
          padding: '40px 36px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
        }}>
          <Title level={3} style={{ textAlign: 'center', marginBottom: 8, fontWeight: 700 }}>
            {activeTab === 'login' ? '欢迎回来' : '创建账号'}
          </Title>
          <Text type="secondary" style={{ display: 'block', textAlign: 'center', marginBottom: 32 }}>
            {activeTab === 'login' ? '登录您的账号，继续创作之旅' : '注册账号，开启 AI 优化之旅'}
          </Text>

          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            centered
            items={[
              {
                key: 'login',
                label: '登录',
                children: (
                  <Form
                    form={loginForm}
                    layout="vertical"
                    onFinish={handleLogin}
                    size="large"
                  >
                    <Form.Item
                      name="email"
                      rules={[
                        { required: true, message: '请输入邮箱' },
                        { type: 'email', message: '请输入正确的邮箱地址' },
                      ]}
                      extra={
                        emailCheck?.exists ? (
                          <span style={{ color: '#ff4d4f', fontSize: 12 }}>
                            该邮箱已注册，
                            <a onClick={() => setActiveTab('login')} style={{ cursor: 'pointer' }}>
                              去登录
                            </a>
                          </span>
                        ) : emailCheck && !emailCheck.exists && !emailCheck.loading ? (
                          <span style={{ color: '#52c41a', fontSize: 12 }}>该邮箱可注册</span>
                        ) : null
                      }
                      validateStatus={emailCheck?.exists ? 'error' : undefined}
                    >
                      <Input
                        prefix={<MailOutlined style={{ color: '#bfbfbf' }} />}
                        placeholder="邮箱地址"
                        autoComplete="email"
                        onBlur={(e) => handleCheckEmail(e.target.value)}
                      />
                    </Form.Item>

                    <Form.Item
                      name="password"
                      rules={[
                        { required: true, message: '请输入密码' },
                        { min: 6, message: '密码至少 6 位' },
                        { max: 64, message: '密码最多 64 位' },
                      ]}
                    >
                      <Input.Password
                        prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
                        placeholder="密码"
                        maxLength={64}
                        autoComplete="current-password"
                      />
                    </Form.Item>

                    <div style={{ textAlign: 'right', marginBottom: 16 }}>
                      <Link to="/forgot-password" style={{ fontSize: 13, color: '#1677ff' }}>
                        忘记密码？
                      </Link>
                    </div>

                    <Form.Item>
                      <Button
                        type="primary"
                        htmlType="submit"
                        block
                        loading={loading}
                        style={{ height: 44, fontSize: 16, fontWeight: 600 }}
                      >
                        登 录
                      </Button>
                    </Form.Item>
                  </Form>
                ),
              },
              {
                key: 'register',
                label: '注册',
                children: (
                  <Form
                    form={registerForm}
                    layout="vertical"
                    onFinish={handleRegister}
                    size="large"
                  >
                    <Form.Item
                      name="email"
                      rules={[
                        { required: true, message: '请输入邮箱' },
                        { type: 'email', message: '请输入正确的邮箱地址' },
                      ]}
                      extra={
                        emailCheck?.exists ? (
                          <span style={{ color: '#ff4d4f', fontSize: 12 }}>
                            该邮箱已注册，
                            <a onClick={() => setActiveTab('login')} style={{ cursor: 'pointer' }}>
                              去登录
                            </a>
                          </span>
                        ) : emailCheck && !emailCheck.exists && !emailCheck.loading ? (
                          <span style={{ color: '#52c41a', fontSize: 12 }}>该邮箱可注册</span>
                        ) : null
                      }
                      validateStatus={emailCheck?.exists ? 'error' : undefined}
                    >
                      <Input
                        prefix={<MailOutlined style={{ color: '#bfbfbf' }} />}
                        placeholder="邮箱地址"
                        autoComplete="email"
                        onBlur={(e) => handleCheckEmail(e.target.value)}
                      />
                    </Form.Item>

                    <Form.Item
                      name="code"
                      rules={[
                        { required: true, message: '请输入验证码' },
                        { len: 6, message: '验证码为 6 位数字' },
                      ]}
                    >
                      <Input
                        prefix={<SafetyOutlined style={{ color: '#bfbfbf' }} />}
                        placeholder="6 位验证码"
                        maxLength={6}
                        suffix={
                          <Button
                            type="link"
                            size="small"
                            onClick={handleSendCode}
                            loading={codeLoading}
                            disabled={countdown > 0}
                            style={{ padding: 0, fontSize: 13 }}
                          >
                            {countdown > 0 ? `${countdown}s 后重发` : '获取验证码'}
                          </Button>
                        }
                      />
                    </Form.Item>

                    <Form.Item
                      name="password"
                      rules={[
                        { required: true, message: '请输入密码' },
                        { min: 6, message: '密码至少 6 位' },
                        { max: 64, message: '密码最多 64 位' },
                      ]}
                    >
                      <Input.Password
                        prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
                        placeholder="设置密码（至少 6 位）"
                        maxLength={64}
                        autoComplete="new-password"
                      />
                    </Form.Item>

                    <Form.Item
                      name="confirmPassword"
                      dependencies={['password']}
                      rules={[
                        { required: true, message: '请确认密码' },
                        ({ getFieldValue }) => ({
                          validator(_, value) {
                            if (!value || getFieldValue('password') === value) {
                              return Promise.resolve()
                            }
                            return Promise.reject(new Error('两次输入的密码不一致'))
                          },
                        }),
                      ]}
                    >
                      <Input.Password
                        prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
                        placeholder="确认密码"
                        autoComplete="new-password"
                      />
                    </Form.Item>

                    <Form.Item>
                      <Button
                        type="primary"
                        htmlType="submit"
                        block
                        loading={loading}
                        style={{ height: 44, fontSize: 16, fontWeight: 600 }}
                      >
                        注 册
                      </Button>
                    </Form.Item>

                    <div style={{ textAlign: 'center', fontSize: 13, color: '#999' }}>
                      注册即表示同意
                      <a style={{ margin: '0 4px' }}>《服务条款》</a>
                      和
                      <a style={{ margin: '0 4px' }}>《隐私政策》</a>
                    </div>
                  </Form>
                ),
              },
            ]}
          />

          {/* 企业登录入口 */}
          <div style={{ marginTop: 24, textAlign: 'center' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              marginBottom: 16,
            }}>
              <div style={{ flex: 1, height: 1, background: '#f0f0f0' }} />
              <span style={{ padding: '0 16px', fontSize: 12, color: '#bbb' }}>企业员工</span>
              <div style={{ flex: 1, height: 1, background: '#f0f0f0' }} />
            </div>
            <Button
              block
              icon={<TeamOutlined />}
              onClick={handleIamLogin}
              style={{ height: 40, borderColor: '#d9d9d9', color: '#666' }}
            >
              企业账号登录（IAM）
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Login
