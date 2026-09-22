import { useEffect, useState } from 'react'
import {
  Row, Col, Card, Table, Switch, Progress, Tag, Button, Space,
  Typography, Modal, InputNumber, message, Descriptions, Empty
} from 'antd'
import { ReloadOutlined, SafetyOutlined, DollarOutlined, ApiOutlined } from '@ant-design/icons'
import { usageGovernanceApi } from '@/api'

const { Title, Text } = Typography

const platformNames: Record<string, string> = {
  glm: '智谱GLM', minimax: 'MiniMax', deepseek: 'DeepSeek',
  doubao: '豆包', qwen: '通义千问', kimi: 'Kimi',
  ernie: '文心一言', yuanbao: '腾讯元宝',
}

const UsageGovernance = () => {
  const [platforms, setPlatforms] = useState<any[]>([])
  const [quota, setQuota] = useState<any>(null)
  const [adminUsers, setAdminUsers] = useState<any[]>([])
  const [adminReport, setAdminReport] = useState<any[]>([])
  const [allUsers, setAllUsers] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [editModal, setEditModal] = useState<{user_id: number, username: string, limit: number} | null>(null)
  const [newLimit, setNewLimit] = useState<number>(19.9)

  const isAdmin = quota?.is_admin

  const loadAll = async () => {
    setLoading(true)
    try {
      const [pf, qt] = await Promise.all([
        usageGovernanceApi.getAvailablePlatforms(),
        usageGovernanceApi.getMyQuota(),
      ])
      setPlatforms(pf.data.platforms || [])
      setQuota(qt.data)

      // 管理员加载额外数据
      if (qt.data.is_admin) {
        const [users, report, allU] = await Promise.all([
          usageGovernanceApi.adminListUsersQuota(),
          usageGovernanceApi.adminUsageReport(),
          usageGovernanceApi.adminListUsers(),
        ])
        setAdminUsers(users.data.users || [])
        setAdminReport(report.data.items || [])
        setAllUsers(allU.data.users || [])
      }
    } catch (e) {
      console.error('加载失败', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadAll() }, [])

  const handleToggle = async (platform: string, enabled: boolean) => {
    try {
      await usageGovernanceApi.updatePref(platform, enabled)
      message.success(`${platformNames[platform] || platform} 已${enabled ? '开启' : '关闭'}`)
      loadAll()
    } catch (e) { /* 错误拦截器已提示 */ }
  }

  const handleEditQuota = (record: any) => {
    setEditModal({ user_id: record.user_id, username: record.username, limit: record.monthly_limit })
    setNewLimit(record.monthly_limit)
  }

  const handleChangeRole = async (record: any) => {
    const newRole = record.role === 'admin' ? 'doctor' : 'admin'
    try {
      await usageGovernanceApi.adminChangeRole(record.user_id, newRole)
      message.success(`${record.username} 已${newRole === 'admin' ? '提升为管理员' : '降为普通用户'}`)
      loadAll()
    } catch (e) { /* 拦截器提示 */ }
  }

  const saveQuota = async () => {
    if (!editModal) return
    try {
      await usageGovernanceApi.adminUpdateQuota(editModal.user_id, newLimit)
      message.success(`已更新 ${editModal.username} 的配额为 ¥${newLimit}/月`)
      setEditModal(null)
      loadAll()
    } catch (e) { /* 拦截器提示 */ }
  }

  // 配额进度条颜色
  const getProgressColor = (pct: number) => {
    if (pct >= 100) return '#ff4d4f'
    if (pct >= 80) return '#faad14'
    return '#52c41a'
  }

  const adminColumns = [
    { title: '用户', dataIndex: 'username', key: 'username' },
    { title: '邮箱', dataIndex: 'email', key: 'email' },
    { title: '角色', dataIndex: 'role', key: 'role', render: (v: string) =>
      <Tag color={v === 'admin' ? 'red' : 'blue'}>{v}</Tag> },
    { title: '月配额', dataIndex: 'monthly_limit', key: 'monthly_limit', render: (v: number) =>
      v < 0 ? '无限' : `¥${v}` },
    { title: '已用', dataIndex: 'used_cost', key: 'used_cost', render: (v: number) =>
      `¥${v.toFixed(2)}` },
    { title: '使用率', dataIndex: 'usage_pct', key: 'usage_pct', render: (v: number) =>
      <Progress percent={v} size="small" strokeColor={getProgressColor(v)} style={{ width: 100 }} /> },
    { title: '操作', key: 'action', render: (_: any, record: any) =>
      <Button size="small" onClick={() => handleEditQuota(record)}>调整配额</Button> },
  ]

  const reportColumns = [
    { title: '用户', dataIndex: 'username', key: 'username' },
    { title: '平台', dataIndex: 'platform', key: 'platform', render: (v: string) =>
      <Tag>{platformNames[v] || v}</Tag> },
    { title: 'Token', dataIndex: 'tokens', key: 'tokens', render: (v: number) =>
      v >= 10000 ? `${(v/10000).toFixed(1)}万` : v },
    { title: '费用', dataIndex: 'cost', key: 'cost', render: (v: number) =>
      `¥${v.toFixed(4)}` },
  ]

  return (
    <div>
      <div className="page-title-bar">
        <div>
          <h2>用量管理</h2>
          <div className="page-desc">管理您使用的AI模型开关，查看月度用量配额</div>
        </div>
        <Button icon={<ReloadOutlined />} onClick={loadAll} loading={loading}>刷新</Button>
      </div>

      {/* 我的配额概览 */}
      {quota && (
        <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
          <Col xs={24} md={12}>
            <Card>
              <div style={{ marginBottom: 12 }}>
                <Space>
                  <DollarOutlined style={{ fontSize: 24, color: '#1890ff' }} />
                  <Title level={4} style={{ margin: 0 }}>本月AI用量</Title>
                </Space>
              </div>
              <Descriptions column={1} size="small">
                <Descriptions.Item label="月度配额">
                  {quota.monthly_limit < 0 ? '无限' : `¥${quota.monthly_limit}`}
                </Descriptions.Item>
                <Descriptions.Item label="已消耗">
                  <Text strong>¥{quota.used_cost.toFixed(2)}</Text>
                  {quota.usage_pct >= 80 && <Tag color="orange" style={{ marginLeft: 8 }}>接近上限</Tag>}
                  {quota.usage_pct >= 100 && <Tag color="red" style={{ marginLeft: 8 }}>已用尽</Tag>}
                </Descriptions.Item>
              </Descriptions>
              <Progress
                percent={quota.usage_pct}
                strokeColor={getProgressColor(quota.usage_pct)}
                style={{ marginTop: 16 }}
              />
              {!isAdmin && (
                <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
                  配额用尽后AI功能将暂停，如需提升请联系管理员
                </div>
              )}
            </Card>
          </Col>

          <Col xs={24} md={12}>
            <Card title="各平台本月消耗">
              {quota.by_platform?.length ? (
                <Table
                  dataSource={quota.by_platform}
                  columns={[
                    { title: '平台', dataIndex: 'platform', key: 'platform', render: (v: string) => <Tag>{platformNames[v] || v}</Tag> },
                    { title: 'Token', dataIndex: 'tokens', key: 'tokens' },
                    { title: '费用', dataIndex: 'cost', key: 'cost', render: (v: number) => `¥${v.toFixed(4)}` },
                  ]}
                  rowKey="platform"
                  size="small"
                  pagination={false}
                />
              ) : (
                <Empty description="本月暂无用量" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </Card>
          </Col>
        </Row>
      )}

      {/* 平台开关 */}
      <Card
        title={<Space><ApiOutlined /> AI模型开关</Space>}
        style={{ marginBottom: 20 }}
      >
        {platforms.map((p) => (
          <div key={p.platform_code} style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '12px 0', borderBottom: '1px solid #f0f0f0'
          }}>
            <div>
              <Text strong>{platformNames[p.platform_code] || p.platform_code}</Text>
              <div style={{ fontSize: 12, color: '#999' }}>{p.platform_code}</div>
            </div>
            <Space>
              <Text type="secondary">{p.enabled ? '已开启' : '已停用'}</Text>
              <Switch
                checked={p.enabled}
                onChange={(checked) => handleToggle(p.platform_code, checked)}
              />
            </Space>
          </div>
        ))}
      </Card>

      {/* 管理员区域 */}
      {isAdmin && (
        <>
          <Card
            title={<Space><SafetyOutlined /> 用户管理（管理员）</Space>}
            style={{ marginBottom: 20 }}
          >
            <Table
              dataSource={allUsers}
              columns={[
                { title: 'ID', dataIndex: 'user_id', key: 'user_id', width: 60 },
                { title: '用户名', dataIndex: 'username', key: 'username' },
                { title: '邮箱', dataIndex: 'email', key: 'email' },
                { title: '角色', dataIndex: 'role', key: 'role', render: (v: string) =>
                  <Tag color={v === 'admin' ? 'red' : 'blue'}>{v === 'admin' ? '管理员' : '普通用户'}</Tag> },
                { title: '状态', dataIndex: 'status', key: 'status', render: (v: boolean) =>
                  v ? <Tag color="success">正常</Tag> : <Tag color="error">禁用</Tag> },
                { title: '操作', key: 'action', render: (_: any, record: any) =>
                  record.role === 'admin' ? (
                    <Button size="small" danger onClick={() => handleChangeRole(record)}>降为普通用户</Button>
                  ) : (
                    <Button size="small" type="primary" onClick={() => handleChangeRole(record)}>设为管理员</Button>
                  )
                },
              ]}
              rowKey="user_id"
              size="small"
              pagination={{ pageSize: 10 }}
            />
          </Card>

          <Card
            title={<Space><SafetyOutlined /> 用户配额管理（管理员）</Space>}
            style={{ marginBottom: 20 }}
          >
            <Table
              dataSource={adminUsers}
              columns={adminColumns}
              rowKey="user_id"
              size="small"
              pagination={{ pageSize: 10 }}
            />
          </Card>

          <Card title="用户×平台用量交叉报表（本月）">
            <Table
              dataSource={adminReport}
              columns={reportColumns}
              rowKey={(r) => `${r.user_id}-${r.platform}`}
              size="small"
              pagination={{ pageSize: 20 }}
            />
          </Card>
        </>
      )}

      {/* 编辑配额弹窗 */}
      <Modal
        title={`调整配额 — ${editModal?.username}`}
        open={!!editModal}
        onOk={saveQuota}
        onCancel={() => setEditModal(null)}
      >
        <div style={{ marginBottom: 12 }}>
          当前月配额：{editModal?.limit !== undefined ? (editModal.limit < 0 ? '无限' : `¥${editModal.limit}`) : '-'}
        </div>
        <div>
          新月度费用上限（元）：
          <InputNumber
            style={{ width: 150, marginLeft: 12 }}
            min={-1}
            value={newLimit}
            onChange={(v) => setNewLimit(v ?? 19.9)}
            step={1}
          />
        </div>
        <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
          设为 -1 表示无限额
        </div>
      </Modal>
    </div>
  )
}

export default UsageGovernance
