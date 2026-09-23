import { useEffect, useState } from 'react'
import {
  Row, Col, Card, Table, Button, Space, Select, Tag, Tooltip, Empty, Typography, message
} from 'antd'
import { ReloadOutlined, InfoCircleOutlined, DownloadOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { usageApi, exportApi } from '@/api'

const { Title } = Typography

// 格式化 token 数（万/亿）
const formatTokens = (n: number) => {
  if (n >= 100000000) return (n / 100000000).toFixed(2) + ' 亿'
  if (n >= 10000) return (n / 10000).toFixed(1) + ' 万'
  return n.toString()
}

// 任务类型中文映射
const taskTypeMap: Record<string, string> = {
  geo_collect: 'GEO采集',
  semantic_extend: '语义延伸',
  article_gen: '文章生成',
  rag: 'RAG问答',
  llm_analyze: 'LLM分析',
  image_gen: '图片生成',
  other: '其他',
  unknown: '未知',
}

// 平台颜色
const platformColors: Record<string, string> = {
  deepseek: '#2563EB',
  glm: '#8B5CF6',
  minimax: '#10B981',
  doubao: '#F59E0B',
  qwen: '#EF4444',
}

const UsageDashboard = () => {
  const [days, setDays] = useState(7)
  const [overview, setOverview] = useState<any>(null)
  const [trend, setTrend] = useState<any[]>([])
  const [byTaskType, setByTaskType] = useState<any[]>([])
  const [byPlatform, setByPlatform] = useState<any[]>([])
  const [byUser, setByUser] = useState<any[]>([])
  const [logs, setLogs] = useState<any>({ items: [], total: 0 })
  const [logPage, setLogPage] = useState(1)
  const [loading, setLoading] = useState(false)

  const loadAll = async () => {
    setLoading(true)
    try {
      const [ov, tr, tt, pf, us, lg] = await Promise.all([
        usageApi.getOverview(days),
        usageApi.getTrend(days),
        usageApi.getByTaskType(days),
        usageApi.getByPlatform(days),
        usageApi.getByUser(days, 20),
        usageApi.getLogs({ page: logPage, page_size: 20, days }),
      ])
      setOverview(ov.data)
      setTrend(tr.data || [])
      setByTaskType(tt.data || [])
      setByPlatform(pf.data || [])
      setByUser(us.data || [])
      setLogs(lg.data || { items: [], total: 0 })
    } catch (e) {
      console.error('加载用量统计失败', e)
    } finally {
      setLoading(false)
    }
  }

  // 导出用量数据（待后端实现 /usage/export 接口后启用）
  const handleExport = async () => {
    message.info('用量导出功能开发中，敬请期待')
  }

  useEffect(() => {
    loadAll()
  }, [days, logPage])

  // ===== 趋势图配置 =====
  const trendOption = trend.length ? {
    tooltip: { trigger: 'axis' },
    legend: { data: ['输入Token', '输出Token', '总Token'], bottom: 0 },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'category',
      data: trend.map((d: any) => d.date.slice(5)),
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
        name: '输入Token', type: 'line', smooth: true, stack: null,
        data: trend.map((d: any) => d.prompt_tokens),
        itemStyle: { color: '#2563EB' },
        areaStyle: { color: 'rgba(37,99,235,0.08)' }
      },
      {
        name: '输出Token', type: 'line', smooth: true,
        data: trend.map((d: any) => d.completion_tokens),
        itemStyle: { color: '#8B5CF6' },
        areaStyle: { color: 'rgba(139,92,246,0.08)' }
      },
      {
        name: '总Token', type: 'line', smooth: true,
        data: trend.map((d: any) => d.total_tokens),
        itemStyle: { color: '#10B981' },
        lineStyle: { width: 2, type: 'dashed' }
      }
    ]
  } : {}

  // ===== 任务类型饼图配置 =====
  const taskTypeOption = byTaskType.length ? {
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
      data: byTaskType.map((t: any) => ({
        name: taskTypeMap[t.task_type] || t.task_type,
        value: t.total_tokens,
      }))
    }]
  } : {}

  // ===== 统计卡片配置 =====
  const statCards = overview ? [
    {
      label: '总 Token 消耗',
      value: formatTokens(overview.total_tokens),
      sub: `输入 ${formatTokens(overview.prompt_tokens)} / 输出 ${formatTokens(overview.completion_tokens)}`,
      gradient: 'var(--primary-gradient)',
    },
    {
      label: '估算总成本',
      value: `¥${overview.total_cost?.toFixed(4) || '0.0000'}`,
      sub: `今日 ¥${overview.today?.total_cost?.toFixed(4) || '0'}`,
      gradient: 'var(--success-gradient)',
    },
    {
      label: 'LLM 调用次数',
      value: overview.call_count?.toLocaleString() || '0',
      sub: `今日 ${overview.today?.call_count || 0} 次`,
      gradient: 'var(--purple-gradient)',
    },
    {
      label: '活跃用户数',
      value: overview.active_users || '0',
      sub: `成功率 ${overview.success_rate}%`,
      gradient: 'var(--warning-gradient)',
    },
  ] : []

  // ===== 平台对比表格列 =====
  const platformColumns = [
    { title: '平台', dataIndex: 'platform', key: 'platform', render: (v: string) => (
      <Tag color={platformColors[v] || 'default'}>{v}</Tag>
    )},
    { title: '模型', dataIndex: 'model', key: 'model', ellipsis: true },
    { title: '总Token', dataIndex: 'total_tokens', key: 'total_tokens', render: (v: number) => formatTokens(v) },
    { title: '调用次数', dataIndex: 'call_count', key: 'call_count' },
    { title: '成功率', dataIndex: 'success_rate', key: 'success_rate', render: (v: number) => `${v}%` },
    { title: '平均耗时', dataIndex: 'avg_latency_ms', key: 'avg_latency_ms', render: (v: number) => `${v}ms` },
    { title: '估算成本', dataIndex: 'total_cost', key: 'total_cost', render: (v: number) => `¥${v?.toFixed(4) || '0'}` },
  ]

  // ===== 用户排行表格列 =====
  const userColumns = [
    { title: '排名', dataIndex: 'rank', key: 'rank', width: 60, render: (v: number) => (
      <span style={{ fontWeight: 700, color: v <= 3 ? '#F59E0B' : '#94A3B8' }}>{v}</span>
    )},
    { title: '用户', dataIndex: 'username', key: 'username' },
    { title: '角色', dataIndex: 'role', key: 'role', render: (v: string) => <Tag>{v}</Tag> },
    { title: '总Token', dataIndex: 'total_tokens', key: 'total_tokens', render: (v: number) => formatTokens(v) },
    { title: '调用次数', dataIndex: 'call_count', key: 'call_count' },
    { title: '估算成本', dataIndex: 'total_cost', key: 'total_cost', render: (v: number) => `¥${v?.toFixed(4) || '0'}` },
  ]

  // ===== 详细日志表格列 =====
  const logColumns = [
    { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 170, render: (v: string) => v?.slice(0, 19).replace('T', ' ') },
    { title: '用户ID', dataIndex: 'user_id', key: 'user_id', width: 80 },
    { title: '平台', dataIndex: 'platform', key: 'platform', width: 90, render: (v: string) => <Tag color={platformColors[v] || 'default'}>{v}</Tag> },
    { title: '任务类型', dataIndex: 'task_type', key: 'task_type', width: 110, render: (v: string) => taskTypeMap[v] || v },
    { title: '输入', dataIndex: 'prompt_tokens', key: 'prompt_tokens', width: 80 },
    { title: '输出', dataIndex: 'completion_tokens', key: 'completion_tokens', width: 80 },
    { title: '总计', dataIndex: 'total_tokens', key: 'total_tokens', width: 90 },
    { title: '耗时', dataIndex: 'latency_ms', key: 'latency_ms', width: 80, render: (v: number) => `${v}ms` },
    { title: '状态', dataIndex: 'success', key: 'success', width: 70, render: (v: boolean) => v ? <Tag color="success">成功</Tag> : <Tag color="error">失败</Tag> },
    { title: '来源', dataIndex: 'source', key: 'source', width: 70 },
  ]

  return (
    <div>
      {/* 页头 */}
      <div className="page-title-bar">
        <div>
          <h2>LLM 用量统计</h2>
          <div className="page-desc">
            监控全平台 Token 消耗与成本，支持按用户、任务类型、平台维度分析
            <Tooltip title="成本估算基于 config.MODEL_PRICING 配置的模型单价，未配置时成本为 0">
              <InfoCircleOutlined style={{ marginLeft: 6, color: '#94A3B8' }} />
            </Tooltip>
          </div>
        </div>
        <Space>
          <Select value={days} onChange={setDays} style={{ width: 120 }}>
            <Select.Option value={7}>最近7天</Select.Option>
            <Select.Option value={14}>最近14天</Select.Option>
            <Select.Option value={30}>最近30天</Select.Option>
            <Select.Option value={90}>最近90天</Select.Option>
          </Select>
          <Tooltip title="用量导出功能开发中，敬请期待">
            <Button icon={<DownloadOutlined />} onClick={handleExport} disabled>导出Excel</Button>
          </Tooltip>
          <Button icon={<ReloadOutlined />} onClick={loadAll} loading={loading}>刷新</Button>
        </Space>
      </div>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        {statCards.map((card, i) => (
          <Col xs={12} sm={6} key={i}>
            <div className="stat-card-gradient animate-fade-in-up" style={{ background: card.gradient, animationDelay: `${i * 50}ms` }}>
              <div className="stat-label">{card.label}</div>
              <div className="stat-value">{card.value}</div>
              <div className="stat-sub">{card.sub}</div>
            </div>
          </Col>
        ))}
      </Row>

      {/* 趋势图 + 任务类型分布 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={24} lg={14}>
          <div className="geo-card">
            <h3 style={{ marginBottom: 16, fontSize: 16, fontWeight: 600 }}>Token 消耗趋势</h3>
            {trend.length ? (
              <ReactECharts option={trendOption} style={{ height: 300 }} />
            ) : (
              <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94A3B8' }}>
                暂无数据
              </div>
            )}
          </div>
        </Col>
        <Col xs={24} lg={10}>
          <div className="geo-card">
            <h3 style={{ marginBottom: 16, fontSize: 16, fontWeight: 600 }}>任务类型 Token 分布</h3>
            {byTaskType.length ? (
              <ReactECharts option={taskTypeOption} style={{ height: 300 }} />
            ) : (
              <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94A3B8' }}>
                暂无数据
              </div>
            )}
          </div>
        </Col>
      </Row>

      {/* 平台对比 + 用户排行 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={24} lg={14}>
          <div className="geo-card">
            <h3 style={{ marginBottom: 16, fontSize: 16, fontWeight: 600 }}>各平台调用对比</h3>
            <Table
              dataSource={byPlatform}
              columns={platformColumns}
              rowKey="platform"
              size="small"
              pagination={false}
              locale={{ emptyText: <Empty description="暂无数据" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
            />
          </div>
        </Col>
        <Col xs={24} lg={10}>
          <div className="geo-card">
            <h3 style={{ marginBottom: 16, fontSize: 16, fontWeight: 600 }}>用户 Token 消耗排行</h3>
            <Table
              dataSource={byUser}
              columns={userColumns}
              rowKey="user_id"
              size="small"
              pagination={false}
              locale={{ emptyText: <Empty description="暂无数据" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
            />
          </div>
        </Col>
      </Row>

      {/* 详细日志 */}
      <div className="geo-card">
        <h3 style={{ marginBottom: 16, fontSize: 16, fontWeight: 600 }}>LLM 调用详细日志</h3>
        <Table
          dataSource={logs.items}
          columns={logColumns}
          rowKey="id"
          size="small"
          loading={loading}
          pagination={{
            current: logPage,
            pageSize: 20,
            total: logs.total,
            onChange: (page) => setLogPage(page),
            showSizeChanger: false,
            showTotal: (total) => `共 ${total} 条`,
          }}
          locale={{ emptyText: <Empty description="暂无调用记录" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
          scroll={{ x: 1000 }}
        />
      </div>
    </div>
  )
}

export default UsageDashboard

