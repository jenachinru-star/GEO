import { useState, useEffect, useRef } from 'react'
import {
  Card, Row, Col, Statistic, Button, Select, Table, Tag, Tabs,
  Space, Empty, Spin, message, Alert, List, Badge
} from 'antd'
import {
  ThunderboltOutlined, ArrowUpOutlined, ArrowDownOutlined,
  EyeOutlined, LikeOutlined, ShareAltOutlined, ReloadOutlined
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import request from '@/api'

const CompetitorAnalysis = () => {
  const [ownAccounts, setOwnAccounts] = useState<any[]>([])
  const [benchmarks, setBenchmarks] = useState<any[]>([])
  const [ownAccountId, setOwnAccountId] = useState<number | null>(null)
  const [benchmarkId, setBenchmarkId] = useState<number | null>(null)
  const [comparison, setComparison] = useState<any>(null)
  const [analysis, setAnalysis] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const pollRef = useRef<number | null>(null)

  // 加载自己的微信公众号账号列表
  const loadOwnAccounts = async () => {
    try {
      const res: any = await request.get('/publish-accounts', { params: { platform: 'wechat' } })
      setOwnAccounts(res.data?.items || [])
    } catch (e) {
      // 错误已由拦截器处理
    }
  }

  // 加载对标账号列表
  const loadBenchmarks = async () => {
    try {
      const res: any = await request.get('/benchmark')
      setBenchmarks(res.data?.items || [])
    } catch (e) {
      // 错误已由拦截器处理
    }
  }

  useEffect(() => {
    loadOwnAccounts()
    loadBenchmarks()
  }, [])

  // 加载对比数据（规则计算，立即返回）
  const loadComparison = async () => {
    if (!ownAccountId || !benchmarkId) return
    setLoading(true)
    try {
      const res: any = await request.get('/benchmark/analysis/compare', {
        params: { account_id: ownAccountId, benchmark_id: benchmarkId }
      })
      setComparison(res.data)
    } catch (e) {
      // 错误已由拦截器处理
    } finally {
      setLoading(false)
    }
  }

  // 加载AI分析结果
  const loadAnalysis = async () => {
    if (!ownAccountId || !benchmarkId) return
    try {
      const res: any = await request.get('/benchmark/analysis', {
        params: { account_id: ownAccountId, benchmark_id: benchmarkId }
      })
      setAnalysis(res.data)
      if (res.data?.status === 'processing' || res.data?.status === 'pending') {
        // 继续轮询
        pollRef.current = window.setTimeout(() => loadAnalysis(), 3000)
      } else {
        setAnalyzing(false)
        if (pollRef.current) {
          clearTimeout(pollRef.current)
          pollRef.current = null
        }
      }
    } catch (e) {
      setAnalyzing(false)
    }
  }

  // 提交AI分析
  const handleAnalyze = async () => {
    if (!ownAccountId || !benchmarkId) {
      message.warning('请先选择自己的账号和对标账号')
      return
    }
    setAnalyzing(true)
    try {
      await request.post('/benchmark/analysis', null, {
        params: { account_id: ownAccountId, benchmark_id: benchmarkId }
      })
      message.success('分析任务已提交，约10-30秒后完成')
      // 开始轮询
      setTimeout(() => loadAnalysis(), 3000)
    } catch (e) {
      setAnalyzing(false)
    }
  }

  // 当选择变化时重新加载
  useEffect(() => {
    if (ownAccountId && benchmarkId) {
      loadComparison()
      loadAnalysis()
    }
    return () => {
      if (pollRef.current) {
        clearTimeout(pollRef.current)
        pollRef.current = null
      }
    }
  }, [ownAccountId, benchmarkId])

  // 差距标签渲染
  const GapTag = ({ value }: { value: number }) => {
    if (value > 0) return <Tag color="green" icon={<ArrowUpOutlined />}>领先 {value}%</Tag>
    if (value < 0) return <Tag color="red" icon={<ArrowDownOutlined />}>落后 {Math.abs(value)}%</Tag>
    return <Tag>持平</Tag>
  }

  // 发文频率对比柱状图
  const frequencyOption = comparison ? {
    title: { text: '关键指标对比', left: 'center' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['自己账号', '对标账号'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: ['粉丝数', '平均阅读', '平均点赞', '平均分享', '每周发文']
    },
    yAxis: { type: 'value' },
    series: [
      {
        name: '自己账号',
        type: 'bar',
        data: [
          comparison.own.followers,
          comparison.own.avg_reads,
          comparison.own.avg_likes,
          comparison.own.avg_shares,
          comparison.own.weekly_posts,
        ],
        itemStyle: { color: '#1890ff' }
      },
      {
        name: '对标账号',
        type: 'bar',
        data: [
          comparison.benchmark.followers,
          comparison.benchmark.avg_reads,
          comparison.benchmark.avg_likes,
          comparison.benchmark.avg_shares,
          comparison.benchmark.weekly_posts,
        ],
        itemStyle: { color: '#fa8c16' }
      }
    ]
  } : {}

  // 爆款文章列
  const articleColumns = [
    { title: '排名', key: 'rank', width: 50, render: (_: any, __: any, index: number) => index + 1 },
    { title: '文章标题', dataIndex: 'title', key: 'title', ellipsis: true },
    { title: '发布日期', dataIndex: 'publish_date', key: 'publish_date', width: 100 },
    { title: '阅读量', dataIndex: 'reads', key: 'reads', width: 80, render: (v: number) => <span><EyeOutlined /> {v?.toLocaleString() || 0}</span> },
    { title: '点赞', dataIndex: 'likes', key: 'likes', width: 70, render: (v: number) => <span><LikeOutlined /> {v || 0}</span> },
    { title: '分享', dataIndex: 'shares', key: 'shares', width: 70, render: (v: number) => <span><ShareAltOutlined /> {v || 0}</span> },
  ]

  // AI分析结果渲染
  const llm = analysis?.result?.llm_analysis
  const renderAnalysisContent = () => {
    if (!analysis || analysis.status === 'none') {
      return <Empty description="暂无AI分析结果，点击上方按钮开始分析" />
    }
    if (analysis.status === 'processing' || analysis.status === 'pending') {
      return (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: '#999' }}>AI分析中，约10-30秒...</div>
        </div>
      )
    }
    if (analysis.status === 'failed') {
      return <Alert type="error" message="分析失败" description={analysis.failed_reason || '未知错误'} showIcon />
    }
    if (!llm) {
      return <Empty description="分析结果为空" />
    }

    const tabItems = [
      {
        key: 'overall',
        label: '整体评估',
        children: (
          <div>
            <Alert
              type="info"
              showIcon
              message="整体评估"
              description={llm.overall_assessment || '暂无评估'}
              style={{ marginBottom: 16 }}
            />
            <Alert
              type="success"
              showIcon
              message="内容方向建议"
              description={llm.content_direction || '暂无建议'}
            />
          </div>
        )
      },
      {
        key: 'strengths',
        label: '自身优势',
        children: (
          <List
            size="large"
            bordered
            dataSource={llm.strengths || []}
            renderItem={(item: string) => (
              <List.Item>
                <Badge color="green" /> {item}
              </List.Item>
            )}
          />
        )
      },
      {
        key: 'weaknesses',
        label: '存在不足',
        children: (
          <List
            size="large"
            bordered
            dataSource={llm.weaknesses || []}
            renderItem={(item: string) => (
              <List.Item>
                <Badge color="red" /> {item}
              </List.Item>
            )}
          />
        )
      },
      {
        key: 'gap',
        label: '差距分析',
        children: (
          <Row gutter={[16, 16]}>
            <Col span={12}>
              <Card size="small" title="内容质量"><p style={{ margin: 0 }}>{llm.gap_analysis?.content_quality || '-'}</p></Card>
            </Col>
            <Col span={12}>
              <Card size="small" title="发文频率"><p style={{ margin: 0 }}>{llm.gap_analysis?.publishing_frequency || '-'}</p></Card>
            </Col>
            <Col span={12}>
              <Card size="small" title="互动率"><p style={{ margin: 0 }}>{llm.gap_analysis?.engagement || '-'}</p></Card>
            </Col>
            <Col span={12}>
              <Card size="small" title="粉丝规模"><p style={{ margin: 0 }}>{llm.gap_analysis?.audience_scale || '-'}</p></Card>
            </Col>
          </Row>
        )
      },
      {
        key: 'suggestions',
        label: '改进建议',
        children: (
          <List
            size="large"
            bordered
            dataSource={llm.improvement_suggestions || []}
            renderItem={(item: any) => (
              <List.Item>
                <List.Item.Meta
                  title={
                    <Space>
                      <Tag color={item.priority === 'high' ? 'red' : item.priority === 'medium' ? 'orange' : 'blue'}>
                        {item.priority === 'high' ? '高优先级' : item.priority === 'medium' ? '中优先级' : '低优先级'}
                      </Tag>
                      <span>{item.area}</span>
                    </Space>
                  }
                  description={
                    <div>
                      <p style={{ margin: '4px 0' }}>{item.suggestion}</p>
                      <p style={{ margin: 0, color: '#52c41a' }}>预期效果：{item.expected_effect}</p>
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        )
      },
    ]

    return <Tabs items={tabItems} />
  }

  return (
    <div style={{ padding: 24 }}>
      {/* 选择器 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col span={8}>
            <div style={{ fontWeight: 500, marginBottom: 8 }}>自己的公众号</div>
            <Select
              style={{ width: '100%' }}
              placeholder="选择自己的公众号账号"
              value={ownAccountId}
              onChange={setOwnAccountId}
              showSearch
              optionFilterProp="label"
              options={ownAccounts.map((a: any) => ({ label: a.account_name, value: a.id }))}
            />
          </Col>
          <Col span={8}>
            <div style={{ fontWeight: 500, marginBottom: 8 }}>对标账号</div>
            <Select
              style={{ width: '100%' }}
              placeholder="选择对标账号"
              value={benchmarkId}
              onChange={setBenchmarkId}
              showSearch
              optionFilterProp="label"
              options={benchmarks.map((b: any) => ({ label: b.account_name, value: b.id }))}
            />
          </Col>
          <Col span={8}>
            <Space>
              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                loading={analyzing}
                onClick={handleAnalyze}
                disabled={!ownAccountId || !benchmarkId}
              >
                {analyzing ? '分析中...' : 'AI差距分析'}
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={loadComparison}
                disabled={!ownAccountId || !benchmarkId}
              >
                刷新对比
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {!ownAccountId || !benchmarkId ? (
        <Empty description="请先选择自己的公众号和对标账号" style={{ padding: 60 }} />
      ) : (
        <Spin spinning={loading}>
          {/* 数据概览对比 */}
          {comparison && (
            <>
              <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                <Col xs={24} sm={12}>
                  <Card title={`自己账号：${comparison.own.account_name}`} style={{ borderTop: '3px solid #1890ff' }}>
                    <Row gutter={[16, 12]}>
                      <Col span={12}><Statistic title="粉丝数" value={comparison.own.followers} /></Col>
                      <Col span={12}><Statistic title="平均阅读" value={comparison.own.avg_reads} /></Col>
                      <Col span={12}><Statistic title="平均点赞" value={comparison.own.avg_likes} /></Col>
                      <Col span={12}><Statistic title="平均分享" value={comparison.own.avg_shares} /></Col>
                      <Col span={12}><Statistic title="每周发文" value={comparison.own.weekly_posts} /></Col>
                      <Col span={12}><Statistic title="近30天发文" value={comparison.own.total_articles_30d} /></Col>
                    </Row>
                  </Card>
                </Col>
                <Col xs={24} sm={12}>
                  <Card title={`对标账号：${comparison.benchmark.account_name}`} style={{ borderTop: '3px solid #fa8c16' }}>
                    <Row gutter={[16, 12]}>
                      <Col span={12}><Statistic title="粉丝数" value={comparison.benchmark.followers} /></Col>
                      <Col span={12}><Statistic title="平均阅读" value={comparison.benchmark.avg_reads} /></Col>
                      <Col span={12}><Statistic title="平均点赞" value={comparison.benchmark.avg_likes} /></Col>
                      <Col span={12}><Statistic title="平均分享" value={comparison.benchmark.avg_shares} /></Col>
                      <Col span={12}><Statistic title="每周发文" value={comparison.benchmark.weekly_posts} /></Col>
                      <Col span={12}>
                        <Statistic title="数据来源" value={comparison.benchmark.data_source === 'manual' ? '手动输入' : comparison.benchmark.data_source} />
                      </Col>
                    </Row>
                  </Card>
                </Col>
              </Row>

              {/* 差距百分比 */}
              <Card title="差距对比（正数领先，负数落后）" style={{ marginBottom: 16 }}>
                <Row gutter={16}>
                  <Col span={4}><div style={{ textAlign: 'center' }}><div style={{ fontSize: 12, color: '#999' }}>粉丝数</div><GapTag value={comparison.gaps.followers} /></div></Col>
                  <Col span={4}><div style={{ textAlign: 'center' }}><div style={{ fontSize: 12, color: '#999' }}>平均阅读</div><GapTag value={comparison.gaps.avg_reads} /></div></Col>
                  <Col span={4}><div style={{ textAlign: 'center' }}><div style={{ fontSize: 12, color: '#999' }}>平均点赞</div><GapTag value={comparison.gaps.avg_likes} /></div></Col>
                  <Col span={4}><div style={{ textAlign: 'center' }}><div style={{ fontSize: 12, color: '#999' }}>平均分享</div><GapTag value={comparison.gaps.avg_shares} /></div></Col>
                  <Col span={4}><div style={{ textAlign: 'center' }}><div style={{ fontSize: 12, color: '#999' }}>发文频率</div><GapTag value={comparison.gaps.weekly_posts} /></div></Col>
                </Row>
              </Card>

              {/* 柱状图对比 */}
              <Card title="关键指标对比图" style={{ marginBottom: 16 }}>
                <ReactECharts option={frequencyOption} style={{ height: 320 }} />
              </Card>

              {/* 爆款文章对比 */}
              <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col xs={24} lg={12}>
                  <Card title="自己账号爆款文章 Top5">
                    <Table
                      columns={articleColumns}
                      dataSource={comparison.own_top_articles || []}
                      rowKey="title"
                      pagination={false}
                      size="small"
                    />
                  </Card>
                </Col>
                <Col xs={24} lg={12}>
                  <Card title="对标账号爆款文章 Top5">
                    <Table
                      columns={articleColumns}
                      dataSource={comparison.benchmark_top_articles || []}
                      rowKey="title"
                      pagination={false}
                      size="small"
                    />
                  </Card>
                </Col>
              </Row>
            </>
          )}

          {/* AI差距分析结果 */}
          <Card title="AI差距分析">
            {renderAnalysisContent()}
          </Card>
        </Spin>
      )}
    </div>
  )
}

export default CompetitorAnalysis
