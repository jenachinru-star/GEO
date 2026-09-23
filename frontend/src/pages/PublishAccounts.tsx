import { useState, useEffect } from 'react'
import {
  Table, Button, Space, Tag, Modal, Form, Select, Input,
  message, Popconfirm
} from 'antd'
import {
  PlusOutlined, ReloadOutlined, DeleteOutlined,
  CheckCircleOutlined, CloseCircleOutlined, BarChartOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
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
  const navigate = useNavigate()
  const [list, setList] = useState<PublishAccount[]>([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [selectedPlatform, setSelectedPlatform] = useState('')
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
      setSelectedPlatform('')
      form.resetFields()
      loadList()
    } catch (e) {
      // 错误提示已由拦截器统一弹出
    }
  }

  const handleVerify = async (id: number, platform: string) => {
    try {
      if (platform === 'wechat') {
        // 微信公众号调用真实验证API
        const res: any = await request.post(`/publish-accounts/${id}/verify-real`)
        if (res.data?.valid) {
          message.success('验证成功')
        } else {
          message.error(`验证失败: ${res.data?.error || 'AppID或AppSecret无效'}`)
        }
      } else {
        // 其他平台手动标记
        await request.post(`/publish-accounts/${id}/verify`)
        message.success('已标记为有效')
      }
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
          {record.platform === 'wechat' && (
            <Button
              size="small"
              type="link"
              icon={<BarChartOutlined />}
              onClick={() => navigate(`/publish-accounts/${record.id}/stats`)}
            >
              数据
            </Button>
          )}
          {record.platform === 'wechat' ? (
            <Button
              size="small"
              type="link"
              icon={<CheckCircleOutlined />}
              onClick={() => handleVerify(record.id, record.platform)}
            >
              验证
            </Button>
          ) : (
            record.login_status !== 'valid' && (
              <Button
                size="small"
                type="link"
                icon={<CheckCircleOutlined />}
                onClick={() => handleVerify(record.id, record.platform)}
              >
                标记有效
              </Button>
            )
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
        onCancel={() => { setModalVisible(false); setSelectedPlatform(''); form.resetFields() }}
        onOk={() => form.submit()}
        width={560}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="platform" label="发布平台" rules={[{ required: true, message: '请选择平台' }]}>
            <Select
              placeholder="选择发布平台"
              showSearch
              optionFilterProp="label"
              onChange={(value) => setSelectedPlatform(value)}
            >
              {PUBLISH_PLATFORMS.map((p: any) => (
                <Select.Option key={p.code} value={p.code} label={p.name}>
                  {p.name}
                  {p.code === 'wechat' && <span style={{ color: '#52c41a', fontSize: 12, marginLeft: 8 }}>（官方API一键发布）</span>}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="account_name" label="账号名称" rules={[{ required: true, message: '请输入账号名称' }]}>
            <Input placeholder="如：张三医生公众号" />
          </Form.Item>

          {/* 微信公众号：显示 AppID + AppSecret */}
          {selectedPlatform === 'wechat' && (
            <>
              <Form.Item name="app_id" label="AppID" rules={[{ required: true, message: '请填写AppID' }]}>
                <Input placeholder="微信公众号的AppID（开发者ID）" />
              </Form.Item>
              <Form.Item name="app_secret" label="AppSecret" rules={[{ required: true, message: '请填写AppSecret' }]}>
                <Input.Password placeholder="微信公众号的AppSecret（开发者密码）" />
              </Form.Item>
            </>
          )}

          {/* 其他平台：显示 Cookie/Token */}
          {selectedPlatform && selectedPlatform !== 'wechat' && (
            <Form.Item name="credential" label="登录凭证（Cookie/Token）" rules={[{ required: true, message: '请输入登录凭证' }]}>
              <TextArea rows={4} placeholder="粘贴平台登录后的Cookie或Access Token" />
            </Form.Item>
          )}

          <Form.Item name="note" label="备注">
            <TextArea rows={2} placeholder="账号用途、注意事项等" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default PublishAccounts



