import { useState, useEffect, useCallback } from 'react'
import {
  Card, Row, Col, Statistic, Button, Tag, message,
  Space, Descriptions, Spin, Empty, Alert, Tabs
} from 'antd'
import {
  ArrowLeftOutlined, EyeOutlined, LikeOutlined, ShareAltOutlined,
  StarOutlined, ThunderboltOutlined, ReloadOutlined, FileTextOutlined
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import request from '@/api'
import { useParams, useNavigate } from 'react-router-dom'

// 轮询参数：每3秒一次，最多20次（约60秒超时）
const POLL_INTERVAL_MS = 3000
const POLL_MAX_TIMES = 20

const WechatArticleDetail = () => {
  const { accountId, articleId } = useParams()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [article, setArticle] = useState<any>(null)
  const [analysis, setAnalysis] = useState<any>(null)
  const [pollTick, setPollTick] = useState(0)

  const loadArticle = useCallback(async () => {
    setLoading(true)
    try {
      const res: any = await request.get(
        `/publish-accounts/${accountId}/articles/${articleId}`
      )
      // 响应拦截器已返回 body，res.data 即数据载荷
      setArticle(res.data)
    } catch (e) {
      // 错误已由拦截器处理
    } finally {
      setLoading(false)
    }
  }, [accountId, articleId])

  const loadAnalysis = useCallback(async () => {
    try {
      const res: any = await request.get(
        `/publish-accounts/${accountId}/articles/${articleId}/analysis`
      )
      setAnalysis(res.data)
      return res.data?.status as string
    } catch (e) {
      // 错误已由拦截器处理
      return undefined
    }
  }, [accountId, articleId])

  const handleAnalyze = async () => {
    setAnalyzing(true)
    try {
      await request.post(
        `/publish-accounts/${accountId}/articles/${articleId}/analyze`
      )
      message.success('分析任务已提交，约10-30秒后完成')
      setPollTick(0)
      // 立即拉一次状态（后端已置 processing），随后由轮询 effect 接管
      await loadAnalysis()
    } catch (e) {
      // 错误已由拦截器处理
    } finally {
      setAnalyzing(false)
    }
  }

  // 首次进入加载
  useEffect(() => {
    if (accountId && articleId) {
      loadArticle()
      loadAnalysis()
    }
  }, [accountId, articleId, loadArticle, loadAnalysis])

  // 轮询：analysis 每次刷新都是新对象 → effect 重跑；
  // processing 且未超次数时，3秒后再拉；超次数停止并提示超时
  useEffect(() => {
    if (analysis?.status !== 'processing' || pollTick >= POLL_MAX_TIMES) return
    const timer = setTimeout(async () => {
      setPollTick((c) => c + 1)
      await loadAnalysis()
    }, POLL_INTERVAL_MS)
    return () => clearTimeout(timer)
  }, [analysis, pollTick, loadAnalysis])

  // 最新数据（snapshot_day=0）
  const latestData = article?.snapshots?.day_0 || {}

  // 数据增长趋势图（day_30 不填充，显示0）
  const growthOption = article?.snapshots ? {
    title: { text: '文章数据增长趋势', left: 'center' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['阅读量', '点赞', '分享'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: ['发布当天', '第1天', '第3天', '第7天', '第30天'],
    },
    yAxis: { type: 'value' },
    series: [
      {
        name: '阅读量', type: 'line', smooth: true,
        data: [
          article.snapshots.day_0?.int_page_read_count || 0,
          article.snapshots.day_1?.int_page_read_count || 0,
          article.snapshots.day_3?.int_page_read_count || 0,
          article.snapshots.day_7?.int_page_read_count || 0,
          article.snapshots.day_30?.int_page_read_count || 0,
        ]
      },
      {
        name: '点赞', type: 'line', smooth: true,
        data: [
          article.snapshots.day_0?.like_count || 0,
          article.snapshots.day_1?.like_count || 0,
          article.snapshots.day_3?.like_count || 0,
          article.snapshots.day_7?.like_count || 0,
          article.snapshots.day_30?.like_count || 0,
        ]
      },
      {
        name: '分享', type: 'line', smooth: true,
        data: [
          article.snapshots.day_0?.share_count || 0,
          article.snapshots.day_1?.share_count || 0,
          article.snapshots.day_3?.share_count || 0,
          article.snapshots.day_7?.share_count || 0,
          article.snapshots.day_30?.share_count || 0,
        ]
      },
    ]
  } : {}

  const renderAnalysisContent = () => {
    if (!analysis || analysis.status === 'none') {
      return (
        <Empty description="暂无AI分析结果">
          <Button type="primary" icon={<ThunderboltOutlined />}
            loading={analyzing} onClick={handleAnalyze}>
            开始AI分析
          </Button>
        </Empty>
      )
    }

    if (analysis.status === 'processing') {
      // 超过轮询上限仍未完成 → 超时提示
      if (pollTick >= POLL_MAX_TIMES) {
        return (
          <Alert
            type="warning"
            message="分析超时"
            description="已等待约60秒仍未完成，可能是AI平台响应慢。可稍后重试或前往任务中心查看。"
            action={<Button onClick={handleAnalyze}>重试</Button>}
          />
        )
      }
      return (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" />
          <p style={{ marginTop: 16 }}>AI正在分析中，约10-30秒...</p>
        </div>
      )
    }

    if (analysis.status === 'failed') {
      return (
        <Alert
          type="error"
          message="分析失败"
          description={analysis.failed_reason || '未知错误'}
          action={<Button onClick={handleAnalyze}>重试</Button>}
        />
      )
    }

    const result = analysis.result || {}
    const titleAnalysis = result.title_analysis || {}
    const interactionAnalysis = result.interaction_analysis || {}
    const llmAnalysis = result.llm_analysis || {}

    return (
      <div>
        <Space style={{ marginBottom: 16 }}>
          <Button icon={<ReloadOutlined />} loading={analyzing} onClick={handleAnalyze}>
            重新分析
          </Button>
          <Tag color="blue">
            分析时间：{analysis.completed_at ? new Date(analysis.completed_at).toLocaleString() : '-'}
          </Tag>
        </Space>

        <Tabs defaultActiveKey="title" items={[
          {
            key: 'title',
            label: '标题分析',
            children: (
              <div>
                <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
                  <Descriptions.Item label="当前标题">{article?.title}</Descriptions.Item>
                  <Descriptions.Item label="标题长度">{titleAnalysis.title_length ?? '-'} 字</Descriptions.Item>
                  <Descriptions.Item label="标题评分">{titleAnalysis.overall_score ?? '-'} /10</Descriptions.Item>
                  <Descriptions.Item label="阅读量">{titleAnalysis.reads ?? 0}</Descriptions.Item>
                </Descriptions>

                {titleAnalysis.problems?.length > 0 && (
                  <div style={{ marginBottom: 16 }}>
                    <h4>存在问题</h4>
                    {titleAnalysis.problems.map((p: string, i: number) => (
                      <div key={i}>• {p}</div>
                    ))}
                  </div>
                )}

                {titleAnalysis.optimized_titles?.length > 0 && (
                  <div>
                    <h4>AI优化标题建议</h4>
                    {titleAnalysis.optimized_titles.map((t: string, i: number) => (
                      <Alert
                        key={i}
                        type="info"
                        showIcon
                        message={`建议 ${i + 1}：${t}`}
                        style={{ marginBottom: 8 }}
                      />
                    ))}
                  </div>
                )}

                {titleAnalysis.suggestions?.length > 0 && (
                  <div style={{ marginTop: 16 }}>
                    <h4>优化建议</h4>
                    {titleAnalysis.suggestions.map((s: string, i: number) => (
                      <div key={i}>• {s}</div>
                    ))}
                  </div>
                )}
              </div>
            )
          },
          {
            key: 'content',
            label: '内容分析',
            children: (
              <div>
                {!article?.has_content ? (
                  <Alert
                    type="warning"
                    message="该文章非本系统发布，无正文内容"
                    description="内容分析需要文章正文。如需内容分析，请将文章通过本系统发布，或手动粘贴正文（后续版本支持）。"
                  />
                ) : (
                  <div>
                    {llmAnalysis.content_analysis ? (
                      <>
                        <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
                          <Descriptions.Item label="内容结构评分">
                            {llmAnalysis.content_analysis.structure_score} /10
                          </Descriptions.Item>
                        </Descriptions>

                        {llmAnalysis.content_analysis.strengths?.length > 0 && (
                          <div style={{ marginBottom: 16 }}>
                            <h4>内容优点</h4>
                            {llmAnalysis.content_analysis.strengths.map((s: string, i: number) => (
                              <div key={i} style={{ color: '#52c41a' }}>✓ {s}</div>
                            ))}
                          </div>
                        )}

                        {llmAnalysis.content_analysis.weaknesses?.length > 0 && (
                          <div style={{ marginBottom: 16 }}>
                            <h4>内容不足</h4>
                            {llmAnalysis.content_analysis.weaknesses.map((w: string, i: number) => (
                              <div key={i} style={{ color: '#faad14' }}>⚠ {w}</div>
                            ))}
                          </div>
                        )}

                        {llmAnalysis.content_analysis.optimization_suggestions?.length > 0 && (
                          <div>
                            <h4>内容优化建议</h4>
                            {llmAnalysis.content_analysis.optimization_suggestions.map(
                              (s: string, i: number) => (
                                <Alert key={i} type="info" showIcon message={s}
                                  style={{ marginBottom: 8 }} />
                              )
                            )}
                          </div>
                        )}
                      </>
                    ) : (
                      <Empty description="暂无内容分析数据" />
                    )}
                  </div>
                )}
              </div>
            )
          },
          {
            key: 'interaction',
            label: '互动分析',
            children: (
              <div>
                <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
                  <Descriptions.Item label="阅读量">{interactionAnalysis.reads ?? 0}</Descriptions.Item>
                  <Descriptions.Item label="点赞">{interactionAnalysis.likes ?? 0}</Descriptions.Item>
                  <Descriptions.Item label="分享">{interactionAnalysis.shares ?? 0}</Descriptions.Item>
                  <Descriptions.Item label="收藏">{interactionAnalysis.favorites ?? 0}</Descriptions.Item>
                  <Descriptions.Item label="点赞率">
                    {((interactionAnalysis.like_rate ?? 0) * 100).toFixed(2)}%
                  </Descriptions.Item>
                  <Descriptions.Item label="分享率">
                    {((interactionAnalysis.share_rate ?? 0) * 100).toFixed(2)}%
                  </Descriptions.Item>
                  <Descriptions.Item label="收藏率">
                    {((interactionAnalysis.favorite_rate ?? 0) * 100).toFixed(2)}%
                  </Descriptions.Item>
                  <Descriptions.Item label="行业均值点赞率">2%</Descriptions.Item>
                </Descriptions>

                {interactionAnalysis.suggestions?.length > 0 && (
                  <div>
                    <h4>互动提升建议</h4>
                    {interactionAnalysis.suggestions.map((s: string, i: number) => (
                      <Alert key={i} type="info" showIcon message={s}
                        style={{ marginBottom: 8 }} />
                    ))}
                  </div>
                )}
              </div>
            )
          },
          {
            key: 'topic',
            label: '选题建议',
            children: (
              <div>
                {llmAnalysis.topic_suggestions ? (
                  <>
                    <Alert
                      type="info"
                      showIcon
                      message="内容缺口分析"
                      description={llmAnalysis.topic_suggestions.content_gap}
                      style={{ marginBottom: 16 }}
                    />

                    <h4>AI推荐选题方向（5个）</h4>
                    {llmAnalysis.topic_suggestions.suggested_topics?.map((topic: any, i: number) => (
                      <Card key={i} size="small" style={{ marginBottom: 12 }}>
                        <Descriptions column={1} size="small">
                          <Descriptions.Item label={`选题 ${i + 1}`}>{topic.topic}</Descriptions.Item>
                          <Descriptions.Item label="推荐理由">{topic.reason}</Descriptions.Item>
                          <Descriptions.Item label="预期效果">{topic.expected_effect}</Descriptions.Item>
                        </Descriptions>
                      </Card>
                    ))}
                  </>
                ) : (
                  <Empty description="暂无选题建议" />
                )}
              </div>
            )
          },
        ]} />
      </div>
    )
  }

  if (loading && !article) {
    return <div style={{ padding: 40, textAlign: 'center' }}><Spin size="large" /></div>
  }

  return (
    <div style={{ padding: 24 }}>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>返回</Button>
        {article?.article_url && (
          <Button type="link" href={article.article_url} target="_blank">
            <FileTextOutlined /> 查看原文
          </Button>
        )}
      </Space>

      {/* 文章标题 */}
      <Card style={{ marginBottom: 16 }}>
        <h2 style={{ marginBottom: 8 }}>{article?.title}</h2>
        <Space>
          <Tag color="blue">发布日期：{article?.publish_date || '-'}</Tag>
          {article?.has_content && <Tag color="green">有正文</Tag>}
          {!article?.has_content && <Tag color="orange">无正文（非本系统发布）</Tag>}
        </Space>
      </Card>

      {/* 数据卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="阅读量" value={latestData.int_page_read_count || 0} prefix={<EyeOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="点赞" value={latestData.like_count || 0} prefix={<LikeOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="分享" value={latestData.share_count || 0} prefix={<ShareAltOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic title="收藏" value={latestData.add_to_fav_count || 0} prefix={<StarOutlined />} />
          </Card>
        </Col>
      </Row>

      {/* 数据增长趋势图 */}
      <Card title="数据增长趋势" style={{ marginBottom: 24 }}>
        <ReactECharts option={growthOption} style={{ height: 350 }} />
      </Card>

      {/* AI分析结果 */}
      <Card title="AI优化建议" extra={<ThunderboltOutlined style={{ color: '#faad14' }} />}>
        {renderAnalysisContent()}
      </Card>
    </div>
  )
}

export default WechatArticleDetail
