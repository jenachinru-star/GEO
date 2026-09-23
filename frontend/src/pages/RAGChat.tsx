import { useState, useEffect, useRef } from 'react'
import {
  Row, Col, Card, Input, Button, Select, Tag, Space, Spin, message, Empty
} from 'antd'
import {
  SendOutlined, RobotOutlined, UserOutlined,
  BookOutlined, CopyOutlined
} from '@ant-design/icons'
import { ragApi } from '@/api'
import { PLATFORM_NAMES, useAppStore } from '@/store/useStore'

interface Message {
  role: 'user' | 'assistant'
  content: string
  platform?: string
  sources?: any[]
  success?: boolean
}

const RAGChat = () => {
  const [messages, setMessages] = useState<Message[]>([])
  const { user } = useAppStore()
  const isAdmin = user?.role === 'admin'
  const [input, setInput] = useState('')
  const [platform, setPlatform] = useState('glm')
  const [level, setLevel] = useState('public')
  const [loading, setLoading] = useState(false)
  const [platforms, setPlatforms] = useState<any[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    ragApi.getPlatforms().then((res: any) => {
      setPlatforms(res.data)
      if (res.data.length > 0) {
        setPlatform(res.data[0].code)
      }
    }).catch(() => {})
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // 普通用户自动降级 confidential 级别
  useEffect(() => {
    if (!isAdmin && level === 'confidential') {
      setLevel('public')
    }
  }, [isAdmin, level])

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage: Message = { role: 'user', content: input.trim() }
    const newMessages = [...messages, userMessage]
    setMessages(newMessages)
    setInput('')
    setLoading(true)

    try {
      // 构建历史对话（排除当前用户消息）
      const history = messages.map(m => ({
        role: m.role,
        content: m.content
      }))

      const res: any = await ragApi.query({
        query: userMessage.content,
        platform,
        level,
        history
      })
      const assistantMessage: Message = {
        role: 'assistant',
        content: res.data.answer,
        platform: res.data.platform,
        sources: res.data.sources,
        success: res.data.success
      }
      setMessages(prev => [...prev, assistantMessage])
    } catch (e: any) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `回答生成失败：${e.message || '未知错误'}`,
        success: false
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleClearChat = () => {
    setMessages([])
    message.success('对话已清空')
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const quickQuestions = [
    '公司的核心业务是什么？',
    '深圳层次智慧生物技术有限公司有哪些技术优势？',
    '公司的团队背景如何？',
    'AI药物研发服务包括哪些内容？'
  ]

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2>智能问答</h2>
            <div className="page-desc">基于公司知识库的智能问答，支持多轮对话和多平台对比</div>
          </div>
          <Button
            icon={<CopyOutlined />}
            onClick={handleClearChat}
            disabled={messages.length === 0}
          >
            清空对话
          </Button>
        </div>
      </div>

      <Row gutter={16}>
        {/* 主对话区 */}
        <Col xs={24} lg={16}>
          <div className="geo-card" style={{ height: 'calc(100vh - 200px)', display: 'flex', flexDirection: 'column' }}>
            {/* 消息区 */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '0 8px' }}>
              {messages.length === 0 ? (
                <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                  <RobotOutlined style={{ fontSize: 48, color: '#0EA5E9', marginBottom: 16 }} />
                  <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 8 }}>GEO 智能助手</div>
                  <div style={{ color: '#64748B', marginBottom: 24, fontSize: 13 }}>
                    基于公司知识库，为您解答公司相关问题
                  </div>
                  <Space wrap style={{ justifyContent: 'center' }}>
                    {quickQuestions.map((q, i) => (
                      <Tag
                        key={i}
                        color="blue"
                        style={{ cursor: 'pointer', padding: '6px 12px', fontSize: 13 }}
                        onClick={() => setInput(q)}
                      >
                        {q}
                      </Tag>
                    ))}
                  </Space>
                </div>
              ) : (
                messages.map((msg, idx) => (
                  <div key={idx} style={{
                    display: 'flex',
                    justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                    marginBottom: 16
                  }}>
                    {msg.role === 'assistant' && (
                      <div style={{
                        width: 36, height: 36, borderRadius: '50%',
                        background: '#0EA5E9', display: 'flex',
                        alignItems: 'center', justifyContent: 'center',
                        marginRight: 10, flexShrink: 0
                      }}>
                        <RobotOutlined style={{ color: '#fff' }} />
                      </div>
                    )}
                    <div style={{
                      maxWidth: '75%',
                      background: msg.role === 'user' ? '#0EA5E9' : '#F1F5F9',
                      color: msg.role === 'user' ? '#fff' : '#0F172A',
                      padding: '12px 16px',
                      borderRadius: msg.role === 'user' ? '12px 12px 0 12px' : '12px 12px 12px 0',
                      lineHeight: 1.7,
                      fontSize: 14,
                      whiteSpace: 'pre-wrap'
                    }}>
                      {msg.content}
                      {msg.platform && (
                        <div style={{ marginTop: 8, fontSize: 11, opacity: 0.7 }}>
                          来自 {PLATFORM_NAMES[msg.platform] || msg.platform}
                        </div>
                      )}
                      {msg.sources && msg.sources.length > 0 && (
                        <div style={{ marginTop: 12, borderTop: '1px solid rgba(0,0,0,0.1)', paddingTop: 8 }}>
                          <div style={{ fontSize: 11, marginBottom: 4, opacity: 0.7 }}>
                            <BookOutlined /> 参考来源：
                          </div>
                          {msg.sources.map((s: any, i: number) => (
                            <div key={i} style={{ fontSize: 11, opacity: 0.8, marginBottom: 2 }}>
                              {i + 1}. {s.title} (相关度 {(s.score * 100).toFixed(0)}%)
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                    {msg.role === 'user' && (
                      <div style={{
                        width: 36, height: 36, borderRadius: '50%',
                        background: '#64748B', display: 'flex',
                        alignItems: 'center', justifyContent: 'center',
                        marginLeft: 10, flexShrink: 0
                      }}>
                        <UserOutlined style={{ color: '#fff' }} />
                      </div>
                    )}
                  </div>
                ))
              )}
              {loading && (
                <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 16 }}>
                  <div style={{
                    width: 36, height: 36, borderRadius: '50%',
                    background: '#0EA5E9', display: 'flex',
                    alignItems: 'center', justifyContent: 'center',
                    marginRight: 10
                  }}>
                    <RobotOutlined style={{ color: '#fff' }} />
                  </div>
                  <div style={{
                    background: '#F1F5F9', padding: '12px 20px',
                    borderRadius: '12px 12px 12px 0'
                  }}>
                    <Spin size="small" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* 输入区 */}
            <div style={{ borderTop: '1px solid #E2E8F0', paddingTop: 16, marginTop: 8 }}>
              <Space.Compact style={{ width: '100%' }}>
                <Input.TextArea
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="输入您的问题，按Enter发送..."
                  autoSize={{ minRows: 1, maxRows: 4 }}
                  style={{ borderRadius: '8px 0 0 8px' }}
                />
                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  onClick={handleSend}
                  loading={loading}
                  style={{ height: 'auto', borderRadius: '0 8px 8px 0' }}
                >
                  发送
                </Button>
              </Space.Compact>
            </div>
          </div>
        </Col>

        {/* 右侧设置区 */}
        <Col xs={24} lg={8}>
          <div className="geo-card" style={{ marginBottom: 16 }}>
            <h3 style={{ fontSize: 15, marginBottom: 16 }}>问答设置</h3>
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 13, color: '#64748B', marginBottom: 6 }}>AI平台</div>
              <Select
                value={platform}
                onChange={setPlatform}
                style={{ width: '100%' }}
                options={platforms.map((p: any) => ({ value: p.code, label: p.name }))}
              />
            </div>
            <div>
              <div style={{ fontSize: 13, color: '#64748B', marginBottom: 6 }}>知识库级别</div>
              <Select
                value={level}
                onChange={setLevel}
                style={{ width: '100%' }}
                options={[
                  { value: 'public', label: '公开（默认）' },
                  { value: 'internal', label: '内部' },
                  { value: 'confidential', label: '涉密（仅管理员）', disabled: !isAdmin }
                ]}
              />
            </div>
          </div>

          <div className="geo-card">
            <h3 style={{ fontSize: 15, marginBottom: 12 }}>使用说明</h3>
            <ul style={{ paddingLeft: 16, margin: 0, color: '#64748B', fontSize: 13, lineHeight: 2 }}>
              <li>回答基于公司知识库生成</li>
              <li>支持多轮对话，自动理解上下文</li>
              <li>支持切换不同AI平台对比回答</li>
              <li>可选择知识库可见级别</li>
              <li>回答会标注参考来源</li>
              <li>未收录的问题会如实告知</li>
              <li>点击「清空对话」可重新开始</li>
            </ul>
          </div>
        </Col>
      </Row>
    </div>
  )
}

export default RAGChat
