import { useEffect, useState } from 'react'
import { Row, Col, Table, Tag, Button, Space } from 'antd'
import {
  ReloadOutlined,
  DownloadOutlined
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { dashboardApi, exportApi } from '@/api'

const Dashboard = () => {
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const loadData = async () => {
    setLoading(true)
    try {
      const res: any = await dashboardApi.getDoctorStats()
      setStats(res.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  // 趋势图配置（GEO率+AEO率双线）
  const trendOption = stats?.trend_7days?.length ? {
    tooltip: { trigger: 'axis' },
    legend: { data: ['GEO推荐率', 'AEO引用率'], bottom: 0 },
    grid: { left: 40, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'category',
      data: stats.trend_7days.map((d: any) => d.date.slice(5)),
      axisLine: { lineStyle: { color: '#CBD5E1' } }
    },
    yAxis: {
      type: 'value',
      name: '%',
      max: 100,
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#F1F5F9' } }
    },
    series: [
      {
        name: 'GEO推荐率',
        type: 'line',
        smooth: true,
        data: stats.trend_7days.map((d: any) => d.geo_rate),
        itemStyle: { color: '#2563EB' },
        areaStyle: { color: 'rgba(37,99,235,0.1)' }
      },
      {
        name: 'AEO引用率',
        type: 'line',
        smooth: true,
        data: stats.trend_7days.map((d: any) => d.aeo_rate),
        itemStyle: { color: '#8B5CF6' },
        areaStyle: { color: 'rgba(139,92,246,0.1)' }
      }
    ]
  } : {}

  // 平台环形图（各平台GEO率）
  const platformOption = stats?.platform_stats?.length ? {
    tooltip: { trigger: 'item', formatter: '{b}: {c}%' },
    legend: { bottom: 0, left: 'center' },
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: false,
      label: { show: true, formatter: '{b}\n{c}%' },
      data: stats.platform_stats.map((p: any) => ({
        name: p.name,
        value: p.geo_rate,
        itemStyle: { color: p.code === 'deepseek' ? '#2563EB' : p.code === 'glm' ? '#8B5CF6' : p.code === 'minimax' ? '#10B981' : '#F59E0B' }
      }))
    }]
  } : {}

  const rankColumns = [
    { title: '语义问题', dataIndex: 'question', key: 'question', ellipsis: true },
    { title: 'GEO率', dataIndex: 'geo_rate', key: 'geo_rate', width: 80,
      render: (v: number) => <span style={{ color: v >= 50 ? '#10B981' : v >= 20 ? '#F59E0B' : '#EF4444', fontWeight: 600 }}>{v}%</span> },
    { title: 'AEO率', dataIndex: 'aeo_rate', key: 'aeo_rate', width: 80,
      render: (v: number) => <span style={{ color: v >= 30 ? '#8B5CF6' : '#94A3B8', fontWeight: 600 }}>{v}%</span> },
    { title: '最佳排名', dataIndex: 'best_rank', key: 'best_rank', width: 80,
      render: (r: number) => r > 0 ? <span style={{ color: '#10B981', fontWeight: 600 }}>第{r}名</span> : <span style={{ color: '#94A3B8' }}>未推荐</span> }
  ]

  return (
    <div>
      <div className="page-title-bar">
        <div>
          <h2>数据概览</h2>
          <div className="page-desc">实时监控您的GEO/AEO表现，追踪AI推荐与引用趋势</div>
        </div>
        <Space>
          <Button icon={<DownloadOutlined />} onClick={() => exportApi.exportReport()}>
            导出报告
          </Button>
          <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>刷新数据</Button>
        </Space>
      </div>

      {/* 核心指标卡 - 渐变背景 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={12} sm={6}>
          <div className="stat-card-gradient animate-fade-in-up" style={{ background: 'var(--primary-gradient)', animationDelay: '0ms' }}>
            <div className="stat-label">我的GEO推荐率</div>
            <div className="stat-value">{stats?.overall_geo_rate ?? 0}%</div>
            <div className="stat-sub">AI平台被推荐占比</div>
          </div>
        </Col>
        <Col xs={12} sm={6}>
          <div className="stat-card-gradient animate-fade-in-up" style={{ background: 'var(--purple-gradient)', animationDelay: '50ms' }}>
            <div className="stat-label">我的AEO引用率</div>
            <div className="stat-value">{stats?.overall_aeo_rate ?? 0}%</div>
            <div className="stat-sub">被引用为答案占比</div>
          </div>
        </Col>
        <Col xs={12} sm={6}>
          <div className="stat-card-gradient animate-fade-in-up" style={{ background: 'var(--success-gradient)', animationDelay: '100ms' }}>
            <div className="stat-label">活跃语义数</div>
            <div className="stat-value">
              {stats?.active_semantics ?? 0}
              <span style={{ fontSize: 16, opacity: 0.8, marginLeft: 4 }}>/ {stats?.total_semantics ?? 0}</span>
            </div>
            <div className="stat-sub">监测中语义</div>
          </div>
        </Col>
        <Col xs={12} sm={6}>
          <div className="stat-card-gradient animate-fade-in-up" style={{ background: 'var(--warning-gradient)', animationDelay: '150ms' }}>
            <div className="stat-label">已生成文章</div>
            <div className="stat-value">{stats?.article_count ?? 0}</div>
            <div className="stat-sub">内容资产</div>
          </div>
        </Col>
      </Row>

      {/* 图表区 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={24} lg={14}>
          <div className="geo-card">
            <h3 style={{ marginBottom: 16, fontSize: 16, fontWeight: 600 }}>近7天 GEO/AEO 趋势</h3>
            {stats?.trend_7days?.length ? (
              <ReactECharts option={trendOption} style={{ height: 280 }} />
            ) : (
              <div style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94A3B8' }}>
                暂无数据，请先到数据中心触发采集
              </div>
            )}
          </div>
        </Col>
        <Col xs={24} lg={10}>
          <div className="geo-card">
            <h3 style={{ marginBottom: 16, fontSize: 16, fontWeight: 600 }}>各平台GEO推荐率</h3>
            {stats?.platform_stats?.length ? (
              <ReactECharts option={platformOption} style={{ height: 280 }} />
            ) : (
              <div style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94A3B8' }}>
                暂无数据
              </div>
            )}
          </div>
        </Col>
      </Row>

      {/* 排名列表 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <div className="geo-card">
            <h3 style={{ marginBottom: 16, fontSize: 16, fontWeight: 600, color: '#10B981' }}>
              GEO表现最好 Top5
            </h3>
            <Table
              dataSource={stats?.top_semantics || []}
              columns={rankColumns}
              rowKey="semantic_id"
              size="small"
              pagination={false}
              locale={{ emptyText: '暂无数据' }}
            />
          </div>
        </Col>
        <Col xs={24} lg={12}>
          <div className="geo-card">
            <h3 style={{ marginBottom: 16, fontSize: 16, fontWeight: 600, color: '#EF4444' }}>
              需重点优化语义
            </h3>
            <Table
              dataSource={stats?.bottom_semantics || []}
              columns={rankColumns}
              rowKey="semantic_id"
              size="small"
              pagination={false}
              locale={{ emptyText: '暂无数据' }}
            />
          </div>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard
