import { useEffect, useState } from 'react'
import {
  Row, Col, Card, Table, Switch, Progress, Tag, Button, Space,
  Typography, Modal, InputNumber, message, Descriptions, Empty, Select, Alert
} from 'antd'
import { ReloadOutlined, SafetyOutlined, DollarOutlined, ApiOutlined } from '@ant-design/icons'
import request, { usageGovernanceApi } from '@/api'
import ReactECharts from 'echarts-for-react'

const { Title, Text } = Typography

const platformNames: Record<string, string> = {
  glm: '智谱GLM', minimax: 'MiniMax', deepseek: 'DeepSeek',
  doubao: '豆包', qwen: '通义千问', kimi: 'Kimi',
  ernie: '文心一言', yuanbao: '腾讯元宝',
}

const taskTypeNames: Record<string, string> = {
  geo_refresh: 'GEO刷新',
  geo_collect: 'GEO采集',
  semantic_gen: '语义生成',
  semantic_extend: '语义延伸',
  article_gen: '文章生成',
  compliance_check: '合规检查',
  image_gen: '生图',
  video_gen: '生视频',
  rag_query: 'RAG问答',
  http_request: 'HTTP请求',
  asset_url_collect: '资产采集',
  llm_analyze: 'LLM分析',
  rag: 'RAG问答',
  other: '其他',
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
  const [viewUserId, setViewUserId] = useState<number | null>(null)  // null表示看自己
  // 用量明细
  const [usageLogs, setUsageLogs] = useState<any[]>([])
  const [logsTotal, setLogsTotal] = useState(0)
  const [logsPage, setLogsPage] = useState(1)
  const [logsPageSize, setLogsPageSize] = useState(20)
  const [logsDays, setLogsDays] = useState(7)
  const [logsLoading, setLogsLoading] = useState(false)
  const [logsPlatform, setLogsPlatform] = useState<string | undefined>(undefined)
  // 平台统计
  const [platformStats, setPlatformStats] = useState<any[]>([])
  const [platformDays, setPlatformDays] = useState(30)
  // 趋势图
  const [trendData, setTrendData] = useState<any[]>([])
  const [trendDays, setTrendDays] = useState(30)
  // 任务类型分布
  const [taskTypeData, setTaskTypeData] = useState<any[]>([])
  const [taskTypeDays, setTaskTypeDays] = useState(30)

  const isAdmin = quota?.is_admin

  const loadAll = async () => {
    setLoading(true)
    try {
      // 加载配额（管理员可传target_user_id）
      const quotaParams = viewUserId ? { target_user_id: viewUserId } : {}
      const [pf, qt] = await Promise.all([
        usageGovernanceApi.getAvailablePlatforms(),
        request.get('/usage/quota/my', { params: quotaParams }),
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

  useEffect(() => { loadAll() }, [viewUserId])

  // 加载用量明细
  const loadUsageLogs = async (page = 1, pageSize = 20, days = 7, platform?: string) => {
    setLogsLoading(true)
    try {
      const params: any = { page, page_size: pageSize, days }
      if (platform) params.platform = platform
      const res: any = await request.get('/usage/my/logs', { params })
      setUsageLogs(res.data.items || [])
      setLogsTotal(res.data.total || 0)
    } catch (e) {
      console.error('加载用量明细失败', e)
    } finally {
      setLogsLoading(false)
    }
  }

  useEffect(() => {
    loadUsageLogs(logsPage, logsPageSize, logsDays, logsPlatform)
  }, [logsPage, logsPageSize, logsDays, logsPlatform])

  // 加载平台统计
  const loadPlatformStats = async (days: number) => {
    try {
      const res: any = await request.get('/usage/my/by-platform', { params: { days } })
      setPlatformStats(res.data || [])
    } catch (e) {
      console.error('加载平台统计失败', e)
    }
  }

  useEffect(() => { loadPlatformStats(platformDays) }, [platformDays])

  // 加载趋势数据
  const loadTrend = async (days: number) => {
    try {
      const res: any = await request.get('/usage/my/trend', { params: { days } })
      setTrendData(res.data || [])
    } catch (e) {
      console.error('加载趋势数据失败', e)
    }
  }

  useEffect(() => { loadTrend(trendDays) }, [trendDays])

  // 加载任务类型分布
  const loadTaskType = async (days: number) => {
    try {
      const res: any = await request.get('/usage/my/by-task-type', { params: { days } })
      setTaskTypeData(res.data || [])
    } catch (e) {
      console.error('加载任务类型分布失败', e)
    }
  }

  useEffect(() => { loadTaskType(taskTypeDays) }, [taskTypeDays])

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

  // 用量明细表格列
  const logColumns = [
    { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 170, render: (v: string) => v ? new Date(v).toLocaleString('zh-CN') : '-' },
    { title: '平台', dataIndex: 'platform', key: 'platform', width: 100, render: (v: string) => <Tag color="blue">{platformNames[v] || v}</Tag> },
    { title: '模型', dataIndex: 'model', key: 'model', width: 150, ellipsis: true },
    { title: '任务类型', dataIndex: 'task_type', key: 'task_type', width: 110, render: (v: string) => <Tag>{taskTypeNames[v] || v || '未知'}</Tag> },
    { title: '输入Token', dataIndex: 'prompt_tokens', key: 'prompt_tokens', width: 90, render: (v: number) => v?.toLocaleString() || 0 },
    { title: '输出Token', dataIndex: 'completion_tokens', key: 'completion_tokens', width: 90, render: (v: number) => v?.toLocaleString() || 0 },
    { title: '总Token', dataIndex: 'total_tokens', key: 'total_tokens', width: 90, render: (v: number) => <Text strong>{v?.toLocaleString() || 0}</Text> },
    { title: '费用', dataIndex: 'estimated_cost', key: 'estimated_cost', width: 90, render: (v: number) => <Text type={v > 0 ? 'danger' : undefined}>¥{v ? v.toFixed(4) : '0.0000'}</Text> },
    { title: '耗时', dataIndex: 'latency_ms', key: 'latency_ms', width: 80, render: (v: number) => v ? `${(v/1000).toFixed(1)}s` : '-' },
    { title: '状态', dataIndex: 'success', key: 'success', width: 70, render: (v: boolean) => v ? <Tag color="green">成功</Tag> : <Tag color="red">失败</Tag> },
  ]

  // 格式化 token 数
  const formatTokens = (n: number) => {
    if (n >= 100000000) return (n / 100000000).toFixed(2) + ' 亿'
    if (n >= 10000) return (n / 10000).toFixed(1) + ' 万'
    return n.toString()
  }

  // 趋势图配置（用户端接口返回 tokens 字段）
  const trendOption = trendData.length ? {
    tooltip: { trigger: 'axis' },
    legend: { data: ['总Token', '调用次数'], bottom: 0 },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'category',
      data: trendData.map((d: any) => d.date.slice(5)),
      axisLine: { lineStyle: { color: '#CBD5E1' } }
    },
    yAxis: {
      type: 'value',
      name: 'Token',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#F1F5F9' } },
      axisLabel: { formatter: (v: number) => formatTokens(v) }
    },
    series: [
      {
        name: '总Token', type: 'line', smooth: true,
        data: trendData.map((d: any) => d.tokens),
        itemStyle: { color: '#10B981' },
        areaStyle: { color: 'rgba(16,185,129,0.08)' }
      },
      {
        name: '调用次数', type: 'line', smooth: true,
        data: trendData.map((d: any) => d.calls),
        itemStyle: { color: '#2563EB' },
        lineStyle: { width: 2, type: 'dashed' }
      }
    ]
  } : {}

  // 任务类型饼图配置（用户端接口返回 tokens 字段）
  const taskTypeOption = taskTypeData.length ? {
    tooltip: {
      trigger: 'item',
      formatter: (p: any) => `${p.name}<br/>Token: ${formatTokens(p.value)} (${p.percent}%)`
    },
    legend: { bottom: 0, left: 'center', type: 'scroll' },
    series: [{
      type: 'pie',
      radius: ['40%', '65%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: true,
      label: { show: true, formatter: '{b}\n{d}%', fontSize: 11 },
      data: taskTypeData.map((t: any) => ({
        name: taskTypeNames[t.task_type] || t.task_type || '未知',
        value: t.tokens,
      }))
    }]
  } : {}

  // ===== C6：费用预估 + 异常告警 =====
  const now = new Date()
  const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
  const todayCost = trendData.find((d: any) => d.date === todayStr)?.cost || 0
  const todayTokens = trendData.find((d: any) => d.date === todayStr)?.tokens || 0

  // 本月预估（按当前日均消耗 * 本月天数）
  const dayOfMonth = now.getDate()
  const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()
  const dailyAvgCost = dayOfMonth > 0 ? (quota?.used_cost || 0) / dayOfMonth : 0
  const estimatedMonthlyCost = dailyAvgCost * daysInMonth

  // 异常告警（某天消耗超过过去7天平均值的2倍，且超过1000 token）
  const abnormalDays = trendData.filter((d: any, i: number) => {
    if (i < 7) return false
    const prev7Days = trendData.slice(i - 7, i)
    const avg = prev7Days.reduce((sum: number, x: any) => sum + (x.tokens || 0), 0) / 7
    return (d.tokens || 0) > avg * 2 && (d.tokens || 0) > 1000
  })

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
                  <Title level={4} style={{ margin: 0 }}>
                    {quota?.target_user ? `查看用户：${quota.target_user.username}` : '本月AI用量'}
                  </Title>
                  {isAdmin && (
                    <Select
                      value={viewUserId}
                      onChange={(val) => { setViewUserId(val); }}
                      style={{ width: 180, marginLeft: 16 }}
                      placeholder="切换查看用户"
                      allowClear
                      options={[
                        { value: null, label: '我自己' },
                        ...allUsers.filter(u => u.user_id !== quota?.view_user_id).map(u => ({ value: u.user_id, label: u.username }))
                      ]}
                    />
                  )}
                </Space>
              </div>
              <Descriptions column={1} size="small">
                <Descriptions.Item label="月度配额">
                  {quota.monthly_limit < 0 ? '无限' : `¥${quota.monthly_limit}`}
                </Descriptions.Item>
                <Descriptions.Item label="已消耗">
                  <Text strong style={{ fontSize: 18 }}>¥{quota.used_cost.toFixed(2)}</Text>
                  {quota.usage_pct >= 80 && <Tag color="orange" style={{ marginLeft: 8 }}>接近上限</Tag>}
                  {quota.usage_pct >= 100 && <Tag color="red" style={{ marginLeft: 8 }}>已用尽</Tag>}
                </Descriptions.Item>
                {!quota.target_user && (
                  <>
                    <Descriptions.Item label="今日消耗">
                      <Text>¥{todayCost.toFixed(4)}</Text>
                      <Text type="secondary" style={{ marginLeft: 8 }}>{todayTokens.toLocaleString()} Token</Text>
                    </Descriptions.Item>
                    <Descriptions.Item label="本月预估">
                      <Text>¥{estimatedMonthlyCost.toFixed(2)}</Text>
                      {estimatedMonthlyCost > quota.monthly_limit && quota.monthly_limit > 0 && (
                        <Tag color="red" style={{ marginLeft: 8 }}>预计超支</Tag>
                      )}
                    </Descriptions.Item>
                  </>
                )}
              </Descriptions>
              <Progress
                percent={quota.usage_pct}
                strokeColor={getProgressColor(quota.usage_pct)}
                style={{ marginTop: 16 }}
              />
              {!quota.target_user && abnormalDays.length > 0 && (
                <Alert
                  message="用量异常提醒"
                  description={`检测到 ${abnormalDays.length} 天用量突增：${abnormalDays.map((d: any) => d.date).join('、')}，请确认是否为正常使用`}
                  type="warning"
                  showIcon
                  style={{ marginTop: 12 }}
                />
              )}
              {!isAdmin && (
                <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
                  配额用尽后AI功能将暂停，如需提升请联系管理员
                </div>
              )}
            </Card>
          </Col>

          <Col xs={24} md={12}>
            <Card
              title="各平台调用对比"
              extra={
                <Select
                  value={platformDays}
                  onChange={setPlatformDays}
                  style={{ width: 120 }}
                  options={[
                    { value: 7, label: '最近7天' },
                    { value: 30, label: '最近30天' },
                    { value: 90, label: '最近90天' },
                  ]}
                />
              }
            >
              {platformStats?.length ? (
                <Table
                  dataSource={platformStats}
                  columns={[
                    { title: '平台', dataIndex: 'platform', key: 'platform', width: 100, render: (v: string) => <Tag color="blue">{platformNames[v] || v}</Tag> },
                    { title: '模型', dataIndex: 'model', key: 'model', width: 150, ellipsis: true },
                    { title: '总Token', dataIndex: 'tokens', key: 'tokens', width: 100, render: (v: number) => v >= 10000 ? `${(v/10000).toFixed(1)}万` : v.toLocaleString() },
                    { title: '调用次数', dataIndex: 'calls', key: 'calls', width: 90 },
                    { title: '成功率', dataIndex: 'success_rate', key: 'success_rate', width: 80, render: (v: number) => <Text type={v >= 90 ? 'success' : v >= 70 ? 'warning' : 'danger'}>{v}%</Text> },
                    { title: '平均耗时', dataIndex: 'avg_latency_ms', key: 'avg_latency_ms', width: 90, render: (v: number) => v ? `${(v/1000).toFixed(1)}s` : '-' },
                    { title: '估算成本', dataIndex: 'cost', key: 'cost', width: 100, render: (v: number) => `¥${v.toFixed(4)}` },
                  ]}
                  rowKey={(record: any) => `${record.platform}-${record.model}`}
                  size="small"
                  pagination={false}
                  scroll={{ x: 800 }}
                />
              ) : (
                <Empty description="暂无用量数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </Card>
          </Col>
        </Row>
      )}

      {/* 平台开关（查看其他用户时隐藏） */}
      {(!quota?.target_user) && (
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
      )}
      {quota?.target_user && (
        <Alert
          message="查看其他用户模式"
          description="当前正在查看其他用户的用量数据，模型开关和用户管理仅在查看自己时可用。"
          type="info"
          showIcon
          style={{ marginBottom: 20 }}
        />
      )}

      {/* 趋势图 + 任务类型分布 */}
      {!quota?.target_user && (
        <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
          <Col xs={24} lg={14}>
            <Card
              title="Token消耗趋势"
              extra={
                <Select value={trendDays} onChange={setTrendDays} style={{ width: 120 }}>
                  <Select.Option value={7}>最近7天</Select.Option>
                  <Select.Option value={30}>最近30天</Select.Option>
                  <Select.Option value={90}>最近90天</Select.Option>
                </Select>
              }
            >
              {trendData.length ? (
                <ReactECharts option={trendOption} style={{ height: 300 }} />
              ) : (
                <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94A3B8' }}>
                  暂无数据
                </div>
              )}
            </Card>
          </Col>
          <Col xs={24} lg={10}>
            <Card
              title="任务类型Token分布"
              extra={
                <Select value={taskTypeDays} onChange={setTaskTypeDays} style={{ width: 120 }}>
                  <Select.Option value={7}>最近7天</Select.Option>
                  <Select.Option value={30}>最近30天</Select.Option>
                  <Select.Option value={90}>最近90天</Select.Option>
                </Select>
              }
            >
              {taskTypeData.length ? (
                <ReactECharts option={taskTypeOption} style={{ height: 300 }} />
              ) : (
                <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94A3B8' }}>
                  暂无数据
                </div>
              )}
            </Card>
          </Col>
        </Row>
      )}

      {/* 用量明细列表 */}
      <Card
        title={<Space><ApiOutlined /> 用量明细</Space>}
        style={{ marginBottom: 20 }}
        extra={
          <Space>
            <Select
              value={logsDays}
              onChange={setLogsDays}
              style={{ width: 120 }}
              options={[
                { value: 1, label: '今天' },
                { value: 7, label: '最近7天' },
                { value: 30, label: '最近30天' },
                { value: 90, label: '最近90天' },
              ]}
            />
            <Select
              value={logsPlatform}
              onChange={setLogsPlatform}
              allowClear
              placeholder="平台筛选"
              style={{ width: 130 }}
              options={Object.entries(platformNames).map(([k, v]) => ({ value: k, label: v }))}
            />
          </Space>
        }
      >
        {quota?.target_user ? (
          <Alert
            message="查看其他用户时暂不支持明细数据"
            description="用量明细、趋势图和任务类型分布仅显示当前登录用户自己的数据。"
            type="info"
            showIcon
          />
        ) : (
          <Table
            dataSource={usageLogs}
            columns={logColumns}
            rowKey="id"
            loading={logsLoading}
            pagination={{
              current: logsPage,
              pageSize: logsPageSize,
              total: logsTotal,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total) => `共 ${total} 条记录`,
              onChange: (page, pageSize) => { setLogsPage(page); setLogsPageSize(pageSize) },
            }}
            scroll={{ x: 1200 }}
            size="small"
          />
        )}
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
