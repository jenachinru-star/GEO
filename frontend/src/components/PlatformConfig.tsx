import { useState, useEffect } from 'react'
import {
  Table, Button, Modal, Form, Input, Select, Switch, Tag, message,
  Space, Popconfirm, Tooltip, Card, Row, Col, Statistic
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined,
  PauseCircleOutlined, ApiOutlined, ReloadOutlined, CheckCircleOutlined,
  CloseCircleOutlined, ExperimentOutlined, SyncOutlined
} from '@ant-design/icons'
import { platformsApi } from '@/api'

const { TextArea } = Input

// 预设平台选项
const PRESET_PLATFORMS = [
  { code: 'glm', name: '智谱清言 GLM', base_url: 'https://open.bigmodel.cn/api/paas/v4', model: 'glm-4-flash' },
  { code: 'minimax', name: 'MiniMax', base_url: 'https://api.minimax.chat/v1', model: 'MiniMax-M2.7-highspeed' },
  { code: 'deepseek', name: 'DeepSeek', base_url: 'https://api.deepseek.com/v1', model: 'deepseek-chat' },
  { code: 'doubao', name: '字节豆包', base_url: 'https://ark.cn-beijing.volces.com/api/v3', model: 'doubao-pro' },
  { code: 'qwen', name: '阿里通义千问', base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus' },
  { code: 'kimi', name: 'Kimi 月之暗面', base_url: 'https://api.moonshot.cn/v1', model: 'kimi-k2' },
  { code: 'ernie', name: '百度文心一言', base_url: 'https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop', model: 'ernie-4.0' },
  { code: 'custom', name: '自定义（OpenAI兼容）', base_url: '', model: '' },
]

const PlatformConfig = () => {
  const [platforms, setPlatforms] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingPlatform, setEditingPlatform] = useState<any>(null)
  const [form] = Form.useForm()
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<any>(null)
  const [reloading, setReloading] = useState(false)

  const loadPlatforms = async () => {
    setLoading(true)
    try {
      const res: any = await platformsApi.getList()
      setPlatforms(res.data || [])
    } catch (e) {
      console.error('加载平台列表失败', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPlatforms()
  }, [])

  const handleAdd = () => {
    setEditingPlatform(null)
    form.resetFields()
    form.setFieldsValue({
      status: true,
      priority: 0,
      timeout: 30,
      max_tokens: 2000,
      temperature: 0.3,
      platform_type: 'openai_compatible',
    })
    setModalVisible(true)
  }

  const handleEdit = (record: any) => {
    setEditingPlatform(record)
    // 编辑时需要获取完整信息（含 api_key）
    platformsApi.getDetail(record.code).then((res: any) => {
      form.setFieldsValue(res.data)
      setModalVisible(true)
    }).catch(() => {
      message.error('获取平台详情失败')
    })
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      if (editingPlatform) {
        await platformsApi.update(editingPlatform.code, values)
        message.success('平台配置更新成功')
      } else {
        await platformsApi.create(values)
        message.success('平台创建成功')
      }
      setModalVisible(false)
      loadPlatforms()
    } catch (e: any) {
      if (e?.errorFields) return // 表单校验错误
      message.error('保存失败')
    }
  }

  const handleToggle = async (record: any) => {
    try {
      await platformsApi.toggle(record.code)
      message.success(record.status ? '已停用' : '已启用')
      loadPlatforms()
    } catch (e) {
      message.error('操作失败')
    }
  }

  const handleDelete = async (record: any) => {
    try {
      await platformsApi.delete(record.code)
      message.success('删除成功')
      loadPlatforms()
    } catch (e) {
      message.error('删除失败')
    }
  }

  const handleTest = async (record: any) => {
    setTesting(true)
    setTestResult(null)
    try {
      const res: any = await platformsApi.test({ platform_code: record.code })
      setTestResult(res.data)
      if (res.data?.success) {
        message.success('连接成功')
      } else {
        message.error('连接失败')
      }
    } catch (e) {
      message.error('测试请求失败')
    } finally {
      setTesting(false)
    }
  }

  const handleReload = async () => {
    setReloading(true)
    try {
      await platformsApi.reload()
      message.success('适配器重载成功')
      loadPlatforms()
    } catch (e) {
      message.error('重载失败')
    } finally {
      setReloading(false)
    }
  }

  const handlePresetChange = (code: string) => {
    const preset = PRESET_PLATFORMS.find(p => p.code === code)
    if (preset && code !== 'custom') {
      form.setFieldsValue({
        code: preset.code,
        name: preset.name,
        base_url: preset.base_url,
        model: preset.model,
      })
    }
  }

  const enabledCount = platforms.filter(p => p.status).length
  const configuredCount = platforms.filter(p => p.configured).length

  const columns = [
    {
      title: '平台', dataIndex: 'name', key: 'name', width: 150,
      render: (text: string, record: any) => (
        <Space>
          <ApiOutlined style={{ color: '#1677ff' }} />
          <span style={{ fontWeight: 500 }}>{text}</span>
          {record.source === 'env' && <Tag color="blue">.env</Tag>}
        </Space>
      )
    },
    { title: '标识', dataIndex: 'code', key: 'code', width: 100 },
    { title: '模型', dataIndex: 'model', key: 'model', width: 180, ellipsis: true },
    {
      title: '配置状态', dataIndex: 'configured', key: 'configured', width: 100,
      render: (v: boolean) => v
        ? <Tag color="green" icon={<CheckCircleOutlined />}>已配置</Tag>
        : <Tag color="default" icon={<CloseCircleOutlined />}>未配置</Tag>
    },
    {
      title: '启用状态', dataIndex: 'status', key: 'status', width: 100,
      render: (v: boolean, record: any) => (
        <Switch
          checked={v}
          onChange={() => handleToggle(record)}
          checkedChildren="启用"
          unCheckedChildren="停用"
        />
      )
    },
    { title: '优先级', dataIndex: 'priority', key: 'priority', width: 80 },
    {
      title: '操作', key: 'actions', width: 220, fixed: 'right' as const,
      render: (_: any, record: any) => (
        <Space size="small">
          <Tooltip title="测试连接">
            <Button
              type="text"
              size="small"
              icon={<ExperimentOutlined />}
              loading={testing}
              onClick={() => handleTest(record)}
            >
              测试
            </Button>
          </Tooltip>
          <Tooltip title="编辑">
            <Button type="text" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
              编辑
            </Button>
          </Tooltip>
          {record.source !== 'env' && (
            <Popconfirm title="确定删除此平台配置？" onConfirm={() => handleDelete(record)}>
              <Button type="text" size="small" danger icon={<DeleteOutlined />}>
                删除
              </Button>
            </Popconfirm>
          )}
        </Space>
      )
    },
  ]

  return (
    <div>
      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="平台总数" value={platforms.length} prefix={<ApiOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="已启用" value={enabledCount} valueStyle={{ color: '#52c41a' }} prefix={<PlayCircleOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="已配置" value={configuredCount} valueStyle={{ color: '#1677ff' }} prefix={<CheckCircleOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="未配置" value={platforms.length - configuredCount} valueStyle={{ color: '#ff4d4f' }} prefix={<CloseCircleOutlined />} />
          </Card>
        </Col>
      </Row>

      {/* 操作栏 */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            添加平台
          </Button>
          <Button icon={<ReloadOutlined />} onClick={loadPlatforms} loading={loading}>
            刷新
          </Button>
          <Button icon={<SyncOutlined />} onClick={handleReload} loading={reloading}>
            重载适配器
          </Button>
        </Space>
        <div style={{ fontSize: 12, color: '#64748B' }}>
          提示：数据库配置优先于 .env 配置；修改配置后自动热更新，无需重启服务
        </div>
      </div>

      {/* 平台列表 */}
      <Table
        dataSource={platforms}
        columns={columns}
        rowKey="code"
        loading={loading}
        pagination={false}
        scroll={{ x: 1000 }}
      />

      {/* 测试结果 */}
      {testResult && (
        <Modal
          title="连接测试结果"
          open={!!testResult}
          onCancel={() => setTestResult(null)}
          footer={<Button onClick={() => setTestResult(null)}>关闭</Button>}
        >
          {testResult.success ? (
            <div>
              <p><Tag color="success">连接成功</Tag></p>
              <p><strong>模型回复：</strong>{testResult.answer}</p>
              <p><strong>Token 消耗：</strong>输入 {testResult.prompt_tokens} + 输出 {testResult.completion_tokens} = 总计 {testResult.total_tokens}</p>
            </div>
          ) : (
            <div>
              <p><Tag color="error">连接失败</Tag></p>
              <p><strong>错误信息：</strong></p>
              <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4, overflow: 'auto' }}>
                {testResult.error}
              </pre>
            </div>
          )}
        </Modal>
      )}

      {/* 添加/编辑平台弹窗 */}
      <Modal
        title={editingPlatform ? '编辑平台配置' : '添加平台'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleSave}
        width={600}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          {!editingPlatform && (
            <Form.Item
              name="preset"
              label="选择预设平台（快速填充）"
            >
              <Select
                placeholder="选择预设平台..."
                onChange={handlePresetChange}
                options={PRESET_PLATFORMS.map(p => ({ value: p.code, label: p.name }))}
              />
            </Form.Item>
          )}

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="code"
                label="平台标识"
                rules={[
                  { required: true, message: '请输入平台标识' },
                  { pattern: /^[a-z0-9_-]+$/, message: '只能包含小写字母、数字、下划线、连字符' },
                ]}
              >
                <Input placeholder="如 glm / minimax / doubao" disabled={!!editingPlatform} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="name"
                label="平台名称"
                rules={[{ required: true, message: '请输入平台名称' }]}
              >
                <Input placeholder="如 智谱清言 GLM" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="base_url"
            label="API 基础地址"
            rules={[{ required: true, message: '请输入 API 基础地址' }]}
          >
            <Input placeholder="如 https://open.bigmodel.cn/api/paas/v4" />
          </Form.Item>

          <Form.Item
            name="api_key"
            label="API Key"
            rules={[{ required: true, message: '请输入 API Key' }]}
          >
            <Input.Password placeholder="请输入 API Key" autoComplete="off" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="model"
                label="默认模型"
                rules={[{ required: true, message: '请输入默认模型' }]}
              >
                <Input placeholder="如 glm-4-flash" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="platform_type" label="平台类型">
                <Select
                  options={[
                    { value: 'openai_compatible', label: 'OpenAI 兼容' },
                    { value: 'image', label: '生图平台' },
                  ]}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="temperature" label="温度 (0-2)">
                <Input type="number" step={0.1} min={0} max={2} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="max_tokens" label="最大输出 Token">
                <Input type="number" min={100} max={32000} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="timeout" label="超时时间 (秒)">
                <Input type="number" min={5} max={300} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="priority" label="优先级（数字越大越优先）">
                <Input type="number" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="status" label="启用状态" valuePropName="checked">
                <Switch checkedChildren="启用" unCheckedChildren="停用" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="description" label="平台描述">
            <TextArea rows={2} placeholder="可选，平台描述信息" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default PlatformConfig
