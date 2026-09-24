import { useState, useEffect, useRef } from 'react'
import {
  Button, Input, Select, Avatar, Tag, Space, Divider, List, Popconfirm,
  message, Spin, Tooltip, Typography
} from 'antd'
import {
  PlusOutlined, DeleteOutlined, RobotOutlined, UserOutlined,
  DiffOutlined, SendOutlined, ThunderboltOutlined, BulbOutlined
} from '@ant-design/icons'
import { assetApi } from '@/api/asset'
import { marked } from 'marked'
import { sanitizeHtml } from '@/utils/sanitize'

const { Text } = Typography
const { TextArea, Search } = Input

// Markdown渲染组件
const MarkdownText = ({ content }: { content: string }) => {
  const html = marked.parse(content, { breaks: true })
  return (
    <div
      className="markdown-body"
      style={{ whiteSpace: 'normal' }}
      dangerouslySetInnerHTML={{ __html: sanitizeHtml(html as string) }}
    />
  )
}

// 固定4个医学通用问题
const FIXED_QUESTIONS = [
  '总结我收藏的所有文章的核心观点',
  '找出这些内容中有争议的医学观点',
  '帮我整理一份知识点清单',
  '基于我的收藏，推荐几个写作选题',
]

const KnowledgeChat = () => {
  // 对话状态
  const [chatModels, setChatModels] = useState<any[]>([])
  const [selectedModel, setSelectedModel] = useState('glm')
  const [chatTemplates, setChatTemplates] = useState<any[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState('auto')
  const [chatMessages, setChatMessages] = useState<any[]>([])
  const [chatInput, setChatInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)

  // 会话侧边栏
  const [sessions, setSessions] = useState<any[]>([])
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null)
  const [sessionKeyword, setSessionKeyword] = useState('')

  // 对比模式
  const [compareMode, setCompareMode] = useState(false)
  const [compareModels, setCompareModels] = useState<string[]>([])
  const [compareResults, setCompareResults] = useState<any[]>([])
  const [compareLoading, setCompareLoading] = useState(false)

  // 推荐问题
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [suggestionsLoading, setSuggestionsLoading] = useState(false)

  // 加载可用模型
  const fetchModels = async () => {
    try {
      const res: any = await assetApi.getChatModels()
      setChatModels(res.data.models || [])
      if (res.data.models?.length > 0) {
        setSelectedModel(res.data.models[0].code)
      }
    } catch (e) {
      // 静默失败
    }
  }

  const fetchTemplates = async () => {
    try {
      const res: any = await assetApi.getChatTemplates()
      setChatTemplates(res.data.templates || [])
    } catch (e) {
      // 静默失败
    }
  }

  // 加载会话列表（全局，不绑定文档）
  const fetchSessions = async (keyword?: string) => {
    try {
      const res: any = await assetApi.getChatSessions(undefined, keyword)
      setSessions(res.data.items || [])
    } catch (e) {
      // 静默失败
    }
  }

  // 加载推荐问题（sessionStorage缓存）
  const fetchSuggestions = async () => {
    const cached = sessionStorage.getItem('chat_suggestions')
    if (cached) {
      try {
        setSuggestions(JSON.parse(cached))
        return
      } catch (e) {
        // 解析失败，重新获取
      }
    }

    setSuggestionsLoading(true)
    try {
      const res: any = await assetApi.getChatSuggestions()
      const list = res.data.suggestions || []
      setSuggestions(list)
      if (list.length > 0) {
        sessionStorage.setItem('chat_suggestions', JSON.stringify(list))
      }
    } catch (e) {
      // 静默失败
    } finally {
      setSuggestionsLoading(false)
    }
  }

  useEffect(() => {
    fetchModels()
    fetchTemplates()
    fetchSessions()
    fetchSuggestions()
  }, [])

  // 对话滚动到底部
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages, compareResults])

  // 选择会话时加载消息
  const handleSelectSession = async (sessionId: number) => {
    setSelectedSessionId(sessionId)
    setCompareMode(false)
    setCompareResults([])
    try {
      const res: any = await assetApi.getChatMessages(sessionId)
      setChatMessages(res.data.messages || [])
    } catch (e) {
      message.error('加载会话失败')
    }
  }

  // 新建对话
  const handleNewChat = () => {
    setSelectedSessionId(null)
    setChatMessages([])
    setCompareResults([])
    setCompareMode(false)
  }

  // 删除会话
  const handleDeleteSession = async (sessionId: number) => {
    try {
      await assetApi.deleteChatSession(sessionId)
      message.success('会话已删除')
      fetchSessions(sessionKeyword)
      if (selectedSessionId === sessionId) {
        handleNewChat()
      }
    } catch (e) {
      message.error('删除失败')
    }
  }

  // 发送消息（普通模式，流式）
  const handleSendMessage = async (question?: string) => {
    const msg = question || chatInput
    if (!msg.trim() || streaming) return

    const userMsg = { role: 'user', content: msg }
    setChatMessages([...chatMessages, userMsg])
    setChatInput('')
    setStreaming(true)

    try {
      const token = localStorage.getItem('geo_token')
      const response = await fetch('/geo/api/v1/asset/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          session_id: selectedSessionId,
          document_id: undefined, // 全局问答，不绑定文档
          message: msg,
          platform: selectedModel,
          template: selectedTemplate,
        }),
      })

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No reader')

      const decoder = new TextDecoder()
      let buffer = ''
      let currentAnswer = ''
      let sources: any[] = []
      let sessionId: number | null = null

      // 添加一个空的AI回复占位
      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: '',
        platform: selectedModel,
        sources: [],
      }])

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6))

              if (event.type === 'meta') {
                sessionId = event.session_id
                sources = event.sources || []
                if (sessionId) {
                  setSelectedSessionId(sessionId)
                  fetchSessions(sessionKeyword) // 刷新会话列表
                }
              } else if (event.type === 'chunk') {
                currentAnswer += event.content
                // 更新最后一条AI消息
                setChatMessages(prev => {
                  const newMsgs = [...prev]
                  const last = newMsgs[newMsgs.length - 1]
                  if (last.role === 'assistant') {
                    last.content = currentAnswer
                    last.sources = sources
                  }
                  return newMsgs
                })
              } else if (event.type === 'error') {
                message.error(event.message || '生成失败')
              }
            } catch (e) {
              // 解析错误忽略
            }
          }
        }
      }
    } catch (e) {
      message.error('发送失败')
    } finally {
      setStreaming(false)
    }
  }

  // 多模型对比
  const handleCompare = async () => {
    if (!chatInput.trim() || compareModels.length === 0) {
      message.warning('请先选择要对比的模型')
      return
    }

    const question = chatInput
    setChatInput('')
    setCompareLoading(true)
    setCompareResults([])

    try {
      const res: any = await assetApi.compareChatModels({
        message: question,
        platforms: compareModels,
        document_id: undefined, // 全局问答
      })
      setCompareResults(res.data.results || [])
    } catch (e) {
      message.error('对比失败')
    } finally {
      setCompareLoading(false)
    }
  }

  const modelOptions = chatModels.map((m: any) => ({
    value: m.code,
    label: m.name,
  }))

  const allQuestions = [...FIXED_QUESTIONS, ...suggestions]

  return (
    <div style={{ padding: '16px 24px', height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column' }}>
      {/* 页面标题 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ margin: 0 }}>
            <ThunderboltOutlined style={{ color: '#1677ff', marginRight: 8 }} />
            医学知识助手
          </h2>
          <div style={{ color: '#999', fontSize: 13, marginTop: 4 }}>
            基于您的个人数字资产知识库，支持多模型对话和对比
          </div>
        </div>
      </div>

      {/* 主内容区：三栏布局 */}
      <div style={{ flex: 1, display: 'flex', gap: 16, minHeight: 0 }}>
        {/* 左侧：会话栏 */}
        <div style={{
          width: 240,
          border: '1px solid #e8e8e8',
          borderRadius: 8,
          display: 'flex',
          flexDirection: 'column',
          padding: 12,
          background: '#fafafa',
        }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleNewChat}
            style={{ marginBottom: 8 }}
            block
          >
            新建对话
          </Button>

          <Search
            placeholder="搜索会话..."
            size="small"
            allowClear
            onSearch={fetchSessions}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSessionKeyword(e.target.value)}
            style={{ marginBottom: 8 }}
          />

          <div style={{ flex: 1, overflowY: 'auto' }}>
            {sessions.length === 0 ? (
              <Text type="secondary" style={{ fontSize: 12 }}>暂无会话</Text>
            ) : (
              <List
                size="small"
                dataSource={sessions}
                renderItem={(item: any) => (
                  <List.Item
                    style={{
                      cursor: 'pointer',
                      padding: '8px 4px',
                      background: selectedSessionId === item.id ? '#e6f4ff' : 'transparent',
                      borderRadius: 4,
                    }}
                    onClick={() => handleSelectSession(item.id)}
                    actions={[
                      <Popconfirm
                        title="确定删除该会话？"
                        onConfirm={() => handleDeleteSession(item.id)}
                      >
                        <DeleteOutlined style={{ color: '#ff4d4f' }} onClick={(e) => e.stopPropagation()} />
                      </Popconfirm>
                    ]}
                  >
                    <List.Item.Meta
                      title={<Text ellipsis style={{ fontSize: 13 }}>{item.title}</Text>}
                      description={<Text type="secondary" style={{ fontSize: 11 }}>{item.platform}</Text>}
                    />
                  </List.Item>
                )}
              />
            )}
          </div>
        </div>

        {/* 中间：对话区 */}
        <div style={{
          flex: 1,
          border: '1px solid #e8e8e8',
          borderRadius: 8,
          display: 'flex',
          flexDirection: 'column',
          minWidth: 0,
        }}>
          {/* 对比模式模型选择 */}
          {compareMode && (
            <div style={{ padding: '12px 16px', borderBottom: '1px solid #e8e8e8', background: '#fafafa' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>选择要对比的模型（最多3个）：</Text>
              <div style={{ marginTop: 4 }}>
                {chatModels.map((m: any) => (
                  <Tag.CheckableTag
                    key={m.code}
                    checked={compareModels.includes(m.code)}
                    onChange={(checked) => {
                      if (checked) {
                        if (compareModels.length >= 3) {
                          message.warning('最多选择3个模型')
                          return
                        }
                        setCompareModels([...compareModels, m.code])
                      } else {
                        setCompareModels(compareModels.filter(c => c !== m.code))
                      }
                    }}
                    style={{ marginBottom: 4 }}
                  >
                    {m.name}
                  </Tag.CheckableTag>
                ))}
              </div>
            </div>
          )}

          {/* 消息列表 */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '16px 24px' }}>
            {/* 普通模式：单模型对话 */}
            {!compareMode && chatMessages.length === 0 && !streaming && (
              <div style={{ textAlign: 'center', padding: '40px 0' }}>
                <RobotOutlined style={{ fontSize: 48, marginBottom: 16, color: '#1677ff' }} />
                <p style={{ color: '#666', fontSize: 16 }}>开始和您的知识库对话吧</p>
                <p style={{ color: '#999', fontSize: 13 }}>AI会基于您收藏的所有内容回答问题</p>

                {/* 推荐问题 */}
                <div style={{ marginTop: 24, maxWidth: 600, margin: '24px auto 0' }}>
                  <div style={{ textAlign: 'left', marginBottom: 8 }}>
                    <Text type="secondary" style={{ fontSize: 13 }}>
                      <BulbOutlined style={{ marginRight: 4 }} />
                      推荐问题
                    </Text>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'flex-start' }}>
                    {suggestionsLoading ? (
                      <Spin size="small" />
                    ) : (
                      allQuestions.map((q, idx) => (
                        <Tag
                          key={idx}
                          style={{
                            cursor: 'pointer',
                            padding: '6px 12px',
                            fontSize: 13,
                            borderRadius: 16,
                            background: idx < 4 ? '#f0f5ff' : '#f6ffed',
                            borderColor: idx < 4 ? '#adc6ff' : '#b7eb8f',
                          }}
                          onClick={() => handleSendMessage(q)}
                        >
                          {q}
                        </Tag>
                      ))
                    )}
                  </div>
                </div>
              </div>
            )}

            {!compareMode && chatMessages.map((msg, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  marginBottom: 16,
                }}
              >
                {msg.role === 'assistant' && (
                  <Avatar
                    icon={<RobotOutlined />}
                    style={{ background: '#1677ff', marginRight: 8, flexShrink: 0 }}
                  />
                )}
                <div
                  style={{
                    maxWidth: '75%',
                    padding: '12px 16px',
                    borderRadius: 8,
                    background: msg.role === 'user' ? '#1677ff' : '#f5f5f5',
                    color: msg.role === 'user' ? '#fff' : '#333',
                  }}
                >
                  {msg.role === 'user' ? (
                    <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{msg.content}</div>
                  ) : (
                    <MarkdownText content={msg.content} />
                  )}

                  {/* 引用来源 */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid #e8e8e8' }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>引用来源：</Text>
                      {msg.sources.map((s: any, i: number) => (
                        <Tag key={i} style={{ fontSize: 11, margin: '2px 2px 0 0' }}>
                          {s.title}
                          {s.score !== undefined && (
                            <span style={{ color: '#999', marginLeft: 4 }}>
                              ({(s.score * 100).toFixed(0)}%)
                            </span>
                          )}
                        </Tag>
                      ))}
                    </div>
                  )}
                  {/* 模型标签 */}
                  {msg.role === 'assistant' && msg.platform && (
                    <div style={{ marginTop: 4 }}>
                      <Text type="secondary" style={{ fontSize: 11 }}>via {msg.platform}</Text>
                    </div>
                  )}
                </div>
                {msg.role === 'user' && (
                  <Avatar
                    icon={<UserOutlined />}
                    style={{ background: '#52c41a', marginLeft: 8, flexShrink: 0 }}
                  />
                )}
              </div>
            ))}

            {/* 对比模式结果 */}
            {compareMode && compareResults.length > 0 && (
              <div style={{ display: 'flex', gap: 16 }}>
                {compareResults.map((r: any, idx: number) => (
                  <div key={idx} style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      padding: '8px 12px',
                      background: '#1677ff',
                      color: '#fff',
                      borderRadius: '8px 8px 0 0',
                      fontSize: 14,
                      fontWeight: 500,
                    }}>
                      {chatModels.find((m: any) => m.code === r.platform)?.name || r.platform}
                    </div>
                    <div style={{
                      padding: 16,
                      border: '1px solid #e8e8e8',
                      borderTop: 'none',
                      borderRadius: '0 0 8px 8px',
                      background: '#fafafa',
                      maxHeight: 500,
                      overflowY: 'auto',
                    }}>
                      {r.success ? (
                        <MarkdownText content={r.content} />
                      ) : (
                        <Text type="danger" style={{ fontSize: 13 }}>{r.error}</Text>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {compareMode && compareLoading && (
              <div style={{ textAlign: 'center', padding: 40 }}>
                <Spin size="large" />
                <p style={{ marginTop: 12, color: '#999' }}>正在对比多个模型...</p>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* 输入区 */}
          <div style={{ padding: '12px 16px', borderTop: '1px solid #e8e8e8' }}>
            <div style={{ display: 'flex', gap: 8 }}>
              <TextArea
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder={compareMode ? '输入问题，点击"开始对比"...' : '输入问题，按 Enter 发送...'}
                autoSize={{ minRows: 1, maxRows: 4 }}
                onPressEnter={(e) => {
                  if (!e.shiftKey) {
                    e.preventDefault()
                    compareMode ? handleCompare() : handleSendMessage()
                  }
                }}
                style={{ flex: 1 }}
              />
              {compareMode ? (
                <Button
                  type="primary"
                  icon={<DiffOutlined />}
                  onClick={handleCompare}
                  loading={compareLoading}
                  disabled={!chatInput.trim() || compareModels.length === 0}
                >
                  开始对比
                </Button>
              ) : (
                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  onClick={() => handleSendMessage()}
                  loading={streaming}
                  disabled={!chatInput.trim()}
                >
                  发送
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* 右侧：设置栏 */}
        <div style={{
          width: 260,
          border: '1px solid #e8e8e8',
          borderRadius: 8,
          display: 'flex',
          flexDirection: 'column',
          padding: 16,
          background: '#fafafa',
        }}>
          <div style={{ marginBottom: 16 }}>
            <Text strong style={{ fontSize: 14 }}>对话设置</Text>
          </div>

          {/* 模型选择 */}
          <div style={{ marginBottom: 16 }}>
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
              AI模型
            </Text>
            <Select
              value={selectedModel}
              onChange={setSelectedModel}
              style={{ width: '100%' }}
              options={modelOptions}
              disabled={compareMode}
            />
          </div>

          {/* 助手模板选择 */}
          <div style={{ marginBottom: 16 }}>
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
              助手模式
            </Text>
            <Select
              value={selectedTemplate}
              onChange={setSelectedTemplate}
              style={{ width: '100%' }}
              options={chatTemplates.map((t: any) => ({
                value: t.key,
                label: `${t.icon} ${t.name}`,
              }))}
              disabled={compareMode}
            />
            {selectedTemplate !== 'auto' && chatTemplates.find((t: any) => t.key === selectedTemplate) && (
              <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 4 }}>
                {chatTemplates.find((t: any) => t.key === selectedTemplate)?.description}
              </Text>
            )}
          </div>

          {/* 对比模式开关 */}
          <div style={{ marginBottom: 16 }}>
            <Button
              block
              icon={<DiffOutlined />}
              type={compareMode ? 'primary' : 'default'}
              onClick={() => {
                setCompareMode(!compareMode)
                setCompareResults([])
              }}
            >
              {compareMode ? '退出对比模式' : '多模型对比'}
            </Button>
          </div>

          <Divider style={{ margin: '8px 0' }} />

          {/* 使用说明 */}
          <div style={{ flex: 1, overflowY: 'auto' }}>
            <Text strong style={{ fontSize: 13 }}>使用说明</Text>
            <div style={{ marginTop: 8, fontSize: 12, color: '#666', lineHeight: 1.8 }}>
              <p>1. 基于您收藏的所有数字资产进行问答</p>
              <p>2. 支持8个国产大模型切换</p>
              <p>3. 4种助手模式：通用/文献精读/临床决策/科普创作</p>
              <p>4. 多模型对比：同时对比最多3个模型的回答</p>
              <p>5. 引用来源显示相关文档及相似度</p>
              <p>6. 对话历史自动保存，可随时回看</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default KnowledgeChat
