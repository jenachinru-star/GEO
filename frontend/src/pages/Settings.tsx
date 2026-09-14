import { useEffect, useState } from 'react'
import {
  Row, Col, Card, Tag, Button, Space, Descriptions,
  Table, message, Modal
} from 'antd'
import {
  CheckCircleOutlined, CloseCircleOutlined,
  ReloadOutlined, PlayCircleOutlined, DatabaseOutlined
} from '@ant-design/icons'
import { systemApi, monitorApi } from '@/api'

const Settings = () => {
  const [systemInfo, setSystemInfo] = useState<any>(null)
  const [platforms, setPlatforms] = useState<any[]>([])
  const [collecting, setCollecting] = useState(false)

  const loadData = async () => {
    try {
      const [infoRes, platformRes]: any[] = await Promise.all([
        systemApi.getInfo(),
        systemApi.getPlatforms()
      ])
      setSystemInfo(infoRes.data)
      setPlatforms(platformRes.data)
    } catch (e) {}
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleInitDemo = async () => {
    Modal.confirm({
      title: '初始化演示数据',
      content: '将添加默认监测问题（10个）和知识库条目（4个），已有数据将跳过。是否继续？',
      onOk: async () => {
        try {
          const res: any = await systemApi.initDemo()
          if (res.data.skipped) {
            message.info('已有数据，跳过初始化')
          } else {
            message.success(`初始化成功：${res.data.questions}个问题，${res.data.knowledge}条知识`)
          }
        } catch (e) {}
      }
    })
  }

  const handleCollectAll = async () => {
    setCollecting(true)
    try {
      const res: any = await monitorApi.collect({ detect_round: 1 })
      message.success(`采集完成：${res.data.success}/${res.data.total} 个问题，${res.data.records_count} 条记录`)
    } finally {
      setCollecting(false)
    }
  }

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>系统设置</h2>
          <div className="page-desc">查看系统状态、平台配置与快捷操作</div>
        </div>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </div>

      {/* 系统信息 */}
      <div className="geo-card" style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 15, marginBottom: 16 }}>
          <DatabaseOutlined style={{ marginRight: 8, color: '#0EA5E9' }} />
          系统信息
        </h3>
        <Descriptions column={{ xs: 1, sm: 2, md: 3 }}>
          <Descriptions.Item label="应用名称">{systemInfo?.app_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="版本">{systemInfo?.version || '-'}</Descriptions.Item>
          <Descriptions.Item label="运行环境">
            <Tag color={systemInfo?.env === 'production' ? 'green' : 'blue'}>
              {systemInfo?.env || '-'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="监控品牌">{systemInfo?.brand_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="品牌别名">
            {systemInfo?.brand_aliases?.map((a: string, i: number) => (
              <Tag key={i} style={{ marginBottom: 4 }}>{a}</Tag>
            ))}
          </Descriptions.Item>
          <Descriptions.Item label="已启用平台">
            {systemInfo?.enabled_platforms?.map((p: string, i: number) => (
              <Tag key={i} color="green">{p}</Tag>
            ))}
          </Descriptions.Item>
        </Descriptions>
      </div>

      {/* 平台状态 */}
      <div className="geo-card" style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 15, marginBottom: 16 }}>AI平台配置状态</h3>
        <Table
          dataSource={platforms}
          rowKey="code"
          pagination={false}
          columns={[
            { title: '平台', dataIndex: 'name', key: 'name', render: (t: string) => <span style={{ fontWeight: 500 }}>{t}</span> },
            { title: '标识', dataIndex: 'code', key: 'code' },
            { title: '模型', dataIndex: 'model', key: 'model', render: (t: string) => t || '-' },
            {
              title: 'API配置', dataIndex: 'configured', key: 'configured', width: 100,
              render: (v: boolean) => v
                ? <Tag color="green" icon={<CheckCircleOutlined />}>已配置</Tag>
                : <Tag color="default" icon={<CloseCircleOutlined />}>未配置</Tag>
            },
            {
              title: '状态', dataIndex: 'enabled', key: 'enabled', width: 100,
              render: (v: boolean) => v
                ? <Tag color="success">运行中</Tag>
                : <Tag color="default">未启用</Tag>
            }
          ]}
        />
        <div style={{ marginTop: 12, fontSize: 12, color: '#64748B' }}>
          提示：平台配置在 backend/.env 文件中修改，修改后重启服务生效
        </div>
      </div>

      {/* 快捷操作 */}
      <div className="geo-card">
        <h3 style={{ fontSize: 15, marginBottom: 16 }}>快捷操作</h3>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={8}>
            <Card size="small" hoverable>
              <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 8 }}>初始化演示数据</div>
              <div style={{ fontSize: 12, color: '#64748B', marginBottom: 12 }}>
                添加默认问题库和知识库条目，快速体验系统
              </div>
              <Button type="primary" block onClick={handleInitDemo}>
                初始化
              </Button>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Card size="small" hoverable>
              <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 8 }}>立即全量采集</div>
              <div style={{ fontSize: 12, color: '#64748B', marginBottom: 12 }}>
                对所有启用的问题执行一次全平台采集
              </div>
              <Button icon={<PlayCircleOutlined />} block loading={collecting} onClick={handleCollectAll}>
                开始采集
              </Button>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Card size="small" hoverable>
              <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 8 }}>API文档</div>
              <div style={{ fontSize: 12, color: '#64748B', marginBottom: 12 }}>
                查看后端API接口文档（Swagger UI）
              </div>
              <Button block onClick={() => window.open('/docs', '_blank')}>
                打开文档
              </Button>
            </Card>
          </Col>
        </Row>
      </div>
    </div>
  )
}

export default Settings
