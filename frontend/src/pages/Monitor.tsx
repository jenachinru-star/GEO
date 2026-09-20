import { useEffect, useRef, useState } from 'react'
import {
  Row, Col, Card, Table, Tag, Button, Space, Input, Select,
  Modal, Form, Drawer, Descriptions, message, Popconfirm, Tooltip
} from 'antd'
import {
  PlusOutlined, ReloadOutlined, PlayCircleOutlined,
  DeleteOutlined, EyeOutlined, SearchOutlined, DownloadOutlined,
  CheckCircleOutlined, ClockCircleOutlined
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { monitorApi, exportApi, systemApi, taskApi } from '@/api'
import { PLATFORM_NAMES, CATEGORY_NAMES } from '@/store/useStore'

const Monitor = () => {
  const [questions, setQuestions] = useState<any[]>([])
  const [matrix, setMatrix] = useState<any[]>([])
  const [platforms, setPlatforms] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [collectLoading, setCollectLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [drawerVisible, setDrawerVisible] = useState(false)
  const [selectedRecord, setSelectedRecord] = useState<any>(null)
  const [trendData, setTrendData] = useState<any[]>([])
  const [form] = Form.useForm()
  const [filters, setFilters] = useState({ category: '', keyword: '' })
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current)
    }
  }, [])

  const loadPlatforms = async () => {
    try {
      const res: any = await systemApi.getPlatforms()
      setPlatforms(res.data)
    } catch (e) {
      setPlatforms([])
    }
  }

  const loadQuestions = async () => {
    setLoading(true)
    try {
      const res: any = await monitorApi.getQuestions({
        category: filters.category || undefined,
        keyword: filters.keyword || undefined,
        page_size: 100
      })
      setQuestions(res.data.items)
    } finally {
      setLoading(false)
    }
  }

  const loadMatrix = async () => {
    try {
      const res: any = await monitorApi.getMatrix()
      setMatrix(res.data)
    } catch (e) {
      setMatrix([])
    }
  }

  useEffect(() => {
    loadQuestions()
    loadMatrix()
    loadPlatforms()
  }, [filters])

  const handleCollect = async (questionId?: number) => {
    setCollectLoading(true)
    const loadingKey = 'monitor_collect'
    try {
      const res: any = await monitorApi.collect({ question_id: questionId, detect_round: 1 })
      const taskId = res.data?.task_id
      if (!taskId) {
        message.warning('任务已提交，但未获取到任务ID')
        setCollectLoading(false)
        return
      }
      // /monitor/collect 是异步任务：POST 只返回 task_id，采集在 worker 后台执行
      message.loading({ content: `采集任务 #${taskId} 已提交，正在后台执行...`, key: loadingKey, duration: 0 })

      let pollCount = 0
      const maxPolls = 600
      pollTimerRef.current = setInterval(async () => {
        pollCount++
        try {
          const taskRes: any = await taskApi.get(taskId)
          const task = taskRes.data
          if (task.status === 'succeeded') {
            if (pollTimerRef.current) clearInterval(pollTimerRef.current)
            const success = task.result?.success ?? 0
            const total = task.result?.total ?? 0
            message.success({ content: `采集完成：${success}/${total} 个问题`, key: loadingKey })
            loadMatrix()
            loadQuestions()
            setCollectLoading(false)
          } else if (task.status === 'failed') {
            if (pollTimerRef.current) clearInterval(pollTimerRef.current)
            message.error({ content: task.error_message || '采集失败', key: loadingKey })
            setCollectLoading(false)
          } else if (pollCount >= maxPolls) {
            if (pollTimerRef.current) clearInterval(pollTimerRef.current)
            message.warning({ content: '采集任务超时，请在任务中心查看', key: loadingKey })
            setCollectLoading(false)
          }
        } catch (e) {
          // 单次查询失败不中断
        }
      }, 3000)
    } catch (e: any) {
      message.error({ content: e?.response?.data?.detail || '采集失败', key: loadingKey })
      setCollectLoading(false)
    }
  }

  const handleAddQuestion = async () => {
    try {
      const values = await form.validateFields()
      await monitorApi.createQuestion(values)
      message.success('添加成功')
      setModalVisible(false)
      form.resetFields()
      loadQuestions()
    } catch (e) {
      // 校验失败
    }
  }

  const handleDelete = async (id: number) => {
    await monitorApi.deleteQuestion(id)
    message.success('删除成功')
    loadQuestions()
  }

  const handleViewDetail = async (questionId: number, platformCode: string, record: any) => {
    setSelectedRecord(record)
    setDrawerVisible(true)
    // 加载趋势
    try {
      const res: any = await monitorApi.getTrend(questionId, { platform_code: platformCode, days: 7 })
      setTrendData(res.data)
    } catch {
      setTrendData([])
    }
  }

  // 获取矩阵中某问题某平台的记录
  const getMatrixCell = (questionId: number, platformCode: string) => {
    const item = matrix.find(m => m.question_id === questionId)
    return item?.platforms?.[platformCode]
  }

  // 动态获取平台列表
  const platformCodes = Array.from(new Set(matrix.flatMap(m => Object.keys(m.platforms || {}))))

  const trendOption = trendData.length ? {
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 20, bottom: 30 },
    xAxis: {
      type: 'category',
      data: [...new Set(trendData.map((d: any) => d.date.slice(5)))]
    },
    yAxis: { type: 'value', name: '排名', inverse: true },
    series: platformCodes.map(code => ({
      name: PLATFORM_NAMES[code] || code,
      type: 'line',
      data: trendData.filter((d: any) => d.platform === code).map((d: any) => d.rank || null),
      connectNulls: true
    }))
  } : {}

  const columns = [
    {
      title: '监测问题', dataIndex: 'question', key: 'question',
      render: (text: string) => <span style={{ fontWeight: 500 }}>{text}</span>
    },
    {
      title: '分类', dataIndex: 'category', key: 'category', width: 90,
      render: (c: string) => <Tag className={`tag-${c}`}>{CATEGORY_NAMES[c] || c}</Tag>
    },
    ...platformCodes.map(code => ({
      title: PLATFORM_NAMES[code] || code,
      key: code,
      width: 110,
      render: (_: any, record: any) => {
        const cell = getMatrixCell(record.id, code)
        if (!cell) return <span style={{ color: '#CBD5E1' }}>—</span>
        const rankClass = cell.rank > 0 && cell.rank <= 3 ? 'rank-top3' :
          cell.rank > 0 ? 'rank-mid' : 'rank-none'
        return (
          <div
            className={`matrix-cell ${rankClass}`}
            onClick={() => handleViewDetail(record.id, code, cell)}
          >
            {cell.mentioned ? `第${cell.rank}名` : '未提及'}
          </div>
        )
      }
    })),
    {
      title: '操作', key: 'action', width: 150, fixed: 'right' as const,
      render: (_: any, record: any) => (
        <Space size="small">
          <Button type="link" size="small" icon={<PlayCircleOutlined />}
            onClick={() => handleCollect(record.id)} loading={collectLoading}>
            采集
          </Button>
          <Popconfirm title="确定删除此问题？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      )
    }
  ]

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>监测中心</h2>
          <div className="page-desc">管理监测问题，查看各平台排名矩阵</div>
        </div>
        <Space>
          <Button icon={<DownloadOutlined />} onClick={() => exportApi.exportMonitor()}>
            导出记录
          </Button>
          <Button icon={<PlusOutlined />} type="primary" onClick={() => setModalVisible(true)}>
            添加问题
          </Button>
          <Button icon={<PlayCircleOutlined />} onClick={() => handleCollect()} loading={collectLoading}>
            全量采集
          </Button>
          <Button icon={<ReloadOutlined />} onClick={() => { loadQuestions(); loadMatrix() }}>
            刷新
          </Button>
        </Space>
      </div>

      {/* 平台状态区 */}
      <div className="geo-card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>AI平台状态</h3>
          <span style={{ fontSize: 12, color: '#94A3B8' }}>采集时自动调用所有已启用平台</span>
        </div>
        <Space wrap>
          {platforms.map((p: any) => (
            <div key={p.code} style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 16px',
              background: p.enabled ? 'rgba(16,185,129,0.06)' : 'rgba(148,163,184,0.06)',
              border: `1px solid ${p.enabled ? 'rgba(16,185,129,0.2)' : 'rgba(148,163,184,0.2)'}`,
              borderRadius: 8
            }}>
              {p.enabled ? (
                <CheckCircleOutlined style={{ color: '#10B981' }} />
              ) : (
                <ClockCircleOutlined style={{ color: '#94A3B8' }} />
              )}
              <span style={{ fontWeight: 500, fontSize: 13 }}>{p.name}</span>
              <span style={{ fontSize: 11, color: '#94A3B8' }}>{p.model || '未配置'}</span>
              <Tag color={p.enabled ? 'green' : 'default'} style={{ marginLeft: 4 }}>
                {p.enabled ? '已启用' : '未配置'}
              </Tag>
            </div>
          ))}
        </Space>
      </div>

      {/* 筛选区 */}
      <div className="geo-card" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Input
            placeholder="搜索问题"
            prefix={<SearchOutlined />}
            style={{ width: 240 }}
            value={filters.keyword}
            onChange={e => setFilters({ ...filters, keyword: e.target.value })}
            allowClear
          />
          <Select
            placeholder="问题分类"
            style={{ width: 140 }}
            value={filters.category || undefined}
            onChange={v => setFilters({ ...filters, category: v })}
            allowClear
            options={[
              { value: 'brand', label: '品牌类' },
              { value: 'tech', label: '技术类' },
              { value: 'industry', label: '行业类' },
              { value: 'competitor', label: '竞品类' },
              { value: 'general', label: '综合类' }
            ]}
          />
        </Space>
      </div>

      {/* 问题矩阵表 */}
      <div className="geo-card">
        <Table
          dataSource={questions}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20, showSizeChanger: true }}
          scroll={{ x: 'max-content' }}
          locale={{ emptyText: '暂无监测问题，点击右上角添加' }}
        />
      </div>

      {/* 添加问题弹窗 */}
      <Modal
        title="添加监测问题"
        open={modalVisible}
        onOk={handleAddQuestion}
        onCancel={() => setModalVisible(false)}
        okText="添加"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="question" label="问题内容" rules={[{ required: true, message: '请输入问题' }]}>
            <Input.TextArea rows={3} placeholder="例如：深圳有哪些AI药物研发公司" />
          </Form.Item>
          <Form.Item name="category" label="问题分类" initialValue="general">
            <Select options={[
              { value: 'brand', label: '品牌类' },
              { value: 'tech', label: '技术类' },
              { value: 'industry', label: '行业类' },
              { value: 'competitor', label: '竞品类' },
              { value: 'general', label: '综合类' }
            ]} />
          </Form.Item>
          <Form.Item name="tags" label="标签">
            <Input placeholder="多个标签用逗号分隔" />
          </Form.Item>
          <Form.Item name="priority" label="优先级" initialValue={5}>
            <Select options={[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(n => ({ value: n, label: `${n}分` }))} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 详情抽屉 */}
      <Drawer
        title="监测详情"
        placement="right"
        width={560}
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
      >
        {selectedRecord && (
          <div>
            <Descriptions column={1} size="small" style={{ marginBottom: 20 }}>
              <Descriptions.Item label="排名">
                {selectedRecord.mentioned ? `第${selectedRecord.rank}名` : '未提及'}
              </Descriptions.Item>
              <Descriptions.Item label="情感分">{selectedRecord.sentiment}</Descriptions.Item>
              <Descriptions.Item label="记录ID">{selectedRecord.record_id}</Descriptions.Item>
            </Descriptions>

            <h4 style={{ marginBottom: 12 }}>近7天排名趋势</h4>
            {trendData.length ? (
              <ReactECharts option={trendOption} style={{ height: 220, marginBottom: 20 }} />
            ) : (
              <div style={{ height: 100, color: '#94A3B8', textAlign: 'center', lineHeight: '100px' }}>暂无趋势数据</div>
            )}

            <h4 style={{ marginBottom: 12 }}>AI原始回答</h4>
            <div style={{
              background: '#F8FAFC',
              padding: 16,
              borderRadius: 8,
              lineHeight: 1.8,
              fontSize: 13,
              maxHeight: 400,
              overflow: 'auto',
              whiteSpace: 'pre-wrap'
            }}>
              {selectedRecord.raw_answer || '暂无原始回答'}
            </div>
          </div>
        )}
      </Drawer>
    </div>
  )
}

export default Monitor
