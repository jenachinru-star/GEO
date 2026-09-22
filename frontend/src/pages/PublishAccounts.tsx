import { useState, useEffect } from 'react'
import {
  Table, Button, Space, Tag, Modal, Form, Select, Input,
  message, Popconfirm
} from 'antd'
import {
  PlusOutlined, ReloadOutlined, DeleteOutlined,
  CheckCircleOutlined, CloseCircleOutlined
} from '@ant-design/icons'
import { PUBLISH_PLATFORMS, PUBLISH_PLATFORM_NAMES } from '@/store/useStore'
import request from '@/api'

const { TextArea } = Input

interface PublishAccount {
  id: number
  platform: string
  account_name: string
  login_status: string
  note: string
  last_verified_at?: string
  created_at?: string
}

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  valid: { color: 'green', label: '已验证' },
  expired: { color: 'red', label: '已过期' },
  needs_captcha: { color: 'orange', label: '需验证码' },
  unknown: { color: 'default', label: '未知' },
}

const PublishAccounts = () => {
  const [list, setList] = useState<PublishAccount[]>([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [form] = Form.useForm()

  const loadList = async () => {
    setLoading(true)
    try {
      const res: any = await request.get('/publish-accounts')
      setList(res.data?.items || [])
    } catch (e) {
      // 错误提示已由拦截器统一弹出
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadList()
  }, [])

  const handleCreate = async (values: any) => {
    try {
      await request.post('/publish-accounts', values)
      message.success('添加成功')
      setModalVisible(false)
      form.resetFields()
      loadList()
    } catch (e) {
      // 错误提示已由拦截器统一弹出
    }
  }

  const handleVerify = async (id: number) => {
    try {
      await request.post(`/publish-accounts/${id}/verify`)
      message.success('已标记为有效')
      loadList()
    } catch (e) {
      // 错误提示已由拦截器统一弹出
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await request.delete(`/publish-accounts/${id}`)
      message.success('已删除')
      loadList()
    } catch (e) {
      // 错误提示已由拦截器统一弹出
    }
  }

  const columns = [
    {
      title: '平台',
      dataIndex: 'platform',
      key: 'platform',
      render: (p: string) => (
        <Tag color="blue">{PUBLISH_PLATFORM_NAMES[p] || p}</Tag>
      ),
    },
    {
      title: '账号名称',
      dataIndex: 'account_name',
      key: 'account_name',
    },
    {
      title: '登录状态',
      dataIndex: 'login_status',
      key: 'login_status',
      render: (s: string) => {
        const cfg = STATUS_MAP[s] || STATUS_MAP.unknown
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
    {
      title: '备注',
      dataIndex: 'note',
      key: 'note',
      ellipsis: true,
    },
    {
      title: '最后验证时间',
      dataIndex: 'last_verified_at',
      key: 'last_verified_at',
      render: (t: string) => t ? new Date(t).toLocaleString() : '-',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: PublishAccount) => (
        <Space size="small">
          {record.login_status !== 'valid' && (
            <Button
              size="small"
              type="link"
              icon={<CheckCircleOutlined />}
              onClick={() => handleVerify(record.id)}
            >
              标记有效
            </Button>
          )}
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div className="page-title-bar">
        <div>
          <h2>发布账号管理</h2>
          <div className="page-desc">管理各发布平台的账号和登录凭证</div>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadList}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalVisible(true)}>
            添加账号
          </Button>
        </Space>
      </div>

      <div className="geo-card">
        <Table
          dataSource={list}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={false}
        />
      </div>

      <Modal
        title="添加发布账号"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
        width={560}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="platform" label="平台" rules={[{ required: true, message: '请选择平台' }]}>
            <Select showSearch placeholder="选择发布平台" optionFilterProp="label">
              {PUBLISH_PLATFORMS.map((p: any) => (
                <Select.Option key={p.code} value={p.code} label={p.name}>
                  {p.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="account_name" label="账号名称" rules={[{ required: true, message: '请输入账号名称' }]}>
            <Input placeholder="如：张三医生公众号" />
          </Form.Item>
          <Form.Item name="credential" label="登录凭证（Cookie/Token）" rules={[{ required: true, message: '请输入登录凭证' }]}>
            <TextArea rows={4} placeholder="粘贴平台登录后的Cookie或Access Token" />
          </Form.Item>
          <Form.Item name="note" label="备注">
            <TextArea rows={2} placeholder="账号用途、注意事项等" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default PublishAccounts



