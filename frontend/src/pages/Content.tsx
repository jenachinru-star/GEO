import { useEffect, useState } from 'react'
import {
  Row, Col, Table, Tag, Button, Space, Input, Select,
  Modal, Form, Drawer, message, Popconfirm, Statistic
} from 'antd'
import {
  PlusOutlined, ReloadOutlined, DeleteOutlined,
  EyeOutlined, EditOutlined, CheckCircleOutlined, WarningOutlined
} from '@ant-design/icons'
import { articleApi, semanticApi, distributionApi } from '@/api'
import { PUBLISH_PLATFORMS, PUBLISH_PLATFORM_NAMES, ARTICLE_STATUS_NAMES } from '@/store/useStore'

const Content = () => {
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
  const [semantics, setSemantics] = useState<any[]>([])
  const [stats, setStats] = useState({ total: 0, published: 0, consistent: 0 })
  const [distributions, setDistributions] = useState<any[]>([])
  const [distForm] = Form.useForm()

  const loadSemantics = async () => {
    try {
      const res: any = await semanticApi.getList({ page_size: 100 })
      setSemantics(res.data.items || res.data || [])
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
      // 统计
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
  }, [])

  useEffect(() => {
    loadData()
  }, [filters, page])

  const handleAdd = () => {
    setEditMode(false)
    setEditId(null)
    form.resetFields()
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
      render: (t: string) => new Date(t).toLocaleDateString()
    },
    {
      title: '操作', key: 'action', width: 180,
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

  return (
    <div>
      <div className="page-title-bar">
        <div>
          <h2>我的文章</h2>
          <div className="page-desc">管理所有语义下产出的文章，追踪实体一致性</div>
        </div>
        <Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd} className="btn-primary-gradient">添加文章</Button>
          <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
        </Space>
      </div>

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

      {/* 列表 */}
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
          locale={{ emptyText: '暂无文章，去创作中心生成吧' }}
        />
      </div>

      {/* 添加/编辑弹窗 */}
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

      {/* 详情抽屉 */}
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

export default Content
