import { useEffect, useState } from 'react'
import { Row, Col, Button, Space, Empty } from 'antd'
import {
  ReloadOutlined,
  DownloadOutlined,
  ArrowRightOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import ReactECharts from 'echarts-for-react'
import { dashboardApi, exportApi, geoApi } from '@/api'

const Dashboard = () => {
  const [stats, setStats] = useState<any>(null)
  const [semanticStats, setSemanticStats] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const loadData = async () => {
    setLoading(true)
    try {
      const [statsRes, overviewRes] = await Promise.all([
        dashboardApi.getDoctorStats(),
        geoApi.getOverview()
      ])
      setStats(statsRes.data)
      setSemanticStats(overviewRes.data.semantic_stats || [])
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

  // 语义表现概览：GEO推荐率最高前3 + AEO引用率最高前3
  const topGeo = [...semanticStats].sort((a, b) => b.geo_rate - a.geo_rate).slice(0, 3)
  const topAeo = [...semanticStats].sort((a, b) => b.aeo_rate - a.aeo_rate).slice(0, 3)

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

      {/* 语义表现概览 */}
      <div className="geo-card" style={{ marginTop: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>语义表现概览</div>
          <Button type="link" onClick={() => navigate('/data')}>
            查看全部 <ArrowRightOutlined />
          </Button>
        </div>
        <Row gutter={20}>
          {/* GEO推荐率最高 */}
          <Col xs={24} md={12}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#2563EB', marginBottom: 10 }}>
              📈 GEO推荐率最高
            </div>
            {topGeo.length === 0 ? (
              <Empty description="暂无监测数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {topGeo.map((s: any, i: number) => (
                  <div key={s.semantic_id} style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '10px 14px', background: '#F8FAFC', borderRadius: 10
                  }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <span style={{ fontSize: 12, color: '#94A3B8', marginRight: 8 }}>{i + 1}</span>
                      <span style={{ fontSize: 13 }}>{s.question}</span>
                    </div>
                    <span style={{ fontSize: 14, fontWeight: 700, color: '#2563EB', marginLeft: 12 }}>
                      {s.geo_rate}%
                    </span>
                  </div>
                ))}
              </div>
            )}
          </Col>
          {/* AEO引用率最高 */}
          <Col xs={24} md={12}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#8B5CF6', marginBottom: 10 }}>
              🎯 AEO引用率最高
            </div>
            {topAeo.length === 0 ? (
              <Empty description="暂无监测数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {topAeo.map((s: any, i: number) => (
                  <div key={s.semantic_id} style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '10px 14px', background: '#F8FAFC', borderRadius: 10
                  }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <span style={{ fontSize: 12, color: '#94A3B8', marginRight: 8 }}>{i + 1}</span>
                      <span style={{ fontSize: 13 }}>{s.question}</span>
                    </div>
                    <span style={{ fontSize: 14, fontWeight: 700, color: '#8B5CF6', marginLeft: 12 }}>
                      {s.aeo_rate}%
                    </span>
                  </div>
                ))}
              </div>
            )}
          </Col>
        </Row>
      </div>
    </div>
  )
}

export default Dashboard
