import { useState, useEffect } from 'react'
import {
  Card, Row, Col, Statistic, Button, Table, Tag, message,
  Space, Empty, Select
} from 'antd'
import {
  ReloadOutlined, ArrowUpOutlined, ArrowDownOutlined,
  FileTextOutlined, EyeOutlined, LikeOutlined, ShareAltOutlined,
  ThunderboltOutlined, FileExcelOutlined
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import request, { exportApi } from '@/api'
import { useParams, useNavigate } from 'react-router-dom'

const WechatAccountStats = () => {
  const { accountId } = useParams()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [collecting, setCollecting] = useState(false)
  const [overview, setOverview] = useState<any>(null)
  const [trendData, setTrendData] = useState<any>(null)
  const [articles, setArticles] = useState<any[]>([])
  const [articlesTotal, setArticlesTotal] = useState(0)
  const [articlesPage, setArticlesPage] = useState(1)
  const [trendDays, setTrendDays] = useState(30)

  const loadOverview = async () => {
    try {
      const res: any = await request.get(`/publish-accounts/${accountId}/stats/overview`)
      // 响应拦截器已返回body，res即 {code, message, data}
      setOverview(res.data)
    } catch (e) {
      // 错误已由拦截器处理
    }
  }

  const loadTrend = async (days = 30) => {
    try {
      const res: any = await request.get(`/publish-accounts/${accountId}/stats/trend`, {
        params: { days }
      })
      setTrendData(res.data)
    } catch (e) {
      // 错误已由拦截器处理
    }
  }

  const loadArticles = async (page = 1) => {
    setLoading(true)
    try {
      const res: any = await request.get(`/publish-accounts/${accountId}/articles`, {
        params: { page, page_size: 10 }
      })
      setArticles(res.data?.items || [])
      setArticlesTotal(res.data?.total || 0)
      setArticlesPage(page)
    } catch (e) {
      // 错误已由拦截器处理
    } finally {
      setLoading(false)
    }
  }

  const handleCollect = async () => {
    setCollecting(true)
    try {
      await request.post(`/publish-accounts/${accountId}/stats/collect`, null, {
        params: { days: 7 }
      })
      message.success('采集任务已提交，约1-2分钟后完成')
      // 5秒后开始轮询刷新
      setTimeout(() => {
        loadOverview()
        loadTrend(trendDays)
        loadArticles(1)
      }, 5000)
    } catch (e) {
      // 错误已由拦截器处理
    } finally {
      setCollecting(false)
    }
  }

  useEffect(() => {
    if (accountId) {
      loadOverview()
      loadTrend(30)
      loadArticles(1)
    }
  }, [accountId])

  // 粉丝趋势图配置
  const fanTrendOption = trendData ? {
    title: { text: '粉丝数趋势', left: 'center' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['累计粉丝', '新增粉丝', '净增'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: trendData.dates, axisLabel: { rotate: 45 } },
    yAxis: [
      { type: 'value', name: '累计粉丝' },
      { type: 'value', name: '新增/净增' }
    ],
    series: [
      { name: '累计粉丝', type: 'line', data: trendData.cumulate_users, smooth: true, yAxisIndex: 0 },
      { name: '新增粉丝', type: 'bar', data: trendData.new_users, yAxisIndex: 1 },
      { name: '净增', type: 'line', data: trendData.net_growth, smooth: true, yAxisIndex: 1 },
    ]
  } : {}

  // 阅读趋势图配置
  const readTrendOption = trendData ? {
    title: { text: '文章阅读趋势', left: 'center' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['总阅读量', '发文数', '平均阅读'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: trendData.dates, axisLabel: { rotate: 45 } },
    yAxis: [
      { type: 'value', name: '阅读量' },
      { type: 'value', name: '发文数' }
    ],
    series: [
      { name: '总阅读量', type: 'line', data: trendData.total_reads, smooth: true, areaStyle: {}, yAxisIndex: 0 },
      { name: '发文数', type: 'bar', data: trendData.total_articles, yAxisIndex: 1 },
      { name: '平均阅读', type: 'line', data: trendData.avg_reads, smooth: true, yAxisIndex: 0 },
    ]
  } : {}

  const articleColumns = [
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true, width: '30%' },
    { title: '发布日期', dataIndex: 'publish_date', key: 'publish_date', width: 100 },
    { title: '阅读量', dataIndex: 'reads', key: 'reads', width: 80, render: (v: number) => <span><EyeOutlined /> {v}</span> },
    { title: '点赞', dataIndex: 'likes', key: 'likes', width: 70, render: (v: number) => <span><LikeOutlined /> {v}</span> },
    { title: '分享', dataIndex: 'shares', key: 'shares', width: 70, render: (v: number) => <span><ShareAltOutlined /> {v}</span> },
    { title: '收藏', dataIndex: 'favorites', key: 'favorites', width: 70 },
    {
      title: '操作', key: 'action', width: 170,
      render: (_: any, record: any) => (
        <Space size="small">
          <Button
            type="link" size="small"
            onClick={() => navigate(`/publish-accounts/${accountId}/articles/${record.id}`)}
          >
            详情
          </Button>
          <Button
            type="link" size="small"
            icon={<ThunderboltOutlined />}
            onClick={() => navigate(`/publish-accounts/${accountId}/articles/${record.id}`)}
          >
            AI分析
          </Button>
        </Space>
      )
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Space style={{ marginBottom: 16 }}>
        <Button onClick={() => navigate(-1)}>返回</Button>
        <Button
          type="primary"
          icon={<ReloadOutlined />}
          loading={collecting}
          onClick={handleCollect}
        >
          手动采集数据（最近7天）
        </Button>
      </Space>

      {overview && !overview.has_data ? (
        <Empty description={overview.message || '暂无数据'}>
          <Button type="primary" onClick={handleCollect}>立即采集</Button>
        </Empty>
      ) : (
        <>
          {/* 数据概览卡片 */}
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col xs={12} sm={6}>
              <Card>
                <Statistic title="累计粉丝" value={overview?.cumulate_users || 0} />
                <div style={{ marginTop: 8, fontSize: 12 }}>
                  {overview?.today_net_growth >= 0 ? (
                    <Tag color="green"><ArrowUpOutlined /> 今日+{overview?.today_net_growth}</Tag>
                  ) : (
                    <Tag color="red"><ArrowDownOutlined /> 今日{overview?.today_net_growth}</Tag>
                  )}
                </div>
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card>
                <Statistic title="今日发文" value={overview?.today_articles || 0} prefix={<FileTextOutlined />} />
                <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
                  本月共 {overview?.month_articles || 0} 篇
                </div>
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card>
                <Statistic title="今日阅读量" value={overview?.today_reads || 0} prefix={<EyeOutlined />} />
                <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
                  平均阅读 {overview?.today_avg_reads?.toFixed(0) || 0}
                </div>
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card>
                <Statistic title="本月总阅读" value={overview?.month_reads || 0} prefix={<EyeOutlined />} />
                <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
                  平均阅读 {overview?.month_avg_reads?.toFixed(0) || 0}
                </div>
              </Card>
            </Col>
          </Row>

          {/* 30天汇总 */}
          <Card title="近30天汇总" style={{ marginBottom: 24 }}>
            <Row gutter={16}>
              <Col span={4}><Statistic title="新增粉丝" value={overview?.month_new_users || 0} /></Col>
              <Col span={4}><Statistic title="取关" value={overview?.month_cancel_users || 0} /></Col>
              <Col span={4}><Statistic title="净增" value={overview?.month_net_growth || 0} /></Col>
              <Col span={4}><Statistic title="发文数" value={overview?.month_articles || 0} /></Col>
              <Col span={4}><Statistic title="总分享" value={overview?.month_shares || 0} /></Col>
              <Col span={4}><Statistic title="总点赞" value={overview?.month_likes || 0} /></Col>
            </Row>
          </Card>

          {/* 趋势图 */}
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col xs={24} lg={12}>
              <Card
                title="粉丝趋势"
                extra={
                  <Select value={trendDays} onChange={(v) => { setTrendDays(v); loadTrend(v) }} style={{ width: 100 }}>
                    <Select.Option value={7}>近7天</Select.Option>
                    <Select.Option value={30}>近30天</Select.Option>
                    <Select.Option value={90}>近90天</Select.Option>
                  </Select>
                }
              >
                <ReactECharts option={fanTrendOption} style={{ height: 300 }} />
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="阅读趋势">
                <ReactECharts option={readTrendOption} style={{ height: 300 }} />
              </Card>
            </Col>
          </Row>

          {/* 文章列表 */}
          <Card
            title="已发布文章"
            extra={
              <Button
                type="primary"
                ghost
                icon={<FileExcelOutlined />}
                onClick={() => exportApi.exportWechatArticles(accountId as string)}
              >
                导出Excel
              </Button>
            }
          >
            <Table
              columns={articleColumns}
              dataSource={articles}
              rowKey="id"
              loading={loading}
              pagination={{
                current: articlesPage,
                pageSize: 10,
                total: articlesTotal,
                onChange: (page) => loadArticles(page),
              }}
            />
          </Card>
        </>
      )}
    </div>
  )
}

export default WechatAccountStats
