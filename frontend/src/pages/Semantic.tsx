import { useState, useEffect } from 'react'
import { List, Switch, Button, Empty, message, Spin, Statistic, Row, Col, Space, Tooltip } from 'antd'
import { useNavigate } from 'react-router-dom'
import { BranchesOutlined } from '@ant-design/icons'
import { semanticApi, doctorApi } from '@/api'
import { useAppStore } from '@/store/useStore'
import SemanticExtendDrawer from '@/components/SemanticExtendDrawer'

const Semantic = () => {
  const [loading, setLoading] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [extendDrawerOpen, setExtendDrawerOpen] = useState(false)
  const [currentSemanticId, setCurrentSemanticId] = useState<number | null>(null)
  const [currentSemanticQuestion, setCurrentSemanticQuestion] = useState('')
  const navigate = useNavigate()
  const { semantics, setSemantics } = useAppStore()

  useEffect(() => {
    loadSemantics()
  }, [])

  const loadSemantics = async () => {
    setLoading(true)
    try {
      const res: any = await semanticApi.getList()
      setSemantics(res.data || [])
    } catch (e) {
      // 拦截器已提示
    } finally {
      setLoading(false)
    }
  }

  const handleToggle = async (id: number) => {
    try {
      await semanticApi.toggle(id)
      setSemantics(semantics.map((s: any) => s.id === id ? { ...s, is_active: !s.is_active } : s))
    } catch (e) {
      // 拦截器已提示
    }
  }

  const handleRegenerate = async () => {
    setRegenerating(true)
    try {
      const res: any = await doctorApi.regenerateSemantics()
      message.success(`新增 ${res.data?.new_count || 0} 个语义，共 ${res.data?.total || 0} 个`)
      loadSemantics()
    } catch (e) {
      // 拦截器已提示
    } finally {
      setRegenerating(false)
    }
  }

  const handleExtend = (item: any) => {
    setCurrentSemanticId(item.id)
    setCurrentSemanticQuestion(item.question)
    setExtendDrawerOpen(true)
  }

  const handleExtendSaved = () => {
    loadSemantics()
  }

  const activeCount = semantics.filter((s: any) => s.is_active).length

  return (
    <div>
      <div className="page-title-bar">
        <div>
          <h2>语义库</h2>
          <div className="page-desc">系统基于您的执业信息自动生成患者会真实搜索的问题</div>
        </div>
        <Space>
          <Tooltip title="对所有启用的语义批量生成同义变体和深度延伸">
            <Button icon={<BranchesOutlined />} onClick={() => message.info('批量延伸功能开发中，请使用单个语义的延伸按钮')}>
              批量延伸
            </Button>
          </Tooltip>
          <Button onClick={handleRegenerate} loading={regenerating}>重新生成</Button>
        </Space>
      </div>

      <Row gutter={16} style={{ marginBottom: 20 }}>
        <Col span={6}>
          <div className="geo-card" style={{ padding: 20 }}>
            <Statistic title="语义总数" value={semantics.length} valueStyle={{ fontWeight: 700 }} />
          </div>
        </Col>
        <Col span={6}>
          <div className="geo-card" style={{ padding: 20 }}>
            <Statistic title="已启用" value={activeCount} valueStyle={{ color: '#10B981', fontWeight: 700 }} />
          </div>
        </Col>
        <Col span={6}>
          <div className="geo-card" style={{ padding: 20 }}>
            <Statistic title="已禁用" value={semantics.length - activeCount} valueStyle={{ color: '#94A3B8', fontWeight: 700 }} />
          </div>
        </Col>
        <Col span={6}>
          <div className="geo-card" style={{ padding: 20 }}>
            <Statistic title="累计文章" value={semantics.reduce((sum: number, s: any) => sum + (s.article_count || 0), 0)} valueStyle={{ fontWeight: 700 }} />
          </div>
        </Col>
      </Row>

      <div className="geo-card">
        <Spin spinning={loading}>
          {semantics.length === 0 ? (
            <Empty
              description="暂无语义问题"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            >
              <Button type="primary" onClick={() => navigate('/profile')} className="btn-primary-gradient">
                去完善资料
              </Button>
            </Empty>
          ) : (
            <List
              dataSource={semantics}
              renderItem={(item: any) => (
                <List.Item
                  actions={[
                    <Button
                      type="link"
                      size="small"
                      icon={<BranchesOutlined />}
                      onClick={() => handleExtend(item)}
                      style={{ padding: '0 4px' }}
                    >
                      延伸
                    </Button>,
                    <Switch
                      checked={item.is_active}
                      onChange={() => handleToggle(item.id)}
                      checkedChildren="监测中"
                      unCheckedChildren="已停用"
                    />
                  ]}
                  style={{ borderRadius: 12, padding: '12px 16px', marginBottom: 8, transition: 'all 0.2s ease' }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = '#F8FAFC' }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
                >
                  <List.Item.Meta
                    title={
                      <span style={{ fontWeight: 500 }}>
                        {item.question}
                        {item.is_paid && <span className="geo-tag geo-tag-orange" style={{ marginLeft: 8 }}>付费</span>}
                      </span>
                    }
                    description={
                      <span style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                        <span className="geo-tag geo-tag-blue">文章 {item.article_count || 0}</span>
                        <span className="geo-tag geo-tag-green">GEO {(item.geo_rate * 100).toFixed(0)}%</span>
                        <span className="geo-tag geo-tag-purple">AEO {(item.aeo_rate * 100).toFixed(0)}%</span>
                        <span style={{ color: '#94A3B8', fontSize: 12 }}>ID: {item.id}</span>
                      </span>
                    }
                  />
                </List.Item>
              )}
            />
          )}
        </Spin>
      </div>

      <SemanticExtendDrawer
        open={extendDrawerOpen}
        onClose={() => setExtendDrawerOpen(false)}
        semanticId={currentSemanticId}
        semanticQuestion={currentSemanticQuestion}
        onSaved={handleExtendSaved}
      />
    </div>
  )
}

export default Semantic
