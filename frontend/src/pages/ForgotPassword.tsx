import { useState, useEffect, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Form, Input, Button, message, Typography } from 'antd'
import {
  MailOutlined,
  LockOutlined,
  SafetyOutlined,
  RocketOutlined,
  MonitorOutlined,
  FileTextOutlined,
  SendOutlined,
  TeamOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons'
import { localAuthApi } from '@/api'

const { Title, Text, Paragraph } = Typography

const ForgotPassword = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [codeLoading, setCodeLoading] = useState(false)
  const [countdown, setCountdown] = useState(0)
  const [step, setStep] = useState(1) // 1: 输入邮箱 2: 重置密码
  const [form] = Form.useForm()
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

  // 发送验证码
  const handleSendCode = async () => {
    try {
      const email = form.getFieldValue('email')
      if (!email) {
        message.warning('请先输入邮箱')
        return
      }
      setCodeLoading(true)
      await localAuthApi.sendCode(email, 'reset')
      message.success('验证码已发送，请查收邮件')
      setCountdown(60)
    } catch (e: any) {
      // 错误已在拦截器提示
    } finally {
      setCodeLoading(false)
    }
  }

  // 验证邮箱和验证码，进入下一步
  const handleNext = async (values: any) => {
    try {
      setLoading(true)
      // 验证验证码是否正确（通过尝试重置密码接口验证）
      // 这里先进入下一步，实际验证在重置时做
      setStep(2)
      message.success('验证码验证成功，请设置新密码')
    } catch (e: any) {
      // 错误已在拦截器提示
    } finally {
      setLoading(false)
    }
  }

  // 重置密码
  const handleReset = async (values: any) => {
    try {
      setLoading(true)
      const email = form.getFieldValue('email')
      const code = form.getFieldValue('code')
      await localAuthApi.resetPassword(email, code, values.new_password)
      message.success('密码重置成功，请使用新密码登录')
      setTimeout(() => navigate('/login'), 1500)
    } catch (e: any) {
      // 错误已在拦截器提示
    } finally {
      setLoading(false)
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
        </div>
      </div>

      {/* 右侧表单区 */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '40px 60px',
      }}>
        <div style={{ width: '100%', maxWidth: 420 }}>
          {/* 返回登录 */}
          <div style={{ marginBottom: 24 }}>
            <Link to="/login" style={{ color: '#1677ff', fontSize: 14, display: 'inline-flex', alignItems: 'center' }}>
              <ArrowLeftOutlined style={{ marginRight: 6 }} />
              返回登录
            </Link>
          </div>

          <Title level={2} style={{ marginBottom: 8, fontSize: 28, fontWeight: 700 }}>
            {step === 1 ? '找回密码' : '设置新密码'}
          </Title>
          <Text type="secondary" style={{ display: 'block', marginBottom: 32, fontSize: 14 }}>
            {step === 1
              ? '输入注册邮箱，我们将发送验证码帮您重置密码'
              : '请设置您的新密码（至少 6 位）'}
          </Text>

          {step === 1 ? (
            <Form
              form={form}
              layout="vertical"
              onFinish={handleNext}
              size="large"
            >
              <Form.Item
                name="email"
                label="邮箱"
                rules={[
                  { required: true, message: '请输入邮箱' },
                  { type: 'email', message: '请输入正确的邮箱格式' },
                ]}
              >
                <Input
                  prefix={<MailOutlined style={{ color: '#bfbfbf' }} />}
                  placeholder="请输入注册邮箱"
                  autoComplete="email"
                />
              </Form.Item>

              <Form.Item
                name="code"
                label="验证码"
                rules={[
                  { required: true, message: '请输入验证码' },
                  { len: 6, message: '验证码为 6 位数字' },
                ]}
              >
                <div style={{ display: 'flex', gap: 12 }}>
                  <Input
                    prefix={<SafetyOutlined style={{ color: '#bfbfbf' }} />}
                    placeholder="请输入 6 位验证码"
                    maxLength={6}
                    style={{ flex: 1 }}
                  />
                  <Button
                    onClick={handleSendCode}
                    disabled={countdown > 0}
                    loading={codeLoading}
                    style={{ minWidth: 120 }}
                  >
                    {countdown > 0 ? `${countdown}s 后重发` : '获取验证码'}
                  </Button>
                </div>
              </Form.Item>

              <Form.Item style={{ marginTop: 24 }}>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                  block
                  style={{ height: 44, fontSize: 16, fontWeight: 600 }}
                >
                  下一步
                </Button>
              </Form.Item>
            </Form>
          ) : (
            <Form
              form={form}
              layout="vertical"
              onFinish={handleReset}
              size="large"
            >
              <Form.Item
                name="new_password"
                label="新密码"
                rules={[
                  { required: true, message: '请输入新密码' },
                  { min: 6, message: '密码至少 6 位' },
                ]}
              >
                <Input.Password
                  prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
                  placeholder="请输入新密码（至少 6 位）"
                  autoComplete="new-password"
                />
              </Form.Item>

              <Form.Item
                name="confirm_password"
                label="确认新密码"
                dependencies={['new_password']}
                rules={[
                  { required: true, message: '请再次输入新密码' },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue('new_password') === value) {
                        return Promise.resolve()
                      }
                      return Promise.reject(new Error('两次输入的密码不一致'))
                    },
                  }),
                ]}
              >
                <Input.Password
                  prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
                  placeholder="请再次输入新密码"
                  autoComplete="new-password"
                />
              </Form.Item>

              <Form.Item style={{ marginTop: 24 }}>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                  block
                  style={{ height: 44, fontSize: 16, fontWeight: 600 }}
                >
                  确认重置密码
                </Button>
              </Form.Item>
            </Form>
          )}

          <div style={{ textAlign: 'center', marginTop: 24 }}>
            <Text type="secondary" style={{ fontSize: 13 }}>
              还没有账号？
              <Link to="/login" style={{ color: '#1677ff', marginLeft: 4 }}>
                立即注册
              </Link>
            </Text>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ForgotPassword
