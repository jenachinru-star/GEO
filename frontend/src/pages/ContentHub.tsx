import { useEffect, useState } from 'react'
import {
  Row, Col, Button, Select, Modal, Form, Input,
  message, Space, Tag, Empty, Typography, Table,
  Drawer, Popconfirm, Statistic, Tabs, Badge
} from 'antd'
import {
  FileTextOutlined, VideoCameraOutlined, PlusOutlined,
  CheckCircleOutlined, WarningOutlined, ReloadOutlined,
  DeleteOutlined, EyeOutlined, EditOutlined,
  ThunderboltOutlined, BlockOutlined
} from '@ant-design/icons'
import { semanticApi, articleApi, toolsApi, templateApi, distributionApi, opportunityApi } from '@/api'
import { PUBLISH_PLATFORMS, PUBLISH_PLATFORM_NAMES, ARTICLE_STATUS_NAMES } from '@/store/useStore'
import { formatUtcDate } from '@/utils/time'

const { Title, Text } = Typography

const OPPORTUNITY_TYPE_NAMES: Record<string, string> = {
  missing_mention: 'AI未提及',
  missing_citation: '缺少引用',
  low_rank: '排名靠后',
}

const OPPORTUNITY_TYPE_COLORS: Record<string, string> = {
  missing_mention: 'red',
  missing_citation: 'orange',
  low_rank: 'blue',
}

