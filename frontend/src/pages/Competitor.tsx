import { useEffect, useState } from 'react'
import {
  Row, Col, Card, Table, Tag, Button, Space, Input,
  Modal, Form, message, Popconfirm, Empty
} from 'antd'
import {
  PlusOutlined, ReloadOutlined, DeleteOutlined,
  TeamOutlined, BarChartOutlined
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { competitorApi } from '@/api'

const Competitor = () => {
  const [list, setList] = useState<any[]>([])
  const [records, setRecords] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [form] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const [listRes, recordsRes]: any[] = await Promise.all([
        competitorApi.getList(),
        competitorApi.getRecords()
      ])
      setList(listRes.data)
      setRecords(recordsRes.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleAdd = async () => {
    try {
      const values = await form.validateFields()
      await competitorApi.create(values)
      message.success('添加成功')
      setModalVisible(false)
      form.resetFields()
      loadData()
    } catch (e) {}
  }

  const handleDelete = async (id: number) => {
    await competitorApi.delete(id)
    message.success('删除成功')
    loadData()
  }

  // 竞品统计
  const competitorStats = list.map((comp: any) => {
    const compRecords = records.filter((r: any) => r.competitor_id === comp.id)
    const mentioned = compRecords.filter((r: any) => r.mentioned).length
    const ranks = compRecords.filter((r: any) => r.mentioned).map((r: any) => r.rank)
    return {
      ...comp,
      mention_count: mentioned,
      total_count: compRecords.length,
      mention_rate: compRecords.length ? Math.round(mentioned / compRecords.length * 100) : 0,
      avg_rank: ranks.length ? (ranks.reduce((a: number, b: number) => a + b, 0) / ranks.length).toFixed(1) : '-'
    }
  })

  // 对比柱状图
  const chartOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['提及率(%)'], bottom: 0 },
    grid: { left: 40, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'category',
      data: competitorStats.map((c: any) => c.name),
      axisLabel: { rotate: 30 }
    },
    yAxis: { type: 'value', name: '%', max: 100 },
    series: [{
      name: '提及率',
      type: 'bar',
      data: competitorStats.map((c: any) => c.mention_rate),
      itemStyle: {
        color: (params: any) => {
          const colors = ['#EF4444', '#F59E0B', '#8B5CF6', '#0EA5E9', '#10B981']
          return colors[params.dataIndex % colors.length]
        },
        borderRadius: [4, 4, 0, 0]
      },
      barWidth: '40%'
    }]
  }

  const columns = [
    { title: '竞品名称', dataIndex: 'name', key: 'name', render: (t: string) => <span style={{ fontWeight: 500 }}>{t}</span> },
    { title: '别名', dataIndex: 'aliases', key: 'aliases', render: (t: string) => t || '-' },
    { title: '行业', dataIndex: 'industry', key: 'industry' },
    {
      title: '提及次数', dataIndex: 'mention_count', key: 'mention_count', width: 90,
      render: (n: number) => <span style={{ color: n > 0 ? '#0EA5E9' : '#94A3B8' }}>{n}次</span>
    },
    {
      title: '提及率', dataIndex: 'mention_rate', key: 'mention_rate', width: 90,
      render: (n: number) => <span style={{ fontWeight: 600 }}>{n}%</span>
    },
    { title: '平均排名', dataIndex: 'avg_rank', key: 'avg_rank', width: 90 },
    {
      title: '操作', key: 'action', width: 80,
      render: (_: any, record: any) => (
        <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
          <Button type="link" size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      )
    }
  ]

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>竞品分析</h2>
          <div className="page-desc">监控竞品在AI平台的曝光情况，对比分析竞争格局</div>
        </div>
        <Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalVisible(true)}>添加竞品</Button>
          <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
        </Space>
      </div>

      {/* 对比图表 */}
      <div className="geo-card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginBottom: 16, fontSize: 15 }}>
          <BarChartOutlined style={{ marginRight: 8, color: '#0EA5E9' }} />
          竞品提及率对比
        </h3>
        {competitorStats.length > 0 ? (
          <ReactECharts option={chartOption} style={{ height: 300 }} />
        ) : (
          <Empty description="暂无竞品数据，请先添加竞品" style={{ padding: 40 }} />
        )}
      </div>

      {/* 竞品列表 */}
      <div className="geo-card">
        <Table
          dataSource={competitorStats}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={false}
          locale={{ emptyText: <Empty description="暂无竞品" /> }}
        />
      </div>

      {/* 添加竞品弹窗 */}
      <Modal
        title="添加竞品"
        open={modalVisible}
        onOk={handleAdd}
        onCancel={() => setModalVisible(false)}
        okText="添加"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="竞品名称" rules={[{ required: true, message: '请输入竞品名称' }]}>
            <Input placeholder="例如：晶泰科技" />
          </Form.Item>
          <Form.Item name="aliases" label="别名">
            <Input placeholder="多个别名用逗号分隔" />
          </Form.Item>
          <Form.Item name="industry" label="所属行业">
            <Input placeholder="例如：AI药物研发" />
          </Form.Item>
          <Form.Item name="website" label="官网">
            <Input placeholder="https://" />
          </Form.Item>
          <Form.Item name="description" label="简介">
            <Input.TextArea rows={3} placeholder="竞品简要描述" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default Competitor
