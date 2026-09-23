import { useEffect, useState } from 'react'
import {
  Row, Col, Card, Table, Tag, Button, Space, Input, Select,
  Modal, Form, Drawer, message, Popconfirm, Tree, Empty
} from 'antd'
import {
  PlusOutlined, ReloadOutlined, DeleteOutlined,
  EditOutlined, SearchOutlined, BookOutlined, SyncOutlined
} from '@ant-design/icons'
import { knowledgeApi } from '@/api'
import { CATEGORY_NAMES, useAppStore } from '@/store/useStore'
import { formatUtcTime } from '@/utils/time'

const categoryTree = [
  { title: '全部', key: '' },
  { title: '公司简介', key: 'company' },
  { title: '业务线', key: 'business' },
  { title: '技术优势', key: 'tech' },
  { title: '项目案例', key: 'case' },
  { title: '资质专利', key: 'qualification' },
  { title: '团队信息', key: 'team' }
]

const Knowledge = () => {
  const [list, setList] = useState<any[]>([])
  const { user } = useAppStore()
  const isAdmin = user?.role === 'admin'
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [drawerVisible, setDrawerVisible] = useState(false)
  const [detail, setDetail] = useState<any>(null)
  const [editing, setEditing] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState('')
  const [searchKeyword, setSearchKeyword] = useState('')
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [searching, setSearching] = useState(false)
  const [form] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const res: any = await knowledgeApi.getList({
        category: selectedCategory || undefined,
        keyword: searchKeyword || undefined,
        page_size: 100
      })
      setList(res.data.items)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [selectedCategory, searchKeyword])

  const handleSearch = async () => {
    if (!searchKeyword.trim()) return
    setSearching(true)
    try {
      const res: any = await knowledgeApi.search(searchKeyword)
      setSearchResults(res.data)
    } finally {
      setSearching(false)
    }
  }

  const handleAdd = async () => {
    try {
      const values = await form.validateFields()
      await knowledgeApi.create(values)
      message.success('添加成功')
      setModalVisible(false)
      form.resetFields()
      loadData()
    } catch (e) {}
  }

  const handleEdit = async () => {
    try {
      const values = await form.validateFields()
      await knowledgeApi.update(detail.id, values)
      message.success('更新成功')
      setEditing(false)
      setDrawerVisible(false)
      loadData()
    } catch (e) {}
  }

  const handleDelete = async (id: number) => {
    await knowledgeApi.delete(id)
    message.success('删除成功')
    loadData()
  }

  const handleView = (record: any) => {
    setDetail(record)
    setEditing(false)
    setDrawerVisible(true)
    form.setFieldsValue(record)
  }

  const handleRebuild = async () => {
    await knowledgeApi.rebuildEmbeddings()
    message.success('向量重建完成')
  }

  const columns = [
    {
      title: '标题', dataIndex: 'title', key: 'title',
      render: (text: string, record: any) => (
        <a onClick={() => handleView(record)} style={{ fontWeight: 500 }}>
          <BookOutlined style={{ marginRight: 6, color: '#0EA5E9' }} />
          {text}
        </a>
      )
    },
    {
      title: '分类', dataIndex: 'category', key: 'category', width: 100,
      render: (c: string) => <Tag color="purple">{CATEGORY_NAMES[c] || c}</Tag>
    },
    {
      title: '级别', dataIndex: 'level', key: 'level', width: 80,
      render: (l: string) => {
        const colorMap: Record<string, string> = { public: 'green', internal: 'blue', confidential: 'red' }
        const textMap: Record<string, string> = { public: '公开', internal: '内部', confidential: '涉密' }
        return <Tag color={colorMap[l]}>{textMap[l] || l}</Tag>
      }
    },
    { title: '版本', dataIndex: 'version', key: 'version', width: 60 },
    {
      title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', width: 170,
      render: (t: string) => t ? formatUtcTime(t) : '-'
    },
    {
      title: '操作', key: 'action', width: 120,
      render: (_: any, record: any) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleView(record)}>编辑</Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      )
    }
  ]

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>统一知识库</h2>
          <div className="page-desc">公司唯一信息源，支撑AI问答与内容生成</div>
        </div>
        <Space>
          <Button icon={<SyncOutlined />} onClick={handleRebuild}>重建向量</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { form.resetFields(); setModalVisible(true) }}>
            添加条目
          </Button>
        </Space>
      </div>

      <Row gutter={16}>
        {/* 左侧分类树 */}
        <Col xs={24} sm={6} md={5}>
          <div className="geo-card" style={{ padding: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 12, fontSize: 14 }}>知识分类</div>
            <Tree
              selectedKeys={[selectedCategory]}
              onSelect={(keys) => setSelectedCategory(keys[0] as string || '')}
              treeData={categoryTree}
              defaultExpandAll
            />
          </div>
        </Col>

        {/* 右侧内容区 */}
        <Col xs={24} sm={18} md={19}>
          {/* 语义搜索框 */}
          <div className="geo-card" style={{ marginBottom: 16 }}>
            <Space.Compact style={{ width: '100%' }}>
              <Input
                size="large"
                placeholder="语义搜索知识库，例如：公司的核心技术是什么？"
                prefix={<SearchOutlined style={{ color: '#94A3B8' }} />}
                value={searchKeyword}
                onChange={e => setSearchKeyword(e.target.value)}
                onPressEnter={handleSearch}
                allowClear
                onClear={() => setSearchResults([])}
              />
              <Button type="primary" size="large" onClick={handleSearch} loading={searching}>
                语义搜索
              </Button>
            </Space.Compact>

            {/* 搜索结果 */}
            {searchResults.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div style={{ fontSize: 13, color: '#64748B', marginBottom: 8 }}>
                  找到 {searchResults.length} 条相关知识：
                </div>
                {searchResults.map((item: any, idx: number) => (
                  <div
                    key={idx}
                    style={{
                      padding: 12,
                      background: '#F0F9FF',
                      borderRadius: 8,
                      marginBottom: 8,
                      cursor: 'pointer'
                    }}
                    onClick={() => handleView(item)}
                  >
                    <div style={{ fontWeight: 500, marginBottom: 4 }}>
                      {item.title}
                      <Tag style={{ marginLeft: 8 }} color="blue">相关度 {(item.score * 100).toFixed(0)}%</Tag>
                    </div>
                    <div style={{ fontSize: 12, color: '#64748B', lineHeight: 1.6 }}>
                      {item.content?.slice(0, 150)}...
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 知识列表 */}
          <div className="geo-card">
            <Table
              dataSource={list}
              columns={columns}
              rowKey="id"
              loading={loading}
              pagination={{ pageSize: 15 }}
              locale={{ emptyText: <Empty description="暂无知识条目" /> }}
            />
          </div>
        </Col>
      </Row>

      {/* 添加弹窗 */}
      <Modal
        title="添加知识条目"
        open={modalVisible}
        onOk={handleAdd}
        onCancel={() => setModalVisible(false)}
        okText="添加"
        cancelText="取消"
        width={640}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="标题" rules={[{ required: true }]}>
            <Input placeholder="例如：公司核心技术" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="category" label="分类" initialValue="company">
                <Select options={[
                  { value: 'company', label: '公司简介' },
                  { value: 'business', label: '业务线' },
                  { value: 'tech', label: '技术优势' },
                  { value: 'case', label: '项目案例' },
                  { value: 'qualification', label: '资质专利' },
                  { value: 'team', label: '团队信息' }
                ]} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="level" label="级别" initialValue="public">
                <Select options={[
                  { value: 'public', label: '公开' },
                  { value: 'internal', label: '内部' },
                  { value: 'confidential', label: '涉密' }
                ]} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="content" label="内容" rules={[{ required: true }]}>
            <Input.TextArea rows={8} placeholder="请输入知识内容详情" />
          </Form.Item>
          <Form.Item name="tags" label="标签">
            <Input placeholder="多个标签用逗号分隔" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑/查看抽屉 */}
      <Drawer
        title={editing ? '编辑知识条目' : '知识详情'}
        placement="right"
        width={640}
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
        extra={!editing && (
          <Button type="primary" icon={<EditOutlined />} onClick={() => setEditing(true)}>
            编辑
          </Button>
        )}
      >
        {detail && (
          <div>
            {editing ? (
              <Form form={form} layout="vertical">
                <Form.Item name="title" label="标题" rules={[{ required: true }]}>
                  <Input />
                </Form.Item>
                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item name="category" label="分类">
                      <Select options={[
                        { value: 'company', label: '公司简介' },
                        { value: 'business', label: '业务线' },
                        { value: 'tech', label: '技术优势' },
                        { value: 'case', label: '项目案例' },
                        { value: 'qualification', label: '资质专利' },
                        { value: 'team', label: '团队信息' }
                      ]} />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="level" label="级别">
                      <Select options={[
                        { value: 'public', label: '公开' },
                        { value: 'internal', label: '内部' },
                        { value: 'confidential', label: '涉密（仅管理员）', disabled: !isAdmin }
                      ]} />
                    </Form.Item>
                  </Col>
                </Row>
                <Form.Item name="content" label="内容" rules={[{ required: true }]}>
                  <Input.TextArea rows={10} />
                </Form.Item>
                <Form.Item name="tags" label="标签">
                  <Input />
                </Form.Item>
                <Space>
                  <Button type="primary" onClick={handleEdit}>保存</Button>
                  <Button onClick={() => setEditing(false)}>取消</Button>
                </Space>
              </Form>
            ) : (
              <div>
                <h3 style={{ marginBottom: 12 }}>{detail.title}</h3>
                <Space style={{ marginBottom: 16 }}>
                  <Tag color="purple">{CATEGORY_NAMES[detail.category] || detail.category}</Tag>
                  <Tag color={detail.level === 'public' ? 'green' : detail.level === 'internal' ? 'blue' : 'red'}>
                    {detail.level === 'public' ? '公开' : detail.level === 'internal' ? '内部' : '涉密'}
                  </Tag>
                  <span style={{ color: '#64748B', fontSize: 12 }}>版本 v{detail.version}</span>
                </Space>
                <div style={{
                  background: '#F8FAFC',
                  padding: 16,
                  borderRadius: 8,
                  lineHeight: 1.8,
                  fontSize: 14,
                  whiteSpace: 'pre-wrap'
                }}>
                  {detail.content}
                </div>
              </div>
            )}
          </div>
        )}
      </Drawer>
    </div>
  )
}

export default Knowledge
