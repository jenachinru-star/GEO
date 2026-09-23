// 任务中心页面 — 展示所有异步任务的状态和进度
import { useState, useEffect, useCallback } from 'react'
import { Table, Tag, Progress, Button, Space, Card, Typography, Empty, Badge, message, Tooltip, Popconfirm } from 'antd'
import { ReloadOutlined, CheckCircleOutlined, CloseCircleOutlined, LoadingOutlined, ClockCircleOutlined, WarningOutlined } from '@ant-design/icons'
import { taskApi } from '@/api'
import { formatUtcTime as formatTime } from '@/utils/time'

const { Title } = Typography

// 任务类型名称映射
const TASK_TYPE_NAMES: Record<string, string> = {
  geo_refresh: 'GEO/AEO刷新',
  monitor_collect: '监测采集',
  article_generate: '文章生成',
  image_generate: '图片生成',
  video_generate: '视频生成',
  agent_chat: '智能体对话',
}

// 状态配置
const STATUS_CONFIG: Record<string, { color: string; label: string; icon: any }> = {
  queued: { color: 'default', label: '等待中', icon: <ClockCircleOutlined /> },
  running: { color: 'processing', label: '执行中', icon: <LoadingOutlined /> },
  cancelling: { color: 'warning', label: '取消中', icon: <LoadingOutlined /> },
  succeeded: { color: 'success', label: '已完成', icon: <CheckCircleOutlined /> },
  failed: { color: 'error', label: '失败', icon: <CloseCircleOutlined /> },
  cancelled: { color: 'warning', label: '已取消', icon: <CloseCircleOutlined /> },
}

const TaskCenter = () => {
  const [tasks, setTasks] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)

  const fetchTasks = useCallback(async () => {
    setLoading(true)
    try {
      const res: any = await taskApi.list({ page, page_size: pageSize, status: statusFilter })
      setTasks(res.data.items)
      setTotal(res.data.total)
    } catch (e) {
      // 错误已由拦截器处理
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, statusFilter])

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  // 自动刷新：有 running/queued/cancelling 任务时每10秒刷新一次
  useEffect(() => {
    const hasActive = tasks.some(t => t.status === 'running' || t.status === 'queued' || t.status === 'cancelling')
    if (!hasActive) return
    const timer = setInterval(fetchTasks, 10000)
    return () => clearInterval(timer)
  }, [tasks, fetchTasks])

  const handleCancel = async (id: number) => {
    try {
      await taskApi.cancel(id)
      message.success('任务已取消')
      fetchTasks()
    } catch (e) {
      // 错误已处理
    }
  }

  const columns = [
    {
      title: '任务',
      dataIndex: 'task_type',
      width: 200,
      render: (type: string, record: any) => (
        <div>
          <div>{TASK_TYPE_NAMES[type] || type} #{record.user_seq || record.id}</div>
          <div style={{ fontSize: 12, color: '#94a3b8' }}>{record.created_at?.slice(5, 16)}</div>
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 120,
      render: (status: string) => {
        const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.queued
        return <Tag icon={cfg.icon} color={cfg.color}>{cfg.label}</Tag>
      },
    },
    {
      title: '进度',
      dataIndex: 'progress',
      width: 180,
      render: (progress: number, record: any) => {
        if (record.status === 'succeeded') return <Progress percent={100} size="small" status="success" />
        if (record.status === 'failed') return <Progress percent={100} size="small" status="exception" />
        if (record.status === 'cancelled') return <Progress percent={progress || 0} size="small" showInfo={false} />
        if (record.status === 'cancelling') return <Progress percent={progress || 0} size="small" status="active" />
        if (record.status === 'running') return <Progress percent={progress || 0} size="small" status="active" />
        return <Progress percent={0} size="small" />
      },
    },
    {
      title: '进度说明',
      dataIndex: 'progress_message',
      ellipsis: true,
      render: (msg: string, record: any) => {
        if (record.status === 'failed' && record.error_message) {
          return (
            <Tooltip title={record.error_message} placement="topLeft">
              <span style={{ color: '#ff4d4f', fontSize: 13 }}>
                <WarningOutlined style={{ marginRight: 4 }} />
                {record.error_message}
              </span>
            </Tooltip>
          )
        }
        return msg || '-'
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 170,
      render: (t: string) => formatTime(t),
    },
    {
      title: '操作',
      width: 100,
      render: (_: any, record: any) => (
        record.status === 'queued' ? (
          <Popconfirm title="确定取消该任务？" onConfirm={() => handleCancel(record.id)} okText="取消任务" cancelText="再想想">
            <Button type="link" danger size="small">取消</Button>
          </Popconfirm>
        ) : record.status === 'running' ? (
          <Popconfirm title="确定取消正在执行的任务？已采集的部分数据将保留，但任务会标记为失败。" onConfirm={() => handleCancel(record.id)} okText="取消任务" cancelText="再想想">
            <Button type="link" danger size="small">取消</Button>
          </Popconfirm>
        ) : '-'
      ),
    },
  ]

  const runningCount = tasks.filter(t => t.status === 'running' || t.status === 'queued' || t.status === 'cancelling').length

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          任务中心
          {runningCount > 0 && (
            <Badge count={runningCount} style={{ marginLeft: 12, backgroundColor: '#1890ff' }} />
          )}
        </Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchTasks} loading={loading}>刷新</Button>
        </Space>
      </div>

      <Card>
        <Table
          columns={columns}
          dataSource={tasks}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条任务`,
            onChange: (p, ps) => { setPage(p); setPageSize(ps) },
          }}
          locale={{ emptyText: <Empty description="暂无任务" /> }}
        />
      </Card>
    </div>
  )
}

export default TaskCenter
