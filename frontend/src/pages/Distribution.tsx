import { useState, useEffect } from 'react'
import { formatUtcTime } from '@/utils/time'
import {
  Table, Button, Space, Tag, Modal, Form, Select, Input,
  message, Popconfirm, Statistic, Row, Col, Drawer, Descriptions,
  Timeline
} from 'antd'
import {
  PlusOutlined, ReloadOutlined, EyeOutlined, CheckOutlined,
  ClockCircleOutlined, SyncOutlined, DeleteOutlined, LinkOutlined,
  FileTextOutlined, BarChartOutlined, CloseOutlined
} from '@ant-design/icons'
import { distributionApi, articleApi } from '@/api'
import { PUBLISH_PLATFORMS, PUBLISH_PLATFORM_NAMES } from '@/store/useStore'
import EffectTracker from '@/components/EffectTracker'

const { TextArea } = Input

// 状态配置
const STATUS_CONFIG: Record<string, { label: string; color: string; icon: any }> = {
  draft: { label: '草稿', color: 'default', icon: FileTextOutlined },
  scheduled: { label: '已排期', color: 'blue', icon: ClockCircleOutlined },
  processing: { label: '发布中', color: 'processing', icon: SyncOutlined },
  published: { label: '已发布', color: 'success', icon: CheckOutlined },
  failed: { label: '失败', color: 'error', icon: CloseOutlined },
  removed: { label: '已移除', color: 'default', icon: DeleteOutlined },
}

// 状态流转图
const STATUS_FLOW = ['draft', 'scheduled', 'processing', 'published']

