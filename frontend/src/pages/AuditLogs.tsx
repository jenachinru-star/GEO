import { useState, useEffect } from 'react'
import {
  Card, Table, Button, Select, DatePicker, Space, Tag, Row, Col,
  Modal, Descriptions, Badge, Input
} from 'antd'
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import request from '@/api'
import dayjs from 'dayjs'

const { RangePicker } = DatePicker

const ACTION_MAP: Record<string, { label: string; color: string }> = {
  login: { label: '登录', color: 'green' },
  logout: { label: '登出', color: 'default' },
  create: { label: '创建', color: 'blue' },
  update: { label: '更新', color: 'orange' },
  delete: { label: '删除', color: 'red' },
  publish: { label: '发布', color: 'purple' },
  export: { label: '导出', color: 'cyan' },
  config: { label: '配置修改', color: 'gold' },
}

const RESOURCE_MAP: Record<string, string> = {
  auth: '认证',
  distribution: '分发',
  export: '导出',
  platforms: '平台配置',
  'publish-accounts': '发布账号',
  benchmark: '对标账号',
  semantic: '语义库',
  content: '内容',
  monitor: '监测',
  competitor: '竞品',
  asset: '数字资产',
}

const AuditLogs = () => {
  const [list, setList] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [isAdmin, setIsAdmin] = useState(false)
  const [actionTypes, setActionTypes] = useState<any[]>([])
  const [filterAction, setFilterAction] = useState<string | undefined>(undefined)
  const [filterResource, setFilterResource] = useState<string | undefined>(undefined)
  const [filterDateRange, setFilterDateRange] = useState<any>(null)
  const [detailVisible, setDetailVisible] = useState(false)
  const [detailRecord, setDetailRecord] = useState<any>(null)

  const loadActionTypes = async () => {
    try {
      const res: any = await request.get('/audit/actions')
      setActionTypes(res.data?.items || [])
    } catch (e) {
      // 错误已由拦截器处理
    }
  }

  const loadList = async (p = 1, ps = pageSize) => {
    setLoading(true)
    try {
      const params: any = { page: p, page_size: ps }
      if (filterAction) params.action = filterAction
      if (filterResource) params.resource_type = filterResource
      if (filterDateRange && filterDateRange.length === 2) {
        params.start_date = filterDateRange[0].format('YYYY-MM-DD')
        params.end_date = filterDateRange[1].format('YYYY-MM-DD')
      }
      const res: any = await request.get('/audit', { params })
      setList(res.data?.items || [])
      setTotal(res.data?.total || 0)
      setIsAdmin(res.data?.is_admin || false)
      setPage(p)
    } catch (e) {
      // 错误已由拦截器处理
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadActionTypes()
    loadList(1)
  }, [])

  const handleSearch = () => {
    loadList(1)
  }

  const handleReset = () => {
    setFilterAction(undefined)
    setFilterResource(undefined)
    setFilterDateRange(null)
    loadList(1)
  }

  const handleViewDetail = (record: any) => {
    setDetailRecord(record)
    setDetailVisible(true)
  }

  const columns = [
    {
      title: '时间', dataIndex: 'created_at', key: 'created_at', width: 170,
      render: (v: string) => v ? dayjs(v).format('YYYY-MM-DD HH:mm:ss') : '-'
    },
    {
      title: '用户', dataIndex: 'username', key: 'username', width: 120,
      render: (v: string, record: any) => v || `用户#${record.user_id || '未知'}`
    },
    {
      title: '操作类型', dataIndex: 'action', key: 'action', width: 100,
      render: (v: string) => {
        const info = ACTION_MAP[v] || { label: v, color: 'default' }
        return <Tag color={info.color}>{info.label}</Tag>
      }
    },
    {
      title: '资源类型', dataIndex: 'resource_type', key: 'resource_type', width: 110,
      render: (v: string) => RESOURCE_MAP[v] || v || '-'
    },
    { title: '资源ID', dataIndex: 'resource_id', key: 'resource_id', width: 80, render: (v: string) => v || '-' },
    { title: 'IP地址', dataIndex: 'ip_address', key: 'ip_address', width: 130 },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (v: string) => v === 'success'
        ? <Badge status="success" text="成功" />
        : <Badge status="error" text="失败" />
    },
    {
      title: '操作', key: 'action_col', width: 80,
      render: (_: any, record: any) => (
        <Button type="link" size="small" onClick={() => handleViewDetail(record)}>详情</Button>
      )
    },
  ]

  const resourceOptions = Object.entries(RESOURCE_MAP).map(([value, label]) => ({ label, value }))

  return (
    <div style={{ padding: 24 }}>
      <Card
        title="审计日志"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => loadList(page)}>刷新</Button>
          </Space>
        }
      >
        {/* 筛选区 */}
        <Row gutter={[16, 12]} style={{ marginBottom: 16 }}>
          <Col span={5}>
            <Select
              style={{ width: '100%' }}
              placeholder="操作类型"
              allowClear
              value={filterAction}
              onChange={setFilterAction}
              options={actionTypes.map((a: any) => ({ label: a.label, value: a.value }))}
            />
          </Col>
          <Col span={5}>
            <Select
              style={{ width: '100%' }}
              placeholder="资源类型"
              allowClear
              value={filterResource}
              onChange={setFilterResource}
              options={resourceOptions}
            />
          </Col>
          <Col span={7}>
            <RangePicker
              style={{ width: '100%' }}
              value={filterDateRange}
              onChange={setFilterDateRange}
            />
          </Col>
          <Col span={7}>
            <Space>
              <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>查询</Button>
              <Button onClick={handleReset}>重置</Button>
              {isAdmin && <Tag color="blue">管理员视图（可查看所有用户）</Tag>}
            </Space>
          </Col>
        </Row>

        {/* 日志列表 */}
        <Table
          columns={columns}
          dataSource={list}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条记录`,
            onChange: (p, ps) => { setPageSize(ps); loadList(p, ps) },
          }}
        />
      </Card>

      {/* 详情弹窗 */}
      <Modal
        title="审计日志详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={<Button onClick={() => setDetailVisible(false)}>关闭</Button>}
        width={600}
      >
        {detailRecord && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="时间">
              {detailRecord.created_at ? dayjs(detailRecord.created_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="用户">
              {detailRecord.username || `用户#${detailRecord.user_id || '未知'}`}
            </Descriptions.Item>
            <Descriptions.Item label="用户ID">{detailRecord.user_id || '-'}</Descriptions.Item>
            <Descriptions.Item label="操作类型">
              <Tag color={ACTION_MAP[detailRecord.action]?.color || 'default'}>
                {ACTION_MAP[detailRecord.action]?.label || detailRecord.action}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="资源类型">
              {RESOURCE_MAP[detailRecord.resource_type] || detailRecord.resource_type || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="资源ID">{detailRecord.resource_id || '-'}</Descriptions.Item>
            <Descriptions.Item label="IP地址">{detailRecord.ip_address || '-'}</Descriptions.Item>
            <Descriptions.Item label="User-Agent">
              <Input.TextArea value={detailRecord.user_agent} autoSize readOnly style={{ fontSize: 12 }} />
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              {detailRecord.status === 'success'
                ? <Badge status="success" text="成功" />
                : <Badge status="error" text="失败" />}
            </Descriptions.Item>
            {detailRecord.error_message && (
              <Descriptions.Item label="错误信息">{detailRecord.error_message}</Descriptions.Item>
            )}
            {detailRecord.details && (
              <Descriptions.Item label="操作详情">
                <Input.TextArea value={detailRecord.details} autoSize readOnly style={{ fontSize: 12 }} />
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}

export default AuditLogs
