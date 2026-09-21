import { useState, useEffect, useRef } from 'react'
import { formatUtcTime } from '@/utils/time'
import { Card, Button, Space, Typography, Tag, Spin, message, Tabs, Divider, Select, Input, Avatar, List, Popconfirm } from 'antd'
import { ArrowLeftOutlined, RobotOutlined, SendOutlined, UserOutlined, ThunderboltOutlined, PlusOutlined, SearchOutlined, EditOutlined, DeleteOutlined, DiffOutlined } from '@ant-design/icons'
import { useNavigate, useParams } from 'react-router-dom'
import { assetApi } from '@/api/asset'
import MindmapViewer from '@/components/MindmapViewer'
import { marked } from 'marked'

const { Title, Paragraph, Text } = Typography
const { TextArea, Search } = Input

// Markdown渲染组件
const MarkdownText = ({ content }: { content: string }) => {
  const html = marked.parse(content, { breaks: true })
  return (
    <div
      className="markdown-body"
      style={{ whiteSpace: 'normal' }}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}

const AssetDetail = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [detail, setDetail] = useState<any>(null)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [publishLoading, setPublishLoading] = useState(false)
  const [exportLoading, setExportLoading] = useState('')
  const [allTags, setAllTags] = useState<any[]>([])
  const [currentTagIds, setCurrentTagIds] = useState<number[]>([])

  // 对话状态
  const [chatModels, setChatModels] = useState<any[]>([])
  const [selectedModel, setSelectedModel] = useState('glm')
  const [chatTemplates, setChatTemplates] = useState<any[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState('auto')
  const [chatMessages, setChatMessages] = useState<any[]>([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)

  // 会话侧边栏
  const [sessions, setSessions] = useState<any[]>([])
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null)
  const [sessionKeyword, setSessionKeyword] = useState('')
  const [showSessionSidebar, setShowSessionSidebar] = useState(true)

  // 对比模式
  const [compareMode, setCompareMode] = useState(false)
  const [compareModels, setCompareModels] = useState<string[]>([])
  const [compareResults, setCompareResults] = useState<any[]>([])

  const fetchDetail = async () => {
    setLoading(true)
    try {
      const res: any = await assetApi.getSourceDetail(Number(id))
      setDetail(res.data)
    } catch (e) {
      message.error('加载失败')
    } finally {
      setLoading(false)
    }
  }

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

  // 加载会话列表
  const fetchSessions = async (keyword?: string) => {
    try {
      const res: any = await assetApi.getChatSessions(Number(id), keyword)
      setSessions(res.data.items || [])
    } catch (e) {
      // 静默失败
    }
  }

  useEffect(() => {
    if (id) {
      fetchDetail()
      fetchSessions()
    }
    fetchModels()
  }, [id])

  // 对话滚动到底部
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages, compareResults])

  // 选择会话时加载消息
  const handleSelectSession = async (sessionId: number) => {
    setSelectedSessionId(sessionId)
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

  const handleExport = async (format: 'md' | 'html' | 'pdf' | 'mindmap' | 'excel' | 'ppt') => {
    if (!detail?.document) {
      message.warning('文档尚未解析完成')
      return
    }
    setExportLoading(format)
    try {
      const blob = await assetApi.exportDocument({
        document_id: detail.document.id,
        format,
      })
      // 创建下载链接
      const url = window.URL.createObjectURL(new Blob([blob as any]))
      const link = document.createElement('a')
      link.href = url
      const extMap: Record<string, string> = { md: 'md', html: 'html', pdf: 'pdf', mindmap: 'mm.md', excel: 'xlsx', ppt: 'pptx' }
      const ext = extMap[format] || 'md'
      link.setAttribute('download', `${detail.document.title.slice(0, 50)}.${ext}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      message.success('导出成功')
    } catch (e: any) {
      const errMsg = e?.response?.data?.detail || '导出失败'
      message.error(errMsg)
    } finally {
      setExportLoading('')
    }
  }

  const handlePublish = async () => {
    if (!detail?.document) {
      message.warning('文档尚未解析完成')
      return
    }
    setPublishLoading(true)
    try {
      const res: any = await assetApi.publishFromDocument({
        document_id: detail.document.id,
        platform: selectedModel,
        auto_rewrite: true,
      })
      message.success('已创建发布草稿，前往编辑')
      // 跳转到发布列表页
      navigate('/asset/published')
    } catch (e) {
      message.error('创建发布草稿失败')
    } finally {
      setPublishLoading(false)
    }
  }

  const handleGenerateSummary = async () => {
    if (!detail?.document) {
      message.warning('文档尚未解析完成')
      return
    }
    setSummaryLoading(true)
    try {
      await assetApi.generateSummary({
        document_id: detail.document.id,
        platform: selectedModel,
        prompt_template: 'article',
      })
      message.success('AI总结完成')
      fetchDetail()
    } catch (e) {
      message.error('AI总结失败')
    } finally {
      setSummaryLoading(false)
    }
  }

  // 发送消息（普通模式，流式）
  const handleSendMessage = async () => {
    if (!chatInput.trim() || streaming) return

    const userMsg = { role: 'user', content: chatInput }
    setChatMessages([...chatMessages, userMsg])
    const question = chatInput
    setChatInput('')
    setStreaming(true)

    try {
      const response = await fetch('/geo/api/v1/asset/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: selectedSessionId,
          document_id: detail?.document?.id,
          message: question,
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
              } else if (event.type === 'done') {
                // 完成
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
    setChatLoading(true)
    setCompareResults([])

    try {
      const res: any = await assetApi.compareChatModels({
        message: question,
        platforms: compareModels,
        document_id: detail?.document?.id,
      })
      setCompareResults(res.data.results || [])
    } catch (e) {
      message.error('对比失败')
    } finally {
      setChatLoading(false)
    }
  }

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!detail) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <p>资产不存在</p>
        <Button onClick={() => navigate('/asset')}>返回资产库</Button>
      </div>
    )
  }

  const doc = detail.document

  // 模型选择选项
  const modelOptions = chatModels.map((m: any) => ({
    value: m.code,
    label: m.name,
  }))

  const chatTabContent = (
    <div style={{ display: 'flex', height: 600 }}>
      {/* 会话侧边栏 */}
      {showSessionSidebar && (
        <div style={{
          width: 220,
          borderRight: '1px solid #e8e8e8',
          display: 'flex',
          flexDirection: 'column',
          paddingRight: 12,
          marginRight: 12,
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
            onChange={(e) => setSessionKeyword(e.target.value)}
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
      )}

      {/* 对话主区域 */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* 模型选择栏 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <Space>
            <Text type="secondary">模型：</Text>
            <Select
              value={selectedModel}
              onChange={setSelectedModel}
              style={{ width: 130 }}
              options={modelOptions}
            />
            <Text type="secondary" style={{ marginLeft: 16 }}>助手：</Text>
            <Select
              value={selectedTemplate}
              onChange={setSelectedTemplate}
              style={{ width: 130 }}
              options={chatTemplates.map((t: any) => ({
                value: t.key,
                label: `${t.icon}`,
              }))}
            />
            <Button
              size="small"
              icon={<DiffOutlined />}
              type={compareMode ? 'primary' : 'default'}
              onClick={() => setCompareMode(!compareMode)}
            >
              对比模式
            </Button>
          </Space>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {showSessionSidebar ? (
              <span onClick={() => setShowSessionSidebar(false)} style={{ cursor: 'pointer' }}>隐藏侧边栏</span>
            ) : (
              <span onClick={() => setShowSessionSidebar(true)} style={{ cursor: 'pointer' }}>显示侧边栏</span>
            )}
          </Text>
        </div>

        <Divider style={{ margin: '8px 0' }} />

        {/* 对比模式模型选择 */}
        {compareMode && (
          <div style={{ marginBottom: 12 }}>
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
        <div style={{ flex: 1, overflowY: 'auto', marginBottom: 12, padding: '0 4px' }}>
          {/* 普通模式：单模型对话 */}
          {!compareMode && chatMessages.length === 0 && !streaming && (
            <div style={{ textAlign: 'center', padding: '60px 0', color: '#999' }}>
              <RobotOutlined style={{ fontSize: 48, marginBottom: 16, color: '#1677ff' }} />
              <p>开始和您的知识库对话吧</p>
              <p style={{ fontSize: 13 }}>AI会基于本文档和您收藏的其他内容回答问题</p>
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
                  style={{ background: '#87d068', marginLeft: 8, flexShrink: 0 }}
                />
              )}
            </div>
          ))}

          {/* 对比模式：并排展示 */}
          {compareMode && compareResults.length > 0 && (
            <div style={{ display: 'flex', gap: 12, height: '100%' }}>
              {compareResults.map((result: any) => {
                const modelInfo = chatModels.find(m => m.code === result.platform)
                return (
                  <div key={result.platform} style={{ flex: 1, border: '1px solid #e8e8e8', borderRadius: 8, padding: 12, overflowY: 'auto' }}>
                    <div style={{ marginBottom: 8, paddingBottom: 8, borderBottom: '1px solid #f0f0f0' }}>
                      <Tag color={modelInfo?.color}>{modelInfo?.name || result.platform}</Tag>
                    </div>
                    {result.success ? (
                      <MarkdownText content={result.content} />
                    ) : (
                      <Text type="danger">{result.error || '生成失败'}</Text>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {chatLoading && (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 20 }}>
              <Spin tip="正在调用多个模型对比中..." />
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* 输入框 */}
        <div style={{ display: 'flex', gap: 8 }}>
          <TextArea
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            placeholder={compareMode ? '输入问题，对比多个模型回答...' : '输入您的问题，Enter发送，Shift+Enter换行...'}
            autoSize={{ minRows: 2, maxRows: 4 }}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault()
                compareMode ? handleCompare() : handleSendMessage()
              }
            }}
            disabled={streaming}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={compareMode ? handleCompare : handleSendMessage}
            loading={chatLoading || streaming}
            style={{ height: 'auto' }}
          >
            {compareMode ? '对比' : '发送'}
          </Button>
        </div>
      </div>
    </div>
  )

  return (
    <div style={{ padding: '24px', maxWidth: 1200, margin: '0 auto' }}>
      {/* 顶部导航 */}
      <Button
        type="text"
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/asset')}
        style={{ marginBottom: 16 }}
      >
        返回资产库
      </Button>

      {/* 标题区 */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ flex: 1 }}>
            <Title level={3} style={{ margin: '0 0 8px 0' }}>
              {detail.title || '未命名'}
            </Title>
            <Space>
              <Tag color="blue">{detail.source_type}</Tag>
              {detail.category && <Tag>{detail.category}</Tag>}
              {detail.source_site && <Text type="secondary">来源: {detail.source_site}</Text>}
              {detail.tags && detail.tags.split(',').map((tag: string, i: number) => (
                <Tag key={i}>{tag}</Tag>
              ))}
            </Space>
          </div>
          <Space>
            <Space>
              <Button
                icon={<RobotOutlined />}
                loading={summaryLoading}
                onClick={handleGenerateSummary}
              >
                AI总结
              </Button>
              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                loading={publishLoading}
                onClick={handlePublish}
              >
                发布为科普
              </Button>
              <Dropdown menu={{
                items: [
                  { key: 'md', label: 'Markdown (.md)' },
                  { key: 'html', label: 'HTML 网页' },
                  { key: 'pdf', label: 'PDF 文档' },
                  { type: 'divider' },
                  { key: 'mindmap', label: '思维导图 (Markmap)' },
                  { key: 'excel', label: 'Excel 表格' },
                  { key: 'ppt', label: 'PPT 演示文稿' },
                ],
                onClick: ({ key }) => handleExport(key as any),
              }}>
                <Button icon={<DownloadOutlined />} loading={!!exportLoading}>
                  导出
                </Button>
              </Dropdown>
            </Space>
          </Space>
        </div>
      </Card>

      {/* 内容区 */}
      <Tabs
        defaultActiveKey="chat"
        items={[
          {
            key: 'chat',
            label: <span><ThunderboltOutlined /> 智能问答</span>,
            children: chatTabContent,
          },
          {
            key: 'content',
            label: '原文内容',
            children: doc ? (
              <Card>
                {doc.summary && (
                  <>
                    <Title level={4}>AI总结</Title>
                    <Paragraph style={{ background: '#f6ffed', padding: 16, borderRadius: 8 }}>
                      <MarkdownText content={doc.summary} />
                    </Paragraph>
                    <Divider />
                  </>
                )}
                <Title level={4}>全文</Title>
                <Paragraph style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
                  {doc.content || '内容解析中...'}
                </Paragraph>
              </Card>
            ) : (
              <Card>
                <Text type="secondary">文档内容正在解析中...</Text>
              </Card>
            ),
          },
          {
            key: 'notes',
            label: `笔记 (${detail.notes?.length || 0})`,
            children: (
              <Card>
                {detail.notes?.length > 0 ? (
                  detail.notes.map((note: any) => (
                    <Card key={note.id} size="small" style={{ marginBottom: 12 }}>
                      <div style={{ fontWeight: 500, marginBottom: 8 }}>{note.title || '无标题'}</div>
                      <Paragraph style={{ whiteSpace: 'pre-wrap', marginBottom: 0 }}>
                        {note.content}
                      </Paragraph>
                    </Card>
                  ))
                ) : (
                  <Text type="secondary">还没有笔记，开始记录您的思考吧</Text>
                )}
              </Card>
            ),
          },
          {
            key: 'meta',
            label: '元信息',
            children: (
              <Card>
                <p><Text type="secondary">标题：</Text>{detail.title}</p>
                <p><Text type="secondary">来源URL：</Text>{detail.url || '-'}</p>
                <p><Text type="secondary">分类：</Text>{detail.category || '-'}</p>
                <p><Text type="secondary">标签：</Text>{detail.tags || '-'}</p>
                <p><Text type="secondary">创建时间：</Text>{detail.created_at ? formatUtcTime(detail.created_at) : '-'}</p>
                <p><Text type="secondary">更新时间：</Text>{detail.updated_at ? formatUtcTime(detail.updated_at) : '-'}</p>
              </Card>
            ),
          },
        ]}
      />
    </div>
  )
}

export default AssetDetail

