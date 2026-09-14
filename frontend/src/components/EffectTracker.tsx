import { useState, useEffect } from 'react'
import { Drawer, Button, Spin, Statistic, Row, Col, message, Empty, Tag, Space, Card } from 'antd'
import {
  ArrowUpOutlined, ArrowDownOutlined, MinusOutlined,
  ReloadOutlined, BarChartOutlined
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { distributionApi } from '@/api'

interface EffectTrackerProps {
  visible: boolean
  onClose: () => void
  distribution: any
  onRefresh?: () => void
}

const EffectTracker: React.FC<EffectTrackerProps> = ({ visible, onClose, distribution, onRefresh }) => {
  const [loading, setLoading] = useState(false)
  const [recollecting, setRecollecting] = useState(false)
  const [effectData, setEffectData] = useState<any>(null)

  useEffect(() => {
    if (visible && distribution?.id) {
      loadEffect()
    }
    if (!visible) {
      setEffectData(null)
    }
  }, [visible, distribution?.id])

  const loadEffect = async () => {
    if (!distribution?.id) return
    setLoading(true)
    try {
      const res: any = await distributionApi.getEffect(distribution.id)
      setEffectData(res.data)
    } catch (e: any) {
      message.error(e.response?.data?.detail || '加载效果数据失败')
    } finally {
      setLoading(false)
    }
  }

  const handleRecollect = async () => {
    if (!distribution?.id) return
    setRecollecting(true)
    try {
      const res: any = await distributionApi.recollect(distribution.id)
      message.success(`已加入采集队列（任务#${res.data.task_id}），完成后点击刷新查看最新效果`)
    } catch (e: any) {
      message.error(e.response?.data?.detail || '触发采集失败')
    } finally {
      setRecollecting(false)
    }
  }

  // 渲染变化量标签
  // 注意：排名变化是 before - after，正数表示排名提升（数字变小）
  const renderChange = (value: number, isRank = false) => {
    if (value === null || value === undefined) return <Tag>无数据</Tag>
    if (value > 0) {
      return <Tag color="green" icon={<ArrowUpOutlined />}>{isRank ? `上升${value}位` : `+${value}%`}</Tag>
    } else if (value < 0) {
      return <Tag color="red" icon={<ArrowDownOutlined />}>{isRank ? `下降${Math.abs(value)}位` : `${value}%`}</Tag>
    }
    return <Tag icon={<MinusOutlined />}>无变化</Tag>
  }

  // 趋势图配置
  const getTrendOption = () => {
    if (!effectData?.trend || effectData.trend.length === 0) return null
    const publishDate = effectData.publish_time ? effectData.publish_time.slice(0, 10) : null
    return {
      tooltip: { trigger: 'axis' },
      legend: {
        data: ['GEO提及率', 'AEO引用率', '平均排名'],
        top: 0,
        textStyle: { fontSize: 11 }
      },
      grid: { left: 45, right: 45, top: 40, bottom: 40 },
      xAxis: {
        type: 'category',
        data: effectData.trend.map((d: any) => d.date),
        axisLabel: { fontSize: 11, rotate: 30 },
      },
      yAxis: [
        {
          type: 'value',
          name: '比率(%)',
          max: 100,
          axisLabel: { fontSize: 11 },
        },
        {
          type: 'value',
          name: '排名',
          inverse: true,
          axisLabel: { fontSize: 11 },
          splitLine: { show: false }
        }
      ],
      series: [
        {
          name: 'GEO提及率',
          type: 'line',
          data: effectData.trend.map((d: any) => d.mention_rate),
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: { width: 2, color: '#3B82F6' },
          itemStyle: { color: '#3B82F6' },
          areaStyle: {
            color: {
              type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(59,130,246,0.3)' },
                { offset: 1, color: 'rgba(59,130,246,0.02)' }
              ]
            }
          },
          markLine: publishDate ? {
            symbol: 'none',
            data: [{
              xAxis: publishDate,
              label: { formatter: '发布日', fontSize: 11, color: '#10B981' },
              lineStyle: { color: '#10B981', type: 'dashed', width: 2 }
            }],
          } : undefined,
        },
        {
          name: 'AEO引用率',
          type: 'line',
          data: effectData.trend.map((d: any) => d.citation_rate),
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: { width: 2, color: '#8B5CF6' },
          itemStyle: { color: '#8B5CF6' },
        },
        {
          name: '平均排名',
          type: 'bar',
          yAxisIndex: 1,
          data: effectData.trend.map((d: any) => d.avg_rank),
          barWidth: '40%',
          itemStyle: { color: '#F59E0B', borderRadius: [4, 4, 0, 0] },
        }
      ],
    }
  }

  return (
    <Drawer
      title={
        <div>
          <BarChartOutlined style={{ marginRight: 8, color: '#3B82F6' }} />
          内容效果追踪
          <div style={{ fontSize: 12, color: '#94A3B8', fontWeight: 400, marginTop: 4 }}>
            {distribution?.article_title || '文章'}
          </div>
        </div>
      }
      placement="right"
      width={680}
      open={visible}
      onClose={onClose}
      extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadEffect} loading={loading}>刷新</Button>
          <Button type="primary" icon={<ReloadOutlined />} onClick={handleRecollect} loading={recollecting} className="btn-primary-gradient">
            重新采集验证
          </Button>
        </Space>
      }
    >
      <Spin spinning={loading}>
        {!effectData ? (
          <div style={{ padding: '40px 0' }}>
            <Empty
              description={
                <div>
                  <div style={{ marginBottom: 8 }}>暂无效果数据</div>
                  <div style={{ fontSize: 12, color: '#94A3B8' }}>点击「重新采集验证」开始追踪发布效果</div>
                </div>
              }
            />
          </div>
        ) : (
          <div>
            {/* 发布前后对比 */}
            <Card title="📊 发布前后对比" size="small" style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic
                    title="GEO提及率"
                    value={effectData.after?.mention_rate || 0}
                    suffix="%"
                    valueStyle={{ color: '#3B82F6', fontSize: 24, fontWeight: 700 }}
                  />
                  <div style={{ marginTop: 4, fontSize: 12 }}>
                    <span style={{ color: '#64748B' }}>发布前 {effectData.before?.mention_rate || 0}%</span>
                    <span style={{ marginLeft: 8 }}>{renderChange(effectData.change?.mention_rate)}</span>
                  </div>
                </Col>
                <Col span={8}>
                  <Statistic
                    title="AEO引用率"
                    value={effectData.after?.citation_rate || 0}
                    suffix="%"
                    valueStyle={{ color: '#8B5CF6', fontSize: 24, fontWeight: 700 }}
                  />
                  <div style={{ marginTop: 4, fontSize: 12 }}>
                    <span style={{ color: '#64748B' }}>发布前 {effectData.before?.citation_rate || 0}%</span>
                    <span style={{ marginLeft: 8 }}>{renderChange(effectData.change?.citation_rate)}</span>
                  </div>
                </Col>
                <Col span={8}>
                  <Statistic
                    title="平均排名"
                    value={effectData.after?.avg_rank || '-'}
                    suffix={effectData.after?.avg_rank ? '名' : ''}
                    valueStyle={{ color: '#F59E0B', fontSize: 24, fontWeight: 700 }}
                  />
                  <div style={{ marginTop: 4, fontSize: 12 }}>
                    <span style={{ color: '#64748B' }}>发布前 {effectData.before?.avg_rank || '-'}</span>
                    {effectData.change?.avg_rank !== null && effectData.change?.avg_rank !== undefined && (
                      <span style={{ marginLeft: 8 }}>{renderChange(effectData.change.avg_rank, true)}</span>
                    )}
                  </div>
                </Col>
              </Row>
            </Card>

            {/* 样本量说明 */}
            <div style={{ background: '#F0F9FF', padding: '10px 14px', borderRadius: 8, marginBottom: 16, fontSize: 12, color: '#0369A1' }}>
              💡 数据样本：发布前 {effectData.before?.total || 0} 条采集记录，发布后 {effectData.after?.total || 0} 条采集记录。
              {effectData.after?.total === 0 && ' 发布后暂无采集数据，建议点击「重新采集验证」获取最新数据。'}
              {effectData.before?.total === 0 && ' 发布前暂无采集数据，无法对比变化趋势。'}
            </div>

            {/* 趋势图 */}
            <Card title="📈 最近30天效果趋势" size="small">
              {effectData.trend && effectData.trend.length > 0 ? (
                <ReactECharts option={getTrendOption()} style={{ height: 320 }} notMerge />
              ) : (
                <Empty description="暂无趋势数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </Card>

            {/* 使用说明 */}
            <div style={{ marginTop: 16, background: '#F8FAFC', padding: 16, borderRadius: 12 }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: '#334155' }}>📋 效果追踪使用说明</div>
              <div style={{ fontSize: 12, color: '#64748B', lineHeight: 1.8 }}>
                1. 文章发布后，系统对比发布前后的 GEO 提及率、AEO 引用率、排名变化<br />
                2. 点击「重新采集验证」触发一次新采集，获取最新数据<br />
                3. 趋势图展示最近30天变化，绿色虚线为发布时间点<br />
                4. 建议发布后 3-7 天再查看效果，AI 搜索索引更新需要时间
              </div>
            </div>
          </div>
        )}
      </Spin>
    </Drawer>
  )
}

export default EffectTracker