const ContentHub = () => {
  // ========== 创作工作台 state（来自 Create.tsx）==========
  const [semantics, setSemantics] = useState<any[]>([])
  const [selectedSemantic, setSelectedSemantic] = useState<number | null>(null)
  const [selectedPlatform, setSelectedPlatform] = useState<string>('wechat')
  const [toolConfig, setToolConfig] = useState<any>(null)
  const [templateData, setTemplateData] = useState<any>(null)
  const [templateLoading, setTemplateLoading] = useState(false)

  // ========== 文章管理 state（来自 Content.tsx）==========
  const [list, setList] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const [drawerVisible, setDrawerVisible] = useState(false)
  const [detail, setDetail] = useState<any>(null)
  const [validateResult, setValidateResult] = useState<any>(null)
  const [form] = Form.useForm()
  const [filters, setFilters] = useState({ semantic_id: '' as number | '', status: '' as string, keyword: '' })
  const [page, setPage] = useState(1)
  const [stats, setStats] = useState({ total: 0, published: 0, consistent: 0 })
  const [distributions, setDistributions] = useState<any[]>([])
  const [distForm] = Form.useForm()

  // ========== 内容机会 state ==========
  const [opportunities, setOpportunities] = useState<any[]>([])
  const [oppLoading, setOppLoading] = useState(false)
  const [oppScanning, setOppScanning] = useState(false)
  const [activeTab, setActiveTab] = useState('create')

  // ========== 数据加载 ==========
  const loadSemantics = async () => {
    try {
      const res: any = await semanticApi.getList({ page_size: 100 })
      setSemantics(res.data.items || res.data || [])
    } catch (e) {}
  }

  const loadTools = async () => {
    try {
      const res: any = await toolsApi.getConfig()
      setToolConfig(res.data)
    } catch (e) {}
  }

  const loadData = async () => {
    setLoading(true)
    try {
      const params: any = { page, page_size: 20 }
      if (filters.semantic_id) params.semantic_id = filters.semantic_id
      if (filters.status) params.status = filters.status
      const res: any = await articleApi.getList(params)
      let items = res.data.items || []
      if (filters.keyword) {
        items = items.filter((a: any) => a.title?.includes(filters.keyword))
      }
      setList(items)
      setTotal(res.data.total || items.length)
      setStats({
        total: res.data.total || 0,
        published: items.filter((a: any) => a.status === 'published').length,
        consistent: items.filter((a: any) => a.entity_consistent).length
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSemantics()
    loadTools()
    loadOpportunities()
  }, [])

  useEffect(() => {
    loadData()
  }, [filters, page])

  // ========== 创作工作台函数（来自 Create.tsx）==========
  const handleGenerateArticle = () => {
    if (!selectedSemantic) {
      message.warning('请先选择语义问题')
      return
    }
    const semantic = semantics.find(s => s.id === selectedSemantic)
    const url = toolConfig?.article_tool_url || 'https://ops.szcczh.com/paper-next/'
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

  const handleSaveTemplateToArticle = async () => {
    if (!templateData || !selectedSemantic) return
    try {
      await articleApi.create({
        title: templateData.title,
        content: templateData.full_text || `${templateData.intro}\n\n${templateData.body}\n\n${templateData.conclusion}`,
        semantic_id: selectedSemantic,
        platform: 'wechat',
        status: 'draft',
      })
      message.success('已保存到文章库')
      loadData()
    } catch (e: any) {
      message.error('保存失败：' + (e.response?.data?.detail || e.message))
    }
  }

  // ========== 文章管理函数（来自 Content.tsx）==========
  const handleAdd = () => {
    setEditMode(false)
    setEditId(null)
    form.resetFields()
    // 从创作工作台添加时，预填当前选中语义
    if (selectedSemantic) {
      form.setFieldsValue({ semantic_id: selectedSemantic })
    }
    setModalVisible(true)
  }

  const handleEdit = (record: any) => {
    setEditMode(true)
    setEditId(record.id)
    form.setFieldsValue({
      title: record.title,
      platform: record.platform,
      status: record.status,
      semantic_id: record.semantic_id,
      content: record.content
    })
    setModalVisible(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editMode && editId) {
        await articleApi.update(editId, values)
        message.success('更新成功')
      } else {
        await articleApi.create(values)
        message.success('添加成功')
      }
      setModalVisible(false)
      form.resetFields()
      loadData()
    } catch (e) {}
  }

  const handleDelete = async (id: number) => {
    await articleApi.delete(id)
    message.success('删除成功')
    loadData()
  }

  const handleView = async (record: any) => {
    setDetail(record)
    setValidateResult(null)
    setDrawerVisible(true)
    loadDistributions(record.id)
  }

  const loadDistributions = async (articleId: number) => {
    try {
      const res: any = await distributionApi.getList({ article_id: articleId })
      setDistributions(res.data.items || [])
    } catch (e) {}
  }

  const handleAddDistribution = async () => {
    try {
      const values = await distForm.validateFields()
      await distributionApi.create({ article_id: detail.id, ...values })
      message.success('分发记录已添加')
      distForm.resetFields()
      loadDistributions(detail.id)
    } catch (e) {}
  }

  const handleDeleteDistribution = async (id: number) => {
    await distributionApi.delete(id)
    message.success('已删除')
    loadDistributions(detail.id)
  }

  const handleValidate = async (id: number) => {
    try {
      const res: any = await articleApi.validate(id)
      setValidateResult(res.data)
      message.success(`校验完成，得分：${res.data.score}分`)
      loadData()
    } catch (e) {}
  }

  // ========== 内容机会函数 ==========
  const loadOpportunities = async () => {
    setOppLoading(true)
    try {
      const res: any = await opportunityApi.list({ status: 'open' })
      setOpportunities(res.data.items || [])
    } catch (e) {} finally {
      setOppLoading(false)
    }
  }

  const handleScanOpportunities = async () => {
    setOppScanning(true)
    try {
      const res: any = await opportunityApi.scan()
      message.success(`扫描完成，新增 ${res.data.new} 个内容机会`)
      loadOpportunities()
    } catch (e) {} finally {
      setOppScanning(false)
    }
  }

  const handleDismissOpportunity = async (id: number) => {
    try {
      await opportunityApi.dismiss(id)
      message.success('已忽略该机会')
      loadOpportunities()
    } catch (e) {}
  }

  const handleGenerateFromOpportunity = async (opp: any) => {
    // 选中对应语义并生成文章模板
    setSelectedSemantic(opp.question_id)
    setTemplateLoading(true)
    try {
      const res: any = await templateApi.generateArticle(opp.question_id, opp.id)
      setTemplateData(res.data)
      message.success(`已基于内容机会生成文章（来源：${res.data.source === 'llm' ? 'LLM' : '模板'}）`)
      // 切换到内容创作Tab
      setActiveTab('create')
    } catch (e) {} finally {
      setTemplateLoading(false)
    }
  }

  // ========== 文章表格列（来自 Content.tsx）==========
  const columns = [
    {
      title: '标题', dataIndex: 'title', key: 'title',
      render: (text: string, record: any) => (
        <a onClick={() => handleView(record)} style={{ fontWeight: 500 }}>{text || '（无标题）'}</a>
      )
    },
    {
      title: '关联语义', dataIndex: 'semantic_id', key: 'semantic_id', width: 200, ellipsis: true,
      render: (id: number) => {
        const s = semantics.find(x => x.id === id)
        return s ? <span>{s.question}</span> : <span style={{ color: '#94A3B8' }}>-</span>
      }
    },
    {
      title: '平台', dataIndex: 'platform', key: 'platform', width: 100,
      render: (p: string) => <span className="geo-tag geo-tag-blue">{PUBLISH_PLATFORM_NAMES[p] || p}</span>
    },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (s: string) => s === 'published'
        ? <span className="geo-tag geo-tag-green">{ARTICLE_STATUS_NAMES[s] || s}</span>
        : <span className="geo-tag geo-tag-gray">{ARTICLE_STATUS_NAMES[s] || s}</span>
    },
    {
      title: '实体一致性', dataIndex: 'entity_consistent', key: 'entity_consistent', width: 100,
      render: (v: boolean) => v ? (
        <span className="geo-tag geo-tag-green"><CheckCircleOutlined /> 一致</span>
      ) : (
        <span className="geo-tag geo-tag-orange"><WarningOutlined /> 待优化</span>
      )
    },
    {
      title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 110,
      render: (t: string) => formatUtcDate(t)
    },
    {
      title: '操作', key: 'action', width: 240,
      render: (_: any, record: any) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleView(record)}>查看</Button>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>编辑</Button>
          <Button type="link" size="small" onClick={() => handleValidate(record.id)}>校验</Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      )
    }
  ]

  // 创作工作台：选中语义的数据
  const selectedSemanticData = semantics.find(s => s.id === selectedSemantic)

  return (
    <div>
      {/* ===== 页面标题栏 ===== */}
      <div className="page-title-bar">
        <div>
          <h2>内容中心</h2>
          <div className="page-desc">选择语义创作内容，管理所有产出文章</div>
        </div>
        <Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd} className="btn-primary-gradient">添加文章</Button>
          <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
        </Space>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'create',
            label: '智能创作',
            children: (
              <>
      {/* ===== 【智能创作】选语义 → AI生成文章 → 文章管理 ===== */}
      {/* 语义选择 */}
      <div className="geo-card" style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>🎨 智能创作</div>
        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 12 }}>
          基于语义问题，AI 一键生成定向文章（LLM 驱动，医疗合规）
        </Text>
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

      {/* AI 生成文章按钮（选中语义后显示） */}
      {selectedSemantic && (
        <div className="geo-card" style={{ marginBottom: 20, borderLeft: '3px solid #3B82F6' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div>
              <Title level={5} style={{ margin: 0, color: '#1D4ED8' }}>✨ AI 生成文章</Title>
              <Text type="secondary" style={{ fontSize: 12 }}>LLM 驱动，自动填充医生信息和医疗合规结构</Text>
            </div>
            <Button
              type="primary"
              size="large"
              icon={<ThunderboltOutlined />}
              onClick={handleGenerateTemplate}
              loading={templateLoading}
              className="btn-primary-gradient"
            >
              {templateData ? '重新生成' : '生成文章'}
            </Button>
          </div>
          {templateData ? (
            <div style={{ background: '#F8FAFC', padding: 16, borderRadius: 12, fontSize: 13, lineHeight: 1.8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <Tag color={templateData.source === 'llm' ? 'blue' : 'default'}>
                  来源：{templateData.source === 'llm' ? 'AI 生成' : '模板降级'}
                </Tag>
                <Space>
                  <Button onClick={handleCopyTemplate} icon={<FileTextOutlined />}>一键复制</Button>
                  <Button type="primary" onClick={handleSaveTemplateToArticle} className="btn-primary-gradient">保存到文章库</Button>
                </Space>
              </div>
              <div style={{ fontWeight: 600, marginBottom: 8, color: '#1D4ED8', fontSize: 15 }}>【标题】{templateData.title}</div>
              <div style={{ marginBottom: 8 }}><strong>【首段】</strong>{templateData.intro}</div>
              <div style={{ marginBottom: 8, whiteSpace: 'pre-wrap' }}><strong>【正文】</strong>{templateData.body}</div>
              <div style={{ marginBottom: 8 }}><strong>【文末】</strong>{templateData.conclusion}</div>
              <div style={{ color: '#6B7280' }}>
                <strong>【标签】</strong>
                {templateData.tags?.map((t: string, i: number) => (
                  <span key={i} className="geo-tag geo-tag-blue" style={{ marginRight: 6 }}>{t}</span>
                ))}
              </div>
            </div>
          ) : (
            <Empty description="点击上方「生成文章」按钮，AI 将基于语义问题自动生成" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </div>
      )}

      {/* ===== 【文章管理】 ===== */}
      <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>📚 文章管理</div>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 20 }}>
        <Col xs={8}>
          <div className="geo-card" style={{ padding: 20 }}>
            <Statistic title="文章总数" value={stats.total} valueStyle={{ fontWeight: 700 }} />
          </div>
        </Col>
        <Col xs={8}>
          <div className="geo-card" style={{ padding: 20 }}>
            <Statistic title="已发布" value={stats.published} valueStyle={{ color: '#10B981', fontWeight: 700 }} />
          </div>
        </Col>
        <Col xs={8}>
          <div className="geo-card" style={{ padding: 20 }}>
            <Statistic title="实体一致" value={stats.consistent} valueStyle={{ color: '#2563EB', fontWeight: 700 }} />
          </div>
        </Col>
      </Row>

      {/* 筛选 */}
      <div className="geo-card" style={{ marginBottom: 20 }}>
        <Space wrap>
          <Input
            placeholder="搜索标题"
            style={{ width: 200 }}
            value={filters.keyword}
            onChange={e => setFilters({ ...filters, keyword: e.target.value })}
            allowClear
          />
          <Select
            placeholder="关联语义"
            style={{ width: 280 }}
            value={filters.semantic_id || undefined}
            onChange={v => setFilters({ ...filters, semantic_id: v })}
            allowClear
            showSearch
            optionFilterProp="label"
            options={semantics.map(s => ({ value: s.id, label: s.question }))}
          />
          <Select
            placeholder="状态"
            style={{ width: 120 }}
            value={filters.status || undefined}
            onChange={v => setFilters({ ...filters, status: v })}
            allowClear
            options={[
              { value: 'draft', label: '草稿' },
              { value: 'published', label: '已发布' }
            ]}
          />
        </Space>
      </div>

      {/* 文章列表 */}
      <div className="geo-card">
        <Table
          dataSource={list}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            total,
            pageSize: 20,
            onChange: setPage,
            showTotal: (t) => `共 ${t} 条`
          }}
          locale={{ emptyText: '暂无文章，去上方创作工作台生成吧' }}
        />
      </div>
              </>
            ),
          },
          {
            key: 'tools',
            label: '创作工具',
            children: (
              <>
      {/* ===== 【创作工具】外部工具跳转 ===== */}
      <div style={{ background: '#FFFBEB', padding: '12px 16px', borderRadius: 8, marginBottom: 20 }}>
        <Text style={{ fontSize: 13, color: '#92400E' }}>
          💡 以下为外部创作工具，点击后将在新窗口打开。系统内置的 AI 文章生成请使用「智能创作」Tab。
        </Text>
      </div>

      <Row gutter={16}>
        <Col xs={24} md={12}>
          <div className="geo-card" style={{ height: '100%', borderLeft: '3px solid var(--primary)' }}>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
              <FileTextOutlined style={{ fontSize: 28, color: 'var(--primary)', marginRight: 12 }} />
              <div>
                <Title level={4} style={{ margin: 0 }}>生成文章工具</Title>
                <Text type="secondary">外部工具，问答式结构，AEO问句式标题</Text>
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
                <Title level={4} style={{ margin: 0 }}>生成视频工具</Title>
                <Text type="secondary">外部工具，口播/动画视频，多平台适配</Text>
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
              </>
            ),
          },
          {
            key: 'opportunity',
            label: <Badge count={opportunities.length} size="small" offset={[8, 0]}>内容机会</Badge>,
            children: (
              <>
      {/* ===== 内容机会 ===== */}
      {/* 顶部说明区 */}
      <div className="geo-card" style={{ marginBottom: 20, padding: '16px 20px' }}>
        <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>💡 内容机会是什么？</div>
        <Text style={{ fontSize: 13, color: '#475569', display: 'block', marginBottom: 12 }}>
          系统分析 AI 搜索数据后，告诉你「应该写什么文章」的建议。基于监测数据自动识别 GEO 优化机会，一键生成定向文章。
        </Text>
        <Row gutter={12}>
          <Col xs={24} md={8}>
            <div style={{ background: '#FEF2F2', padding: '10px 12px', borderRadius: 8 }}>
              <div style={{ color: '#DC2626', fontWeight: 600, fontSize: 13, marginBottom: 4 }}>🔴 AI未提及</div>
              <div style={{ fontSize: 12, color: '#7F1D1D' }}>AI回答里没提到这个医生，需要多写内容提升曝光</div>
            </div>
          </Col>
          <Col xs={24} md={8}>
            <div style={{ background: '#FFFBEB', padding: '10px 12px', borderRadius: 8 }}>
              <div style={{ color: '#D97706', fontWeight: 600, fontSize: 13, marginBottom: 4 }}>🟡 缺少引用</div>
              <div style={{ fontSize: 12, color: '#92400E' }}>提到了但没引用来源，需要发到可引用平台（知乎/公众号）</div>
            </div>
          </Col>
          <Col xs={24} md={8}>
            <div style={{ background: '#EFF6FF', padding: '10px 12px', borderRadius: 8 }}>
              <div style={{ color: '#2563EB', fontWeight: 600, fontSize: 13, marginBottom: 4 }}>🔵 排名靠后</div>
              <div style={{ fontSize: 12, color: '#1E40AF' }}>医生在AI推荐里排第3以后，需要优化文章质量提升排名</div>
            </div>
          </Col>
        </Row>
        <div style={{ marginTop: 12, fontSize: 12, color: '#64748B' }}>
          <strong>使用流程：</strong>① 去「数据中心」跑采集获取 AI 搜索数据 → ② 点「扫描机会」自动分析 → ③ 点「生成文章」AI 基于机会定向生成
        </div>
      </div>

      <div className="geo-card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div>
            <Title level={5} style={{ margin: 0 }}>内容机会列表</Title>
            <Text type="secondary" style={{ fontSize: 12 }}>共 {opportunities.length} 个待处理机会</Text>
          </div>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={loadOpportunities} loading={oppLoading}>刷新</Button>
            <Button type="primary" icon={<ThunderboltOutlined />} onClick={handleScanOpportunities} loading={oppScanning} className="btn-primary-gradient">
              扫描机会
            </Button>
          </Space>
        </div>
        {opportunities.length === 0 && !oppLoading ? (
          <div style={{ padding: '40px 20px', textAlign: 'center' }}>
            <Empty description={null} image={Empty.PRESENTED_IMAGE_SIMPLE} />
            <div style={{ fontSize: 15, fontWeight: 600, color: '#334155', marginBottom: 16 }}>暂无内容机会</div>
            <div style={{ fontSize: 13, color: '#64748B', marginBottom: 20, textAlign: 'left', maxWidth: 500, margin: '0 auto 20px' }}>
              <div style={{ marginBottom: 8 }}>📋 <strong>开始使用：</strong></div>
              <div style={{ marginBottom: 6 }}>第1步：去「数据中心」跑采集，获取 AI 搜索真实数据</div>
              <div style={{ marginBottom: 6 }}>第2步：回来点「扫描机会」，系统自动分析哪些问题需要写内容</div>
              <div>第3步：点「生成文章」，AI 基于机会定向生成</div>
            </div>
            <Space>
              <Button type="primary" onClick={handleScanOpportunities} loading={oppScanning} className="btn-primary-gradient">
                扫描机会
              </Button>
            </Space>
          </div>
        ) : (
        <Table
          dataSource={opportunities}
          rowKey="id"
          loading={oppLoading}
          pagination={false}
          columns={[
            {
              title: '机会类型', dataIndex: 'opportunity_type', width: 120,
              render: (t: string) => <Tag color={OPPORTUNITY_TYPE_COLORS[t] || 'default'}>{OPPORTUNITY_TYPE_NAMES[t] || t}</Tag>,
            },
            {
              title: '关联语义', dataIndex: 'question_text', key: 'question_text', ellipsis: true,
            },
            {
              title: '优先级', dataIndex: 'priority_score', width: 100,
              render: (s: number) => (
                <span style={{ fontWeight: 600, color: s >= 70 ? '#EF4444' : s >= 50 ? '#F59E0B' : '#6B7280' }}>
                  {s?.toFixed(0)}分
                </span>
              ),
            },
            {
              title: '证据（为什么推荐）', dataIndex: 'evidence', width: 200, ellipsis: true,
              render: (ev: any) => {
                if (!ev) return '-'
                if (ev.mention_rate !== undefined) return `提及率 ${ev.mention_rate}% (${ev.mentioned_count}/${ev.total_count})`
                if (ev.avg_rank !== undefined) return `平均排名 ${ev.avg_rank}`
                if (ev.citation_rate !== undefined) return `引用率 ${ev.citation_rate}%`
                return JSON.stringify(ev)
              },
            },
            {
              title: '建议（怎么做）', dataIndex: 'opportunity_type', width: 180,
              render: (t: string) => {
                const suggestions: Record<string, string> = {
                  missing_mention: '写一篇强调医生姓名+医院+科室的科普文章',
                  missing_citation: '把文章发布到知乎/公众号等AI可引用平台',
                  low_rank: '优化文章关键词匹配度，提升内容质量和权威性',
                }
                return <Text style={{ fontSize: 12, color: '#64748B' }}>{suggestions[t] || '-'}</Text>
              },
            },
            {
              title: '操作', width: 160,
              render: (_: any, record: any) => (
                <Space size="small">
                  <Button type="primary" size="small" icon={<FileTextOutlined />} onClick={() => handleGenerateFromOpportunity(record)} className="btn-primary-gradient">
                    生成文章
                  </Button>
                  <Popconfirm title="忽略该机会？" onConfirm={() => handleDismissOpportunity(record.id)}>
                    <Button size="small" icon={<BlockOutlined />}>忽略</Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
        )}
      </div>
              </>
            ),
          },
        ]}
      />

      {/* ===== 添加/编辑文章弹窗（来自 Content.tsx） ===== */}
      <Modal
        title={editMode ? '编辑文章' : '添加文章'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        okText="保存"
        cancelText="取消"
        width={640}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="文章标题" rules={[{ required: true }]}>
            <Input placeholder="请输入文章标题" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="semantic_id" label="关联语义" rules={[{ required: true }]}>
                <Select
                  showSearch
                  optionFilterProp="label"
                  options={semantics.map(s => ({ value: s.id, label: s.question }))}
                />
              </Form.Item>
            </Col>
            <Col span={6}>
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
            <Col span={6}>
              <Form.Item name="status" label="状态" initialValue="draft">
                <Select options={[
                  { value: 'draft', label: '草稿' },
                  { value: 'published', label: '已发布' }
                ]} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="content" label="文章内容/链接">
            <Input.TextArea rows={5} placeholder="粘贴文章全文或发布链接，用于实体一致性校验" />
          </Form.Item>
        </Form>
      </Modal>

      {/* ===== 文章详情抽屉（来自 Content.tsx） ===== */}
      <Drawer
        title="文章详情"
        placement="right"
        width={640}
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
      >
        {detail && (
          <div>
            <h3 style={{ marginBottom: 12, fontSize: 18, fontWeight: 700 }}>{detail.title || '（无标题）'}</h3>
            <Space style={{ marginBottom: 16 }} wrap>
              <span className="geo-tag geo-tag-blue">{PUBLISH_PLATFORM_NAMES[detail.platform] || detail.platform}</span>
              {detail.status === 'published' ? (
                <span className="geo-tag geo-tag-green">已发布</span>
              ) : (
                <span className="geo-tag geo-tag-gray">草稿</span>
              )}
              {detail.entity_consistent ? (
                <span className="geo-tag geo-tag-green"><CheckCircleOutlined /> 实体一致</span>
              ) : (
                <span className="geo-tag geo-tag-orange"><WarningOutlined /> 待优化</span>
              )}
            </Space>

            <Button
              type="primary"
              size="small"
              style={{ marginBottom: 16 }}
              className="btn-primary-gradient"
              onClick={() => handleValidate(detail.id)}
            >
              重新校验实体一致性
            </Button>

            {validateResult && (
              <div style={{ background: '#EFF6FF', padding: 16, borderRadius: 12, marginBottom: 16 }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: validateResult.passed ? '#10B981' : '#F59E0B' }}>
                  {validateResult.score}分
                </div>
                <div style={{ fontSize: 12, color: '#64748B', marginBottom: 8 }}>
                  {validateResult.passed ? '实体一致性校验通过' : '存在需要优化的问题'}
                </div>
                {validateResult.issues.map((issue: any, idx: number) => (
                  <div key={idx} style={{ marginTop: 8, padding: '8px 12px', background: '#fff', borderRadius: 8 }}>
                    <div style={{ fontWeight: 500, color: issue.level === 'error' ? '#EF4444' : issue.level === 'warning' ? '#F59E0B' : '#2563EB' }}>
                      [{issue.level}] {issue.field}
                    </div>
                    <div style={{ fontSize: 13, marginTop: 2 }}>{issue.message}</div>
                    <div style={{ fontSize: 12, color: '#64748B', marginTop: 2 }}>建议：{issue.suggestion}</div>
                  </div>
                ))}
              </div>
            )}

            <h4 style={{ marginBottom: 12, fontSize: 15, fontWeight: 600 }}>文章内容</h4>
            <div style={{
              background: '#F8FAFC',
              padding: 16,
              borderRadius: 12,
              lineHeight: 1.8,
              fontSize: 13,
              maxHeight: 400,
              overflow: 'auto',
              whiteSpace: 'pre-wrap'
            }}>
              {detail.content || '暂无内容'}
            </div>

            {/* 分发记录 */}
            <h4 style={{ margin: '20px 0 12px', fontSize: 15, fontWeight: 600 }}>
              分发记录 <span className="geo-tag geo-tag-blue">{distributions.length} 个平台</span>
            </h4>
            <div style={{ background: '#EFF6FF', padding: 12, borderRadius: 12, marginBottom: 12 }}>
              <Form form={distForm} layout="inline" style={{ marginBottom: 12 }}>
                <Form.Item name="platform" label="平台" initialValue="wechat" rules={[{ required: true }]}>
                  <Select style={{ width: 140 }} optionFilterProp="label">
                    {[1, 2, 3].map(tier => (
                      <Select.OptGroup key={tier} label={tier === 1 ? 'AI高优先' : tier === 2 ? '医疗权威' : '补充收录'}>
                        {PUBLISH_PLATFORMS.filter(p => p.tier === tier).map(p => (
                          <Select.Option key={p.code} value={p.code} label={p.name}>{p.name}</Select.Option>
                        ))}
                      </Select.OptGroup>
                    ))}
                  </Select>
                </Form.Item>
                <Form.Item name="publish_url" label="链接">
                  <Input placeholder="发布后URL" style={{ width: 200 }} />
                </Form.Item>
                <Form.Item name="note" label="备注">
                  <Input placeholder="备注" style={{ width: 120 }} />
                </Form.Item>
                <Form.Item>
                  <Button type="primary" size="small" onClick={handleAddDistribution} className="btn-primary-gradient">添加</Button>
                </Form.Item>
              </Form>
              {distributions.length === 0 ? (
                <div style={{ color: '#94A3B8', fontSize: 13, textAlign: 'center', padding: 8 }}>暂无分发记录</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {distributions.map((d: any) => (
                    <div key={d.id} style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      background: '#fff', padding: '8px 12px', borderRadius: 8, fontSize: 13
                    }}>
                      <div>
                        <span className="geo-tag geo-tag-blue">{PUBLISH_PLATFORM_NAMES[d.platform] || d.platform}</span>
                        {d.publish_url && (
                          <a href={d.publish_url} target="_blank" rel="noreferrer" style={{ marginRight: 8, marginLeft: 8 }}>查看链接</a>
                        )}
                        {d.note && <span style={{ color: '#64748B' }}>{d.note}</span>}
                      </div>
                      <Popconfirm title="确定删除？" onConfirm={() => handleDeleteDistribution(d.id)}>
                        <Button type="link" size="small" danger icon={<DeleteOutlined />} />
                      </Popconfirm>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </Drawer>
    </div>
  )
}

export default ContentHub
