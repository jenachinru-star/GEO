import { useState, useEffect } from 'react'
import { Form, Input, Select, Button, message, Spin, Space } from 'antd'
import { CheckCircleOutlined, WarningOutlined, ExclamationCircleOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { doctorApi, entityApi } from '@/api'
import { useAppStore } from '@/store/useStore'

const { TextArea } = Input

const TITLE_OPTIONS = ['主任医师', '副主任医师', '主治医师', '住院医师', '其他']

const Profile = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [entityScore, setEntityScore] = useState<any>(null)
  const navigate = useNavigate()
  const { setDoctorProfile } = useAppStore()

  useEffect(() => {
    loadProfile()
    loadEntityScore()
  }, [])

  const loadEntityScore = async () => {
    try {
      const res: any = await entityApi.getProfileScore()
      setEntityScore(res.data)
    } catch (e) {}
  }

  const loadProfile = async () => {
    setLoading(true)
    try {
      const res: any = await doctorApi.getProfile()
      if (res.data) {
        form.setFieldsValue(res.data)
        setDoctorProfile(res.data)
      }
    } catch (e) {
      // 未创建Profile时返回null，正常
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async (values: any) => {
    setSaving(true)
    try {
      const res: any = await doctorApi.saveProfile(values)
      message.success(`保存成功，已自动生成 ${res.data?.semantic_generated || 0} 个语义问题`)
      setDoctorProfile(res.data?.profile)
      setTimeout(() => navigate('/semantic'), 1000)
    } catch (e) {
      // 拦截器已提示
    } finally {
      setSaving(false)
    }
  }

  const handleDownloadLlms = () => {
    // 用token直接fetch下载（不能用axios，会把响应当JSON）
    const token = localStorage.getItem('geo_token')
    fetch('/api/v1/template/llms.txt', {
      headers: { 'Authorization': `Bearer ${token}` }
    }).then(r => {
      if (!r.ok) throw new Error('下载失败')
      return r.text()
    }).then(text => {
      const blob = new Blob([text], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'llms.txt'
      a.click()
      URL.revokeObjectURL(url)
      message.success('llms.txt 已下载，可部署到个人网站根目录帮助AI爬虫识别')
    }).catch(() => {
      message.error('下载失败，请先完善医生资料')
    })
  }

  // 实时计算自我介绍预览
  const introPreview = Form.useWatch((values: any) => {
    const city = values?.city || ''
    const hospital = values?.hospital || ''
    const department = values?.department || ''
    const realName = values?.real_name || ''
    return `${city}${hospital}${department}${realName}医生`
  }, form)

  const scoreGradient = entityScore?.score >= 80
    ? 'var(--success-gradient)'
    : entityScore?.score >= 60
      ? 'var(--warning-gradient)'
      : 'var(--danger-gradient)'

  return (
    <div style={{ maxWidth: 800 }}>
      <div className="page-title-bar">
        <div>
          <h2>我的资料</h2>
          <div className="page-desc">完善资料后，系统将自动为您生成患者会搜索的语义问题</div>
        </div>
      </div>

      {entityScore && (
        <div className="stat-card-gradient" style={{ background: scoreGradient, marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 36, fontWeight: 700 }}>
                {entityScore.score}
              </div>
              <div style={{ fontSize: 12, opacity: 0.9 }}>实体一致性评分</div>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 500, marginBottom: 8 }}>
                {entityScore.passed ? (
                  <span><CheckCircleOutlined /> 实体信息完整，AI识别无歧义</span>
                ) : (
                  <span><WarningOutlined /> 存在 {entityScore.issues.filter((i:any)=>i.level!=='info').length} 个需要优化的问题</span>
                )}
              </div>
              {entityScore.issues.slice(0, 3).map((issue: any, idx: number) => (
                <div key={idx} style={{ fontSize: 12, opacity: 0.9, marginBottom: 2 }}>
                  <ExclamationCircleOutlined style={{ marginRight: 4 }} />
                  {issue.message} — {issue.suggestion}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="geo-card">
        <Spin spinning={loading}>
          <Form
            form={form}
            layout="vertical"
            onFinish={handleSave}
            initialValues={{ title: '主治医师' }}
          >
            <Form.Item name="real_name" label="真实姓名" rules={[{ required: true, message: '请输入真实姓名' }]}>
              <Input placeholder="如：张医生" />
            </Form.Item>

            <Form.Item name="title" label="职称">
              <Select options={TITLE_OPTIONS.map(t => ({ label: t, value: t }))} />
            </Form.Item>

            <div style={{ display: 'flex', gap: 16 }}>
              <Form.Item name="province" label="省份" style={{ flex: 1 }}>
                <Input placeholder="如：广东省" />
              </Form.Item>
              <Form.Item name="city" label="城市" style={{ flex: 1 }} rules={[{ required: true, message: '请输入城市' }]}>
                <Input placeholder="如：深圳市" />
              </Form.Item>
            </div>

            <Form.Item
              name="hospital"
              label="医院全称"
              rules={[{ required: true, message: '请输入医院全称' }]}
              extra={<span style={{ color: '#F59E0B' }}>请填写完整全称，不要用简称。AI会因为信息不一致而降权。</span>}
            >
              <Input placeholder="如：深圳市第一人民医院" />
            </Form.Item>

            <Form.Item name="department" label="科室" rules={[{ required: true, message: '请输入科室' }]}>
              <Input placeholder="如：妇科" />
            </Form.Item>

            <Form.Item
              name="specialty"
              label="专长疾病"
              extra="多个专长用逗号分隔，如：妇科炎症,月经不调,不孕症"
            >
              <Input placeholder="如：妇科炎症" />
            </Form.Item>

            <Form.Item name="awards" label="获奖履历（可选）">
              <TextArea rows={2} placeholder="如：2023年深圳市优秀医师" />
            </Form.Item>

            <Form.Item name="case_history" label="治病履历/数据统计（可选）">
              <TextArea rows={2} placeholder="如：从业15年，累计接诊妇科炎症患者5000+例" />
            </Form.Item>

            <div style={{ background: '#EFF6FF', padding: 16, borderRadius: 12, marginBottom: 16 }}>
              <div style={{ fontSize: 12, color: '#64748B' }}>统一自我介绍格式（自动生成，全网分发时保持一致）：</div>
              <div style={{ fontSize: 15, fontWeight: 600, color: '#1D4ED8', marginTop: 4 }}>
                {introPreview || '填写信息后自动生成'}
              </div>
            </div>

            <Form.Item>
              <Space>
                <Button type="primary" htmlType="submit" loading={saving} className="btn-primary-gradient">
                  保存并生成语义
                </Button>
                <Button onClick={handleDownloadLlms} className="btn-primary-gradient">
                  下载 llms.txt
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Spin>
      </div>
    </div>
  )
}

export default Profile
