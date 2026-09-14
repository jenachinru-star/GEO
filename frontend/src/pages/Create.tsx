import { useEffect, useState } from 'react'
import {
  Row, Col, Button, Select, Modal, Form, Input,
  message, Space, Tag, Empty, Typography
} from 'antd'
import {
  FileTextOutlined, VideoCameraOutlined, PlusOutlined,
  CheckCircleOutlined, WarningOutlined
} from '@ant-design/icons'
import { semanticApi, articleApi, toolsApi, templateApi } from '@/api'
import { PUBLISH_PLATFORMS, PUBLISH_PLATFORM_NAMES } from '@/store/useStore'

const { Title, Text } = Typography

const Create = () => {
  const [semantics, setSemantics] = useState<any[]>([])
  const [selectedSemantic, setSelectedSemantic] = useState<number | null>(null)
  const [selectedPlatform, setSelectedPlatform] = useState<string>('wechat')
  const [toolConfig, setToolConfig] = useState<any>(null)
  const [modalVisible, setModalVisible] = useState(false)
  const [form] = Form.useForm()
  const [articles, setArticles] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [templateData, setTemplateData] = useState<any>(null)
  const [templateLoading, setTemplateLoading] = useState(false)

  const loadSemantics = async () => {
    try {
      const res: any = await semanticApi.getList({ is_active: true })
      setSemantics(res.data.items || res.data || [])
    } catch (e) {}
  }

  const loadTools = async () => {
    try {
      const res: any = await toolsApi.getConfig()
      setToolConfig(res.data)
    } catch (e) {}
  }

  const loadArticles = async () => {
    setLoading(true)
    try {
      const res: any = await articleApi.getList({ page_size: 50 })
      setArticles(res.data.items || [])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSemantics()
    loadTools()
    loadArticles()
  }, [])

  const handleGenerateArticle = () => {
    if (!selectedSemantic) {
      message.warning('请先选择语义问题')
      return
    }
    const semantic = semantics.find(s => s.id === selectedSemantic)
    const url = toolConfig?.article_tool_url || 'https://ops.szcczh.com/paper-next/'
    // 带参数跳转，工具端支持就预填，不支持也不报错
    const params = new URLSearchParams()
    if (semantic) params.set('semantic_question', semantic.question)
    params.set('publish_platform', selectedPlatform)
    const fullUrl = `${url}?${params.toString()}`
    window.open(fullUrl, '_blank')
    message.info('已打开文章生成工具，生成后请回到此页记录文章')
  }

  const handleGenerateVideo = () => {
    if (!selectedSemantic) {
      message.warning('请先选择语义问题')
      return
    }
    const semantic = semantics.find(s => s.id === selectedSemantic)
    const url = toolConfig?.video_tool_url || 'https://video.szcczh.com/'
    const params = new URLSearchParams()
    if (semantic) params.set('semantic_question', semantic.question)
    const fullUrl = `${url}?${params.toString()}`
    window.open(fullUrl, '_blank')
    message.info('已打开视频生成工具')
  }

  const handleAddArticle = async () => {
    try {
      const values = await form.validateFields()
      await articleApi.create({
        semantic_id: selectedSemantic,
        ...values
      })
      message.success('文章记录已添加')
      setModalVisible(false)
      form.resetFields()
      loadArticles()
    } catch (e) {}
  }

  const handleGenerateTemplate = async () => {
    if (!selectedSemantic) {
      message.warning('请先选择语义问题')
      return
    }
    setTemplateLoading(true)
    try {
      const res: any = await templateApi.generateArticle(selectedSemantic)
      setTemplateData(res.data)
    } finally {
      setTemplateLoading(false)
    }
  }

  const handleCopyTemplate = () => {
    if (!templateData) return
    navigator.clipboard.writeText(templateData.full_text)
    message.success('模板已复制到剪贴板，可粘贴到文章工具中使用')
  }

  const selectedSemanticData = semantics.find(s => s.id === selectedSemantic)
  const semanticArticles = selectedSemantic
    ? articles.filter(a => a.semantic_id === selectedSemantic)
    : articles

  return (
    <div>
      <div className="page-title-bar">
        <div>
          <h2>创作中心</h2>
          <div className="page-desc">选择语义问题，跳转工具生成内容，记录产出追踪效果</div>
        </div>
      </div>

      {/* 语义选择 */}
      <div className="geo-card" style={{ marginBottom: 20 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text strong style={{ fontSize: 14 }}>第一步：选择语义问题</Text>
          <Select
            placeholder="请选择要创作的语义问题"
            style={{ width: '100%' }}
            value={selectedSemantic || undefined}
            onChange={setSelectedSemantic}
            showSearch
            optionFilterProp="label"
            options={semantics.map(s => ({ value: s.id, label: s.question }))}
          />
          {selectedSemanticData && (
            <div style={{ background: '#EFF6FF', padding: '10px 14px', borderRadius: 8 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                当前语义：{selectedSemanticData.question}
                （GEO率 {selectedSemanticData.geo_rate}% / AEO率 {selectedSemanticData.aeo_rate}% /
                已产出 {selectedSemanticData.article_count} 篇文章）
              </Text>
            </div>
          )}
        </Space>
      </div>

      {/* 工具卡片 */}
      <Row gutter={16} style={{ marginBottom: 20 }}>
        <Col xs={24} md={12}>
          <div className="geo-card" style={{ height: '100%', borderLeft: '3px solid var(--primary)' }}>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
              <FileTextOutlined style={{ fontSize: 28, color: 'var(--primary)', marginRight: 12 }} />
              <div>
                <Title level={4} style={{ margin: 0 }}>生成文章</Title>
                <Text type="secondary">问答式结构，AEO问句式标题</Text>
              </div>
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text type="secondary" style={{ fontSize: 13 }}>发布平台：</Text>
              <Select
                value={selectedPlatform}
                onChange={setSelectedPlatform}
                style={{ width: 240, marginLeft: 8 }}
                optionFilterProp="label"
              >
                {[1, 2, 3].map(tier => (
                  <Select.OptGroup key={tier} label={tier === 1 ? '🔥 AI高优先抓取平台' : tier === 2 ? '🏥 医疗权威平台' : '📢 补充收录平台'}>
                    {PUBLISH_PLATFORMS.filter(p => p.tier === tier).map(p => (
                      <Select.Option key={p.code} value={p.code} label={p.name}>
                        <span>{p.name}</span>
                        <span style={{ color: '#999', fontSize: 12, marginLeft: 8 }}>{p.tierLabel}</span>
                      </Select.Option>
                    ))}
                  </Select.OptGroup>
                ))}
              </Select>
              {selectedPlatform && (() => {
                const p = PUBLISH_PLATFORMS.find(x => x.code === selectedPlatform)
                if (!p) return null
                return (
                  <div style={{ background: '#FFFBEB', padding: '10px 14px', borderRadius: 8, marginTop: 8, fontSize: 12 }}>
                    <div style={{ color: '#92400E', marginBottom: 4 }}>💡 AI抓取价值：{p.aiValue}</div>
                    <div style={{ color: '#92400E' }}>⚠️ 平台规则：{p.rules.join('；')}</div>
                  </div>
                )
              })()}
            </div>
            <Button
              type="primary"
              size="large"
              block
              icon={<FileTextOutlined />}
              onClick={handleGenerateArticle}
              className="btn-primary-gradient"
            >
              打开文章工具
            </Button>
          </div>
        </Col>
        <Col xs={24} md={12}>
          <div className="geo-card" style={{ height: '100%', borderLeft: '3px solid var(--purple)' }}>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
              <VideoCameraOutlined style={{ fontSize: 28, color: 'var(--purple)', marginRight: 12 }} />
              <div>
                <Title level={4} style={{ margin: 0 }}>生成视频</Title>
                <Text type="secondary">口播/动画视频，多平台适配</Text>
              </div>
            </div>
            <div style={{ marginBottom: 16, height: 32 }}>
              <Text type="secondary" style={{ fontSize: 13 }}>基于当前语义问题生成视频内容</Text>
            </div>
            <Button
              type="primary"
              size="large"
              block
              icon={<VideoCameraOutlined />}
              onClick={handleGenerateVideo}
              style={{ background: 'var(--purple-gradient)', border: 'none', boxShadow: '0 4px 16px rgba(139,92,246,0.25)' }}
            >
              打开视频工具
            </Button>
          </div>
        </Col>
      </Row>

      {/* GEO文章模板 */}
      {selectedSemantic && (
        <div className="geo-card" style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <Title level={5} style={{ margin: 0, color: '#1D4ED8' }}>📝 GEO/AEO 文章模板</Title>
            <Space>
              <Button onClick={handleGenerateTemplate} loading={templateLoading}>
                {templateData ? '重新生成' : '生成模板'}
              </Button>
              {templateData && (
                <Button type="primary" onClick={handleCopyTemplate} className="btn-primary-gradient">一键复制</Button>
              )}
            </Space>
          </div>
          {templateData ? (
            <div style={{ background: '#F8FAFC', padding: 16, borderRadius: 12, fontSize: 13, lineHeight: 1.8 }}>
              <div style={{ fontWeight: 600, marginBottom: 8, color: '#1D4ED8' }}>【标题】{templateData.title}</div>
              <div style={{ marginBottom: 8 }}><strong>【首段】</strong>{templateData.intro}</div>
              <div style={{ marginBottom: 8, whiteSpace: 'pre-wrap' }}><strong>【正文】</strong>{templateData.body}</div>
              <div style={{ marginBottom: 8 }}><strong>【文末】</strong>{templateData.conclusion}</div>
              <div style={{ color: '#6B7280' }}>
                <strong>【标签】</strong>
                {templateData.tags.map((t: string, i: number) => (
                  <span key={i} className="geo-tag geo-tag-blue" style={{ marginRight: 6 }}>{t}</span>
                ))}
              </div>
            </div>
          ) : (
            <Empty description="选择语义后点击生成模板，自动填充医生信息和标准结构" />
          )}
        </div>
      )}

      {/* 已生成文章 */}
      <div className="geo-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <Title level={5} style={{ margin: 0 }}>
            已记录的文章 {selectedSemantic ? `（当前语义下 ${semanticArticles.length} 篇）` : `（共 ${articles.length} 篇）`}
          </Title>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              if (!selectedSemantic) {
                message.warning('请先选择语义问题')
                return
              }
              setModalVisible(true)
            }}
            className="btn-primary-gradient"
          >
            记录已生成的文章
          </Button>
        </div>

        {semanticArticles.length === 0 ? (
          <Empty description="暂无文章记录，生成后请点击上方按钮记录" />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {semanticArticles.map((a: any) => (
              <div key={a.id} style={{
                padding: '14px 18px',
                background: '#F8FAFC',
                borderRadius: 12,
                border: '1px solid var(--border-color)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = '#F1F5F9' }}
              onMouseLeave={(e) => { e.currentTarget.style.background = '#F8FAFC' }}
              >
                <div>
                  <Text strong>{a.title || '（无标题）'}</Text>
                  <div style={{ marginTop: 4 }}>
                    <Tag color="blue">{PUBLISH_PLATFORM_NAMES[a.platform] || a.platform}</Tag>
                    <Tag color={a.status === 'published' ? 'green' : 'default'}>
                      {a.status === 'published' ? '已发布' : '草稿'}
                    </Tag>
                    {a.entity_consistent ? (
                      <Tag icon={<CheckCircleOutlined />} color="success">实体一致</Tag>
                    ) : (
                      <Tag icon={<WarningOutlined />} color="warning">需校验</Tag>
                    )}
                  </div>
                </div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {new Date(a.created_at).toLocaleDateString()}
                </Text>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 记录文章弹窗 */}
      <Modal
        title="记录已生成的文章"
        open={modalVisible}
        onOk={handleAddArticle}
        onCancel={() => setModalVisible(false)}
        okText="保存"
        cancelText="取消"
        width={560}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="文章标题" rules={[{ required: true, message: '请输入文章标题' }]}>
            <Input placeholder="请输入文章标题" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="platform" label="发布平台" initialValue="wechat">
                <Select optionFilterProp="label">
                  {[1, 2, 3].map(tier => (
                    <Select.OptGroup key={tier} label={tier === 1 ? '🔥 AI高优先抓取' : tier === 2 ? '🏥 医疗权威' : '📢 补充收录'}>
                      {PUBLISH_PLATFORMS.filter(p => p.tier === tier).map(p => (
                        <Select.Option key={p.code} value={p.code} label={p.name}>{p.name}</Select.Option>
                      ))}
                    </Select.OptGroup>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="status" label="状态" initialValue="published">
                <Select options={[
                  { value: 'draft', label: '草稿' },
                  { value: 'published', label: '已发布' }
                ]} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="content" label="文章内容/链接">
            <Input.TextArea rows={4} placeholder="粘贴文章全文或发布链接，用于实体一致性校验" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default Create
