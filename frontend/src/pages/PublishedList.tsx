import { useState, useEffect } from 'react'
import { Card, Input, Button, Space, Typography, Tag, Empty, Spin, Modal, Form, message, Popconfirm } from 'antd'
import { PlusOutlined, SearchOutlined, EditOutlined, DeleteOutlined, EyeOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { assetApi } from '@/api/asset'
import { marked } from 'marked'

const { Title, Text, Paragraph } = Typography
const { TextArea } = Input

const PublishedList = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState<any[]>([])
  const [keyword, setKeyword] = useState('')

  // 编辑模态框
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [editingItem, setEditingItem] = useState<any>(null)
  const [editForm, setEditForm] = useState({ title: '', content: '', category: '', tags: '' })
  const [saving, setSaving] = useState(false)

  const fetchData = async (kw = '') => {
    setLoading(true)
    try {
      const res: any = await assetApi.getPublishedList({ keyword: kw || undefined })
      setItems(res.data.items || [])
    } catch (e) {
      message.error('加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleEdit = async (item: any) => {
    try {
      const res: any = await assetApi.getPublishedDetail(item.id)
      setEditingItem(res.data)
      setEditForm({
        title: res.data.title,
        content: res.data.content,
        category: res.data.category,
        tags: res.data.tags,
      })
      setEditModalOpen(true)
    } catch (e) {
      message.error('加载详情失败')
    }
  }

  const handleSave = async () => {
    if (!editForm.title.trim()) {
      message.warning('请填写标题')
      return
    }
    setSaving(true)
    try {
      await assetApi.updatePublished(editingItem.id, {
        ...editForm,
        status: 'published',  // 保存即发布
      })
      message.success('发布成功')
      setEditModalOpen(false)
      fetchData(keyword)
    } catch (e) {
      message.error('保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await assetApi.deletePublished(id)
      message.success('已删除')
      fetchData(keyword)
    } catch (e) {
      message.error('删除失败')
    }
  }

  const getStatusTag = (status: string) => {
    const map: Record<string, { color: string; label: string }> = {
      draft: { color: 'orange', label: '草稿' },
      published: { color: 'green', label: '已发布' },
      archived: { color: 'default', label: '已归档' },
    }
    const s = map[status] || { color: 'default', label: status }
    return <Tag color={s.color}>{s.label}</Tag>
  }

  return (
    <div style={{ padding: '24px', maxWidth: 1000, margin: '0 auto' }}>
      {/* 顶部 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>科普发布中心</Title>
        <Space>
          <Input.Search
            placeholder="搜索标题..."
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onSearch={fetchData}
            style={{ width: 240 }}
            allowClear
          />
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/asset')}>
            从知识库发布
          </Button>
        </Space>
      </div>

      {/* 内容列表 */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Spin size="large" />
        </div>
      ) : items.length === 0 ? (
        <Card>
          <Empty description="还没有发布过科普内容，去知识库选一篇文章一键发布吧" />
        </Card>
      ) : (
        items.map((item) => (
          <Card key={item.id} style={{ marginBottom: 12 }} hoverable>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ flex: 1, marginRight: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
                  <Title level={5} style={{ margin: 0, marginRight: 12 }}>{item.title}</Title>
                  {getStatusTag(item.status)}
                </div>
                <Text type="secondary" style={{ fontSize: 13 }}>{item.summary || item.content.substring(0, 100)}...</Text>
                <div style={{ marginTop: 8 }}>
                  {item.category && <Tag>{item.category}</Tag>}
                  {item.tags && item.tags.split(',').map((tag: string, i: number) => (
                    <Tag key={i}>{tag}</Tag>
                  ))}
                </div>
              </div>
              <Space>
                <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(item)}>
                  编辑
                </Button>
                <Popconfirm title="确定删除？" onConfirm={() => handleDelete(item.id)}>
                  <Button size="small" danger icon={<DeleteOutlined />}>
                    删除
                  </Button>
                </Popconfirm>
              </Space>
            </div>
          </Card>
        ))
      )}

      {/* 编辑模态框 */}
      <Modal
        open={editModalOpen}
        onCancel={() => setEditModalOpen(false)}
        title="编辑科普内容"
        width={800}
        footer={null}
      >
        {editingItem && (
          <Form layout="vertical">
            <Form.Item label="标题">
              <Input
                value={editForm.title}
                onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
              />
            </Form.Item>
            <Form.Item label="分类">
              <Input
                value={editForm.category}
                onChange={(e) => setEditForm({ ...editForm, category: e.target.value })}
                placeholder="如: 心血管 / 内分泌"
              />
            </Form.Item>
            <Form.Item label="标签（逗号分隔）">
              <Input
                value={editForm.tags}
                onChange={(e) => setEditForm({ ...editForm, tags: e.target.value })}
              />
            </Form.Item>
            <Form.Item label="正文">
              <TextArea
                rows={12}
                value={editForm.content}
                onChange={(e) => setEditForm({ ...editForm, content: e.target.value })}
              />
            </Form.Item>
            <div style={{ background: '#fffbe6', padding: 12, borderRadius: 6, marginBottom: 16 }}>
              <Text type="warning" style={{ fontSize: 12 }}>
                ⚠️ 医疗合规提示：发布前请检查内容是否符合医疗广告规范，避免绝对化表述、未经证实的疗效承诺等。
              </Text>
            </div>
            <div style={{ textAlign: 'right' }}>
              <Space>
                <Button onClick={() => setEditModalOpen(false)}>取消</Button>
                <Button type="primary" loading={saving} onClick={handleSave}>
                  保存并发布
                </Button>
              </Space>
            </div>
          </Form>
        )}
      </Modal>
    </div>
  )
}

export default PublishedList