const Distribution = () => {
  const [list, setList] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [articles, setArticles] = useState<any[]>([])
  const [createModal, setCreateModal] = useState(false)
  const [detailDrawer, setDetailDrawer] = useState(false)
  const [currentRecord, setCurrentRecord] = useState<any>(null)
  const [effectVisible, setEffectVisible] = useState(false)
  const [form] = Form.useForm()
  const [filters, setFilters] = useState({ status: '' as string, platform: '' as string })

  useEffect(() => {
    loadArticles()
    loadList()
  }, [filters])

  const loadArticles = async () => {
    try {
      const res: any = await articleApi.getList({ page_size: 100 })
      setArticles(res.data.items || res.data || [])
    } catch (e) {}
  }

  const loadList = async () => {
    setLoading(true)
    try {
      const params: any = {}
      if (filters.status) params.status = filters.status
      if (filters.platform) params.platform = filters.platform
      const res: any = await distributionApi.getList(params)
      setList(res.data.items || [])
    } catch (e) {
      // 拦截器已提示
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (values: any) => {
    try {
      await distributionApi.create({
        article_id: values.article_id,
        platform: values.platform,
        status: values.status || 'draft',
        publish_url: values.publish_url || '',
        note: values.note || '',
      })
      message.success('创建发布记录成功')
      setCreateModal(false)
      form.resetFields()
      loadList()
    } catch (e) {
      // 拦截器已提示
    }
  }

  const handleStatusUpdate = async (record: any, status: string, publish_url?: string) => {
    try {
      await distributionApi.updateStatus(record.id, { status, publish_url })
      message.success(`状态已更新为「${STATUS_CONFIG[status]?.label}」`)
      loadList()
    } catch (e: any) {
      message.error('状态更新失败，请稍后重试')
    }
  }

  const handleMarkPublished = (record: any) => {
    Modal.confirm({
      title: '标记为已发布',
      content: (
        <div>
          <p style={{ marginBottom: 8 }}>请确认已在「{PUBLISH_PLATFORM_NAMES[record.platform] || record.platform}」手动发布了这篇文章。</p>
          <Input
            placeholder="粘贴发布后的URL（可选，用于效果追踪）"
            id="publish_url_input"
            style={{ marginTop: 8 }}
          />
        </div>
      ),
      okText: '确认已发布',
      cancelText: '取消',
      onOk: () => {
        const url = (document.getElementById('publish_url_input') as HTMLInputElement)?.value || ''
        handleStatusUpdate(record, 'published', url)
      },
    })
  }

  const handleRetry = async (record: any) => {
    try {
      await distributionApi.retry(record.id)
      message.success('已重新加入发布队列')
      loadList()
    } catch (e) {
      message.error('重试失败')
    }
  }

  const handleViewDetail = (record: any) => {
    setCurrentRecord(record)
    setDetailDrawer(true)
  }

  // 统计
  const stats = {
    draft: list.filter(r => r.status === 'draft').length,
    scheduled: list.filter(r => r.status === 'scheduled').length,
    processing: list.filter(r => r.status === 'processing').length,
    published: list.filter(r => r.status === 'published').length,
    failed: list.filter(r => r.status === 'failed').length,
  }

  const columns = [
    {
      title: '文章标题', dataIndex: 'article_title', key: 'article_title',
      ellipsis: true, width: 250,
      render: (text: string, record: any) => (
        <a onClick={() => handleViewDetail(record)} style={{ fontWeight: 500 }}>
          {text || `文章#${record.article_id}`}
        </a>
      ),
    },
    {
      title: '关联语义', dataIndex: 'semantic_question', key: 'semantic_question',
      ellipsis: true, width: 200,
      render: (text: string) => <span style={{ color: '#64748B', fontSize: 12 }}>{text || '-'}</span>,
    },
    {
      title: '平台', dataIndex: 'platform', key: 'platform', width: 120,
      render: (p: string) => {
        const platform = PUBLISH_PLATFORMS.find((x: any) => x.code === p)
        return <Tag color={platform?.tier === 1 ? 'red' : platform?.tier === 2 ? 'orange' : 'default'}>
          {platform?.name || p}
        </Tag>
      },
    },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (status: string) => {
        const config = STATUS_CONFIG[status]
        const Icon = config?.icon || FileTextOutlined
        return <Tag color={config?.color} icon={<Icon />}>{config?.label || status}</Tag>
      },
    },
    {
      title: '排期时间', dataIndex: 'scheduled_at', key: 'scheduled_at', width: 160,
      render: (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-',
    },
    {
      title: '发布时间', dataIndex: 'published_at', key: 'published_at', width: 160,
      render: (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作', key: 'action', width: 280, fixed: 'right' as const,
      render: (_: any, record: any) => {
        const actions = []
        // 草稿 → 排期
        if (record.status === 'draft') {
          actions.push(
            <Button key="schedule" size="small" icon={<ClockCircleOutlined />} onClick={() => handleStatusUpdate(record, 'scheduled')}>
              排期
            </Button>
          )
        }
        // 已排期 → 开始发布
        if (record.status === 'scheduled') {
          actions.push(
            <Button key="start" size="small" type="primary" icon={<SyncOutlined />} onClick={() => handleStatusUpdate(record, 'processing')}>
              开始发布
            </Button>
          )
        }
        // 发布中 → 标记已发布
        if (record.status === 'processing') {
          actions.push(
            <Button key="publish" size="small" type="primary" icon={<CheckOutlined />} onClick={() => handleMarkPublished(record)}>
              标记已发布
            </Button>
          )
        }
        // 失败 → 重试
        if (record.status === 'failed') {
          actions.push(
            <Button key="retry" size="small" type="primary" icon={<SyncOutlined />} onClick={() => handleRetry(record)}>
              重试
            </Button>
          )
        }
        // 已发布 → 查看效果
        if (record.status === 'published') {
          actions.push(
            <Button key="effect" size="small" icon={<BarChartOutlined />} onClick={() => { setCurrentRecord(record); setEffectVisible(true) }}>
              效果追踪
            </Button>
          )
        }
        // 查看详情
        actions.push(
          <Button key="detail" size="small" icon={<EyeOutlined />} onClick={() => handleViewDetail(record)}>
            详情
          </Button>
        )
        // 草稿可删除
        if (record.status === 'draft') {
          actions.push(
            <Popconfirm key="delete" title="确定删除这条发布记录？" onConfirm={async () => {
              try { await distributionApi.delete(record.id); message.success('已删除'); loadList() }
              catch (e) { message.error('删除失败') }
            }}>
              <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
            </Popconfirm>
          )
        }
        return <Space size="small" wrap>{actions}</Space>
      },
    },
  ]

  return (
    <div>
      <div className="page-title-bar">
        <div>
          <h2>发布管理</h2>
          <div className="page-desc">管理文章的多平台发布排期、状态追踪和效果验证</div>
        </div>
        <Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModal(true)} className="btn-primary-gradient">
            新建发布
          </Button>
          <Button icon={<ReloadOutlined />} onClick={loadList}>刷新</Button>
        </Space>
      </div>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 20 }}>
        <Col xs={12} md={4}>
          <div className="geo-card" style={{ padding: 16 }}>
            <Statistic title="草稿" value={stats.draft} valueStyle={{ color: '#94A3B8' }} />
          </div>
        </Col>
        <Col xs={12} md={4}>
          <div className="geo-card" style={{ padding: 16 }}>
            <Statistic title="已排期" value={stats.scheduled} valueStyle={{ color: '#3B82F6' }} />
          </div>
        </Col>
        <Col xs={12} md={4}>
          <div className="geo-card" style={{ padding: 16 }}>
            <Statistic title="发布中" value={stats.processing} valueStyle={{ color: '#F59E0B' }} />
          </div>
        </Col>
        <Col xs={12} md={4}>
          <div className="geo-card" style={{ padding: 16 }}>
            <Statistic title="已发布" value={stats.published} valueStyle={{ color: '#10B981' }} />
          </div>
        </Col>
        <Col xs={12} md={4}>
          <div className="geo-card" style={{ padding: 16 }}>
            <Statistic title="失败" value={stats.failed} valueStyle={{ color: '#EF4444' }} />
          </div>
        </Col>
      </Row>

      {/* 筛选 */}
      <div className="geo-card" style={{ marginBottom: 20, padding: '12px 16px' }}>
        <Space wrap>
          <Select
            placeholder="状态筛选"
            style={{ width: 140 }}
            value={filters.status || undefined}
            onChange={(v) => setFilters({ ...filters, status: v || '' })}
            allowClear
          >
            {Object.entries(STATUS_CONFIG).map(([key, config]) => (
              <Select.Option key={key} value={key}>{config.label}</Select.Option>
            ))}
          </Select>
          <Select
            placeholder="平台筛选"
            style={{ width: 160 }}
            value={filters.platform || undefined}
            onChange={(v) => setFilters({ ...filters, platform: v || '' })}
            allowClear
            showSearch
            optionFilterProp="label"
          >
            {PUBLISH_PLATFORMS.map((p: any) => (
              <Select.Option key={p.code} value={p.code} label={p.name}>{p.name}</Select.Option>
            ))}
          </Select>
        </Space>
      </div>

      {/* 状态流转图 */}
      <div className="geo-card" style={{ marginBottom: 20, padding: '12px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 13, color: '#64748B', marginRight: 8 }}>发布流程：</span>
          {STATUS_FLOW.map((status, idx) => (
            <span key={status} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Tag color={STATUS_CONFIG[status].color}>{STATUS_CONFIG[status].label}</Tag>
              {idx < STATUS_FLOW.length - 1 && <span style={{ color: '#CBD5E1' }}>→</span>}
            </span>
          ))}
          <span style={{ color: '#CBD5E1', margin: '0 4px' }}>→</span>
          <Tag color="error">失败（可重试）</Tag>
        </div>
      </div>

      {/* 列表 */}
      <div className="geo-card">
        <Table
          dataSource={list}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }}
          scroll={{ x: 1200 }}
          locale={{ emptyText: '暂无发布记录，点击「新建发布」开始管理文章发布' }}
        />
      </div>

      {/* 新建发布弹窗 */}
      <Modal
        title="新建发布记录"
        open={createModal}
        onCancel={() => { setCreateModal(false); form.resetFields() }}
        onOk={() => form.submit()}
        okText="创建"
        cancelText="取消"
        width={560}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="article_id" label="选择文章" rules={[{ required: true, message: '请选择文章' }]}>
            <Select
              placeholder="请选择要发布的文章"
              showSearch
              optionFilterProp="label"
              options={articles.map((a: any) => ({ value: a.id, label: a.title || `文章#${a.id}` }))}
            />
          </Form.Item>
          <Form.Item name="platform" label="发布平台" rules={[{ required: true, message: '请选择平台' }]}>
            <Select placeholder="请选择发布平台" showSearch optionFilterProp="label">
              {PUBLISH_PLATFORMS.map((p: any) => (
                <Select.Option key={p.code} value={p.code} label={p.name}>
                  <span>{p.name}</span>
                  <span style={{ color: '#999', fontSize: 12, marginLeft: 8 }}>{p.tierLabel}</span>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="status" label="初始状态" initialValue="draft">
            <Select>
              <Select.Option value="draft">草稿</Select.Option>
              <Select.Option value="scheduled">已排期</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="publish_url" label="发布链接（可选）">
            <Input placeholder="已发布的话可粘贴链接" prefix={<LinkOutlined />} />
          </Form.Item>
          <Form.Item name="note" label="备注（可选）">
            <TextArea rows={2} placeholder="备注信息" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 详情抽屉 */}
      <Drawer
        title="发布详情"
        placement="right"
        width={500}
        open={detailDrawer}
        onClose={() => setDetailDrawer(false)}
      >
        {currentRecord && (
          <div>
            <Descriptions title="基本信息" column={1} bordered size="small" style={{ marginBottom: 20 }}>
              <Descriptions.Item label="文章标题">{currentRecord.article_title || '-'}</Descriptions.Item>
              <Descriptions.Item label="关联语义">{currentRecord.semantic_question || '-'}</Descriptions.Item>
              <Descriptions.Item label="发布平台">{PUBLISH_PLATFORM_NAMES[currentRecord.platform] || currentRecord.platform}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={STATUS_CONFIG[currentRecord.status]?.color}>
                  {STATUS_CONFIG[currentRecord.status]?.label}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="发布模式">{currentRecord.publish_mode === 'manual' ? '手动发布' : '自动发布'}</Descriptions.Item>
              <Descriptions.Item label="重试次数">{currentRecord.retry_count}</Descriptions.Item>
              <Descriptions.Item label="创建时间">{currentRecord.created_at ? formatUtcTime(currentRecord.created_at) : '-'}</Descriptions.Item>
              <Descriptions.Item label="排期时间">{currentRecord.scheduled_at ? new Date(currentRecord.scheduled_at).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
              <Descriptions.Item label="发布时间">{currentRecord.published_at ? new Date(currentRecord.published_at).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
              <Descriptions.Item label="发布链接">
                {currentRecord.publish_url ? (
                  <a href={currentRecord.publish_url} target="_blank" rel="noreferrer">{currentRecord.publish_url}</a>
                ) : '-'}
              </Descriptions.Item>
              {currentRecord.failed_reason && (
                <Descriptions.Item label="失败原因"><span style={{ color: '#EF4444' }}>{currentRecord.failed_reason}</span></Descriptions.Item>
              )}
              {currentRecord.note && (
                <Descriptions.Item label="备注">{currentRecord.note}</Descriptions.Item>
              )}
            </Descriptions>

            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>状态流转时间线</div>
              <Timeline
                items={[
                  { color: 'blue', children: `创建记录 - ${currentRecord.created_at ? formatUtcTime(currentRecord.created_at) : '-'}` },
                  currentRecord.scheduled_at && { color: 'blue', children: `排期 - ${new Date(currentRecord.scheduled_at).toLocaleString('zh-CN')}` },
                  currentRecord.published_at && { color: 'green', children: `发布完成 - ${new Date(currentRecord.published_at).toLocaleString('zh-CN')}` },
                  currentRecord.status === 'failed' && { color: 'red', children: `发布失败 - ${currentRecord.failed_reason || '未知原因'}` },
                ].filter(Boolean)}
              />
            </div>

            {currentRecord.status === 'published' && (
              <Button type="primary" block icon={<BarChartOutlined />} onClick={() => { setEffectVisible(true) }} className="btn-primary-gradient">
                查看内容效果追踪
              </Button>
            )}
          </div>
        )}
      </Drawer>

      {/* 效果追踪抽屉（T12组件） */}
      <EffectTracker
        visible={effectVisible}
        onClose={() => setEffectVisible(false)}
        distribution={currentRecord}
        onRefresh={loadList}
      />
    </div>
  )
}

export default Distribution


