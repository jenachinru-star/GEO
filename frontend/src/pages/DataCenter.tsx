import { useEffect, useRef, useState } from 'react'
import { Row, Col, Table, Tag, Button, Statistic, message, Drawer, Descriptions, Empty, Spin, Select } from 'antd'
import { ReloadOutlined, EyeOutlined, InfoCircleOutlined, DownloadOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { geoApi, exportApi, taskApi } from '@/api'
import { PLATFORM_NAMES } from '@/store/useStore'

const DataCenter = () => {
  const [overview, setOverview] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [drawerVisible, setDrawerVisible] = useState(false)
  const [detail, setDetail] = useState<any>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [expandedRaw, setExpandedRaw] = useState<string | null>(null)
  const [trendDays, setTrendDays] = useState(7)
  const [trendData, setTrendData] = useState<any>(null)
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // 组件卸载时清理轮询定时器，避免内存泄漏
  useEffect(() => {
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current)
    }
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const res: any = await geoApi.getOverview()
      setOverview(res.data)
    } catch (e) {
      // 拦截器已提示
    } finally {
      setLoading(false)
    }
  }

  const loadTrend = async (days: number) => {
    try {
      const res: any = await geoApi.getTrend(days)
      setTrendData(res.data)
    } catch (e) {}
  }

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    loadTrend(trendDays)
  }, [trendDays])

  const handleRefresh = async () => {
    setRefreshing(true)
    const loadingKey = 'geo_refresh'
    try {
      const res: any = await geoApi.refresh()
      const taskId = res.data?.task_id
      if (!taskId) {
        message.warning('任务已提交，但未获取到任务ID')
        setRefreshing(false)
        return
      }
      // 后端是异步任务：POST 只返回 task_id，真正的采集在 worker 后台执行
      // 这里只提示"已提交"，然后轮询任务状态，等任务真正完成后再报结果
      message.success({ content: `数据采集已开始，可在任务中心查看进度`, key: loadingKey, duration: 3 })

      let pollCount = 0
      const maxPolls = 300 // 10秒一次 × 300次 = 50分钟上限
      // 启动前先清除旧定时器，防止重复点击导致多个轮询并发
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
        pollTimerRef.current = null
      }
      pollTimerRef.current = setInterval(async () => {
        pollCount++
        try {
          const taskRes: any = await taskApi.get(taskId)
          const task = taskRes.data
          if (task.status === 'succeeded') {
            if (pollTimerRef.current) clearInterval(pollTimerRef.current)
            const success = task.result?.success ?? 0
            const total = task.result?.total ?? 0
            message.success({ content: `采集完成：${success}/${total} 个语义`, key: loadingKey })
            loadData()
            setRefreshing(false)
          } else if (task.status === 'failed') {
            if (pollTimerRef.current) clearInterval(pollTimerRef.current)
            message.error({ content: task.error_message || '采集失败', key: loadingKey })
            setRefreshing(false)
          } else if (pollCount >= maxPolls) {
            if (pollTimerRef.current) clearInterval(pollTimerRef.current)
            message.warning({ content: '采集任务超时，请在任务中心查看', key: loadingKey })
            setRefreshing(false)
          }
        } catch (e) {
          // 单次查询失败不中断，继续轮询
        }
      }, 10000)
    } catch (e: any) {
      message.error({ content: e?.response?.data?.detail || '采集失败', key: loadingKey })
      setRefreshing(false)
    }
  }

  const handleViewDetail = async (semanticId: number) => {
    setDrawerVisible(true)
    setDetailLoading(true)
    setExpandedRaw(null)
    try {
      const res: any = await geoApi.getSemanticDetail(semanticId)
      setDetail(res.data)
    } catch (e) {
      //
    } finally {
      setDetailLoading(false)
    }
  }

  const toggleRawAnswer = (platformCode: string) => {
    setExpandedRaw(expandedRaw === platformCode ? null : platformCode)
  }

  // 趋势图
  const trendOption = trendData?.dates?.length ? {
    tooltip: { trigger: 'axis' },
    legend: { data: ['GEO推荐率', 'AEO引用率'], bottom: 0 },
    grid: { left: 40, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'category',
      data: trendData.dates.map((d: string) => d.slice(5)),
      axisLine: { lineStyle: { color: '#CBD5E1' } }
    },
    yAxis: { type: 'value', name: '%', max: 100, splitLine: { lineStyle: { color: '#F1F5F9' } } },
    series: [
      { name: 'GEO推荐率', type: 'line', smooth: true, data: trendData.geo_rates, itemStyle: { color: '#2563EB' }, areaStyle: { color: 'rgba(37,99,235,0.1)' } },
      { name: 'AEO引用率', type: 'line', smooth: true, data: trendData.aeo_rates, itemStyle: { color: '#8B5CF6' }, areaStyle: { color: 'rgba(139,92,246,0.1)' } },
    ]
  } : {}

  const columns = [
    { title: '语义问题', dataIndex: 'question', key: 'question', ellipsis: true },
    { title: 'GEO推荐率', dataIndex: 'geo_rate', key: 'geo_rate', width: 110,
      render: (v: number) => <span style={{ color: v >= 50 ? '#10B981' : v >= 20 ? '#F59E0B' : '#EF4444', fontWeight: 600 }}>{v}%</span> },
    { title: 'AEO引用率', dataIndex: 'aeo_rate', key: 'aeo_rate', width: 110,
      render: (v: number) => <span style={{ color: v >= 30 ? '#8B5CF6' : '#94A3B8', fontWeight: 600 }}>{v}%</span> },
    { title: '最佳GEO排名', dataIndex: 'best_rank', key: 'best_rank', width: 100,
      render: (r: number) => r > 0 ? <Tag color="green">第{r}名</Tag> : <Tag color="default">未推荐</Tag> },
    { title: '状态', dataIndex: 'is_active', key: 'is_active', width: 80,
      render: (v: boolean) => v ? <Tag color="blue">监测中</Tag> : <Tag>已停用</Tag> },
    { title: '操作', key: 'action', width: 100,
      render: (_: any, record: any) => (
        <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleViewDetail(record.semantic_id)}>详情</Button>
      ) },
  ]

  return (
    <div>
      <div className="page-title-bar">
        <div>
          <h2>GEO/AEO 数据中心</h2>
          <div className="page-desc">
            监测您在各AI平台的被推荐率(GEO)和被引用率(AEO)
            <span style={{ marginLeft: 8 }}>
              <Tag color="orange" icon={<InfoCircleOutlined />}>数据基于AI回答解析，仅供参考</Tag>
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button icon={<DownloadOutlined />} onClick={() => exportApi.exportDoctorReport()} disabled={!overview}>
            导出报告
          </Button>
          <Button type="primary" icon={<ReloadOutlined />} onClick={handleRefresh} loading={refreshing} className="btn-primary-gradient">
            手动刷新采集
          </Button>
        </div>
      </div>

      {/* 指标卡 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={12} sm={6}>
          <div className="geo-card" style={{ padding: 20 }}>
            <Statistic title="GEO推荐率" value={overview?.overall_geo_rate ?? 0} suffix="%" valueStyle={{ color: '#2563EB', fontWeight: 700 }} />
          </div>
        </Col>
        <Col xs={12} sm={6}>
          <div className="geo-card" style={{ padding: 20 }}>
            <Statistic title="AEO引用率" value={overview?.overall_aeo_rate ?? 0} suffix="%" valueStyle={{ color: '#8B5CF6', fontWeight: 700 }} />
          </div>
        </Col>
        <Col xs={12} sm={6}>
          <div className="geo-card" style={{ padding: 20 }}>
            <Statistic title="监测语义数" value={overview?.active_semantics ?? 0} suffix={`/ ${overview?.total_semantics ?? 0}`} valueStyle={{ fontWeight: 700 }} />
          </div>
        </Col>
        <Col xs={12} sm={6}>
          <div className="geo-card" style={{ padding: 20 }}>
            <Statistic title="最后刷新" value={overview?.last_refresh || '从未'} valueStyle={{ fontSize: 16, fontWeight: 600 }} />
          </div>
        </Col>
      </Row>

      {/* 趋势图 */}
      <div className="geo-card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>近{trendDays}天 GEO/AEO 趋势</h3>
          <Select
            value={trendDays}
            onChange={setTrendDays}
            style={{ width: 100 }}
            size="small"
            options={[
              { value: 7, label: '近7天' },
              { value: 30, label: '近30天' },
            ]}
          />
        </div>
        {trendData?.dates?.length ? (
          <ReactECharts option={trendOption} style={{ height: 280 }} />
        ) : (
          <Empty description="暂无趋势数据，点击右上角手动刷新" style={{ height: 200, padding: 40 }} />
        )}
      </div>

      {/* 语义数据表 */}
      <div className="geo-card">
        <h3 style={{ marginBottom: 16, fontSize: 16, fontWeight: 600 }}>各语义 GEO/AEO 表现</h3>
        <Table
          dataSource={overview?.semantic_stats || []}
          columns={columns}
          rowKey="semantic_id"
          loading={loading}
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: '暂无数据，请先完善Profile并刷新' }}
        />
      </div>

      {/* 详情抽屉 */}
      <Drawer title="语义详情" placement="right" width={600} open={drawerVisible} onClose={() => setDrawerVisible(false)}>
        <Spin spinning={detailLoading}>
          {detail && (
            <div>
              <Descriptions column={1} size="small" style={{ marginBottom: 16 }}>
                <Descriptions.Item label="语义问题">{detail.question}</Descriptions.Item>
                <Descriptions.Item label="最后刷新">{detail.last_refresh || '从未'}</Descriptions.Item>
              </Descriptions>

              <h4 style={{ marginBottom: 12, fontSize: 15, fontWeight: 600 }}>各平台检测结果</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {detail.platform_details?.length ? detail.platform_details.map((p: any, idx: number) => {
                  const platformName = PLATFORM_NAMES[p.platform_code] || p.platform_code
                  const isGeo = p.geo_mentioned
                  const isAeo = p.aeo_cited
                  // 状态判断：AEO引用 > GEO推荐 > 未提及
                  let statusLabel: string, statusColor: string, bgColor: string
                  if (isAeo) {
                    statusLabel = '已引用为唯一答案'
                    statusColor = '#2563EB'
                    bgColor = '#EFF6FF'
                  } else if (isGeo) {
                    statusLabel = `已推荐，排名第${p.geo_rank}`
                    statusColor = '#10B981'
                    bgColor = '#ECFDF5'
                  } else {
                    statusLabel = '未提及'
                    statusColor = '#EF4444'
                    bgColor = '#FEF2F2'
                  }
                  return (
                    <div key={p.platform_code} style={{
                      background: bgColor, padding: '16px 18px', borderRadius: 12,
                      borderLeft: `3px solid ${statusColor}`
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                        <div style={{ fontSize: 15, fontWeight: 600 }}>
                          <span style={{ color: '#94A3B8', marginRight: 8 }}>{String(idx + 1).padStart(2, '0')}</span>
                          {platformName}
                        </div>
                        <span style={{ fontSize: 12, fontWeight: 600, color: statusColor }}>{statusLabel}</span>
                      </div>
                      <div style={{ fontSize: 13, color: '#64748B', lineHeight: 1.6, marginBottom: 8 }}>
                        {isAeo ? 'AI在回答中直接引用该医生为推荐答案，未列出其他竞品。' :
                         isGeo ? `AI在回答中将该医生列入推荐列表，排名第${p.geo_rank}位。` :
                         'AI回答中未提及该医生，给出的是通用就医建议。'}
                      </div>
                      {p.raw_answer && (
                        <div>
                          <Button type="link" size="small" style={{ padding: 0 }} onClick={() => toggleRawAnswer(p.platform_code)}>
                            {expandedRaw === p.platform_code ? '收起原始回答' : '查看原始回答'}
                          </Button>
                          {expandedRaw === p.platform_code && (
                            <div style={{
                              marginTop: 8, padding: 12, background: '#fff', borderRadius: 8,
                              fontSize: 12, color: '#475569', lineHeight: 1.7, maxHeight: 200, overflow: 'auto',
                              whiteSpace: 'pre-wrap'
                            }}>
                              {p.raw_answer}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )
                }) : (
                  <Empty description="暂无平台检测数据，请先手动刷新采集" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                )}
              </div>
            </div>
          )}
        </Spin>
      </Drawer>
    </div>
  )
}

export default DataCenter
