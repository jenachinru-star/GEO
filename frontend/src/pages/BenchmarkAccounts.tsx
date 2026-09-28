import { useState, useEffect } from 'react'
import {
  Card, Table, Button, Space, Modal, Form, Input, InputNumber,
  message, Popconfirm, Tag, Row, Col
} from 'antd'
import { PlusOutlined, DeleteOutlined, EditOutlined, BarChartOutlined } from '@ant-design/icons'
import request from '@/api'
import { useNavigate } from 'react-router-dom'

const { TextArea } = Input

const BenchmarkAccounts = () => {
  const navigate = useNavigate()
  const [list, setList] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form] = Form.useForm()

  const loadList = async () => {
    setLoading(true)
    try {
      const res: any = await request.get('/benchmark')
      setList(res.data?.items || [])
    } catch (e) {
      // 错误已由拦截器处理
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadList() }, [])

  const handleSubmit = async (values: any) => {
    try {
      if (editingId) {
        await request.put(`/benchmark/${editingId}`, values)
        message.success('更新成功')
      } else {
        await request.post('/benchmark', values)
        message.success('添加成功')
      }
      setModalVisible(false)
      setEditingId(null)
      form.resetFields()
      loadList()
    } catch (e) {
      // 错误已由拦截器处理
    }
  }

  const handleEdit = (record: any) => {
    setEditingId(record.id)
    form.setFieldsValue(record)
    setModalVisible(true)
  }

  const handleDelete = async (id: number) => {
    try {
      await request.delete(`/benchmark/${id}`)
      message.success('删除成功')
      loadList()
    } catch (e) {
      // 错误已由拦截器处理
    }
  }

  const columns = [
    { title: '公众号名称', dataIndex: 'account_name', key: 'account_name' },
    { title: '微信号', dataIndex: 'wechat_id', key: 'wechat_id' },
    { title: '粉丝数', dataIndex: 'followers', key: 'followers', render: (v: number) => v?.toLocaleString() || 0 },
    { title: '平均阅读', dataIndex: 'avg_reads', key: 'avg_reads', render: (v: number) => v?.toLocaleString() || 0 },
    { title: '平均点赞', dataIndex: 'avg_likes', key: 'avg_likes', render: (v: number) => v?.toLocaleString() || 0 },
    { title: '每周发文', dataIndex: 'weekly_posts', key: 'weekly_posts' },
    {
      title: '数据来源', dataIndex: 'data_source', key: 'data_source',
      render: (v: string) => <Tag color={v === 'manual' ? 'orange' : 'blue'}>{v === 'manual' ? '手动输入' : v}</Tag>
    },
    {
      title: '操作', key: 'action', width: 220,
      render: (_: any, record: any) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>编辑</Button>
          <Button type="link" size="small" icon={<BarChartOutlined />} onClick={() => navigate('/competitor-analysis')}>对比分析</Button>
          <Popconfirm title="确定删除该对标账号？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      )
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Card
        title="对标账号管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditingId(null); form.resetFields(); setModalVisible(true) }}>
            添加对标账号
          </Button>
        }
      >
        <Table columns={columns} dataSource={list} rowKey="id" loading={loading} />
      </Card>

      <Modal
        title={editingId ? '编辑对标账号' : '添加对标账号'}
        open={modalVisible}
        onCancel={() => { setModalVisible(false); setEditingId(null) }}
        footer={null}
        width={600}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="account_name" label="公众号名称" rules={[{ required: true, message: '请输入公众号名称' }]}>
                <Input placeholder="请输入公众号名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="wechat_id" label="微信号">
                <Input placeholder="请输入微信号" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="description" label="账号简介">
            <TextArea rows={2} placeholder="请输入账号简介" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="followers" label="粉丝数">
                <InputNumber style={{ width: '100%' }} min={0} placeholder="0" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="avg_reads" label="平均阅读量">
                <InputNumber style={{ width: '100%' }} min={0} placeholder="0" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="weekly_posts" label="每周发文数">
                <InputNumber style={{ width: '100%' }} min={0} placeholder="0" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="avg_likes" label="平均点赞数">
                <InputNumber style={{ width: '100%' }} min={0} placeholder="0" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="avg_shares" label="平均分享数">
                <InputNumber style={{ width: '100%' }} min={0} placeholder="0" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="note" label="备注">
            <TextArea rows={2} placeholder="备注信息" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">{editingId ? '保存' : '添加'}</Button>
              <Button onClick={() => { setModalVisible(false); setEditingId(null) }}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default BenchmarkAccounts
