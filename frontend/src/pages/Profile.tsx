import { useState, useEffect, useMemo } from 'react'
import {
  Form, Input, Select, Button, message, Spin, Space, Collapse,
  Tag, Tooltip, Divider, Card, Progress, Modal
} from 'antd'
import {
  CheckCircleOutlined, WarningOutlined, ExclamationCircleOutlined,
  PlusOutlined, DeleteOutlined, GlobalOutlined, LinkOutlined,
  ClockCircleOutlined, SaveOutlined, DownloadOutlined, EyeOutlined,
  UserOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { doctorApi, entityApi } from '@/api'
import { useAppStore } from '@/store/useStore'

const { TextArea } = Input

const TITLE_OPTIONS = ['主任医师', '副主任医师', '主治医师', '住院医师', '其他']

const SOCIAL_PLATFORMS = [
  { value: 'zhihu', label: '知乎', color: '#0084FF' },
  { value: 'wechat', label: '公众号', color: '#07C160' },
  { value: 'xiaohongshu', label: '小红书', color: '#FF2442' },
  { value: 'weibo', label: '微博', color: '#E6162D' },
  { value: 'douyin', label: '抖音', color: '#000000' },
  { value: 'bilibili', label: 'B站', color: '#FB7299' },
  { value: 'haodf', label: '好大夫', color: '#1890FF' },
  { value: 'other', label: '其他', color: '#999' },
]

const CLINIC_DAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const CLINIC_TIMES = ['上午', '下午', '晚上', '全天']

// 资料完整度检查项
const COMPLETENESS_CHECKS = [
  { key: 'real_name', label: '真实姓名', weight: 10 },
  { key: 'hospital', label: '医院全称', weight: 15 },
  { key: 'department', label: '科室', weight: 10 },
  { key: 'city', label: '城市', weight: 5 },
  { key: 'specialty', label: '专长疾病', weight: 15 },
  { key: 'title', label: '职称', weight: 5 },
  { key: 'bio', label: '个人简介', weight: 10 },
  { key: 'social_links', label: '社交媒体', weight: 10 },
  { key: 'avatar_url', label: '头像', weight: 5 },
  { key: 'personal_website', label: '个人网站', weight: 5 },
  { key: 'registration_url', label: '挂号链接', weight: 5 },
]

const Profile = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [entityScore, setEntityScore] = useState<any>(null)
  const [showSuccess, setShowSuccess] = useState(false)
  const [specialtyTags, setSpecialtyTags] = useState<string[]>([])
  const [socialLinks, setSocialLinks] = useState<Array<{ platform: string; url: string }>>([])
  const [clinicHours, setClinicHours] = useState<Array<{ day: string; time: string }>>([])
  const navigate = useNavigate()
  const { setDoctorProfile } = useAppStore()

  // 监听表单变化，实时计算完整度
  const formValues = Form.useWatch((values: any) => values, form)

  const completeness = useMemo(() => {
    if (!formValues) return { score: 0, missing: [] }
    let score = 0
    const missing: string[] = []
    for (const check of COMPLETENESS_CHECKS) {
      const val = formValues[check.key]
      const hasValue = val && (Array.isArray(val) ? val.length > 0 : String(val).trim() !== '')
      if (hasValue) {
        score += check.weight
      } else {
        missing.push(check.label)
      }
    }
    return { score, missing }
  }, [formValues])

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
        // 解析专长标签
        if (res.data.specialty) {
          setSpecialtyTags(res.data.specialty.split(',').map((s: string) => s.trim()).filter(Boolean))
        }
        // 解析社交媒体链接
        try {
          if (res.data.social_links) {
            setSocialLinks(JSON.parse(res.data.social_links))
          }
        } catch (e) { setSocialLinks([]) }
        // 解析出诊时间
        try {
          if (res.data.clinic_hours) {
            setClinicHours(JSON.parse(res.data.clinic_hours))
          }
        } catch (e) { setClinicHours([]) }
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
      // 组装专长（标签转逗号分隔）
      values.specialty = specialtyTags.join(',')
      // 组装社交媒体链接
      values.social_links = JSON.stringify(socialLinks)
      // 组装出诊时间
      values.clinic_hours = JSON.stringify(clinicHours)

      const res: any = await doctorApi.saveProfile(values)
      message.success('保存成功，语义问题正在后台生成中')
      setDoctorProfile(res.data?.profile)
      setShowSuccess(true)
    } catch (e) {
      // 拦截器已提示
    } finally {
      setSaving(false)
    }
  }

  const handleDownloadLlms = () => {
    const token = localStorage.getItem('geo_token')
    fetch('/geo/api/v1/template/llms.txt', {
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

  // 专长标签处理
  const handleSpecialtyInputConfirm = (inputValue: string) => {
    const trimmed = inputValue.trim()
    if (trimmed && !specialtyTags.includes(trimmed)) {
      setSpecialtyTags([...specialtyTags, trimmed])
    }
  }

  const handleSpecialtyTagRemove = (tag: string) => {
    setSpecialtyTags(specialtyTags.filter(t => t !== tag))
  }

  // 社交媒体链接处理
  const addSocialLink = () => {
    setSocialLinks([...socialLinks, { platform: 'zhihu', url: '' }])
  }

  const updateSocialLink = (index: number, field: string, value: string) => {
    const updated = [...socialLinks]
    updated[index] = { ...updated[index], [field]: value }
    setSocialLinks(updated)
  }

  const removeSocialLink = (index: number) => {
    setSocialLinks(socialLinks.filter((_, i) => i !== index))
  }

  // 出诊时间处理
  const addClinicHour = () => {
    setClinicHours([...clinicHours, { day: '周一', time: '上午' }])
  }

  const updateClinicHour = (index: number, field: string, value: string) => {
    const updated = [...clinicHours]
    updated[index] = { ...updated[index], [field]: value }
    setClinicHours(updated)
  }

  const removeClinicHour = (index: number) => {
    setClinicHours(clinicHours.filter((_, i) => i !== index))
  }

  const scoreGradient = entityScore?.score >= 80
    ? 'var(--success-gradient)'
    : entityScore?.score >= 60
      ? 'var(--warning-gradient)'
      : 'var(--danger-gradient)'

  const collapseItems = [
    {
      key: 'basic',
      label: <span><span style={{ fontWeight: 600 }}>📋 基本信息</span> <span style={{ color: '#999', fontSize: 12, marginLeft: 8 }}>GEO核心，必填</span></span>,
      children: (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div style={{ display: 'flex', gap: 16 }}>
            <Form.Item name="real_name" label="真实姓名" rules={[{ required: true, message: '请输入真实姓名' }]} style={{ flex: 1 }}>
              <Input placeholder="如：张医生" />
            </Form.Item>
            <Form.Item name="title" label="职称" style={{ flex: 1 }}>
              <Select options={TITLE_OPTIONS.map(t => ({ label: t, value: t }))} />
            </Form.Item>
          </div>
          <div style={{ display: 'flex', gap: 16 }}>
            <Form.Item name="province" label="省份" style={{ flex: 1 }}>
              <Input placeholder="如：广东省" />
            </Form.Item>
            <Form.Item name="city" label="城市" rules={[{ required: true, message: '请输入城市' }]} style={{ flex: 1 }}>
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
            label="专长疾病"
            extra="输入后回车添加标签，多个专长用标签管理，自动用于语义延伸和内容生成"
          >
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
              {specialtyTags.map(tag => (
                <Tag
                  key={tag}
                  closable
                  onClose={() => handleSpecialtyTagRemove(tag)}
                  color="blue"
                  style={{ fontSize: 13, padding: '2px 8px' }}
                >
                  {tag}
                </Tag>
              ))}
              <Input
                placeholder="输入专长后回车添加，如：妇科炎症"
                size="small"
                style={{ width: 200 }}
                onPressEnter={(e) => {
                  handleSpecialtyInputConfirm((e.target as HTMLInputElement).value)
                  ;(e.target as HTMLInputElement).value = ''
                }}
              />
            </div>
          </Form.Item>
        </Space>
      ),
    },
    {
      key: 'brand',
      label: <span><span style={{ fontWeight: 600 }}>✍️ 个人品牌</span> <span style={{ color: '#999', fontSize: 12, marginLeft: 8 }}>AEO核心，提升引用率</span></span>,
      children: (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Form.Item name="avatar_url" label="头像URL">
            <Input placeholder="如：https://example.com/avatar.jpg（二期支持本地上传）" />
          </Form.Item>
          <Form.Item name="bio" label="个人简介">
            <TextArea rows={4} placeholder="200-500字，介绍您的执业经历、专业擅长、诊疗理念等。AI会引用这段内容。" showCount maxLength={500} />
          </Form.Item>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontSize: 14, fontWeight: 500 }}>社交媒体链接</span>
              <Button type="dashed" size="small" icon={<PlusOutlined />} onClick={addSocialLink}>添加链接</Button>
            </div>
            {socialLinks.length === 0 && (
              <div style={{ color: '#999', fontSize: 12, padding: '8px 0' }}>暂无社交媒体链接，点击"添加链接"添加知乎/公众号/小红书等</div>
            )}
            {socialLinks.map((link, index) => (
              <div key={index} style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                <Select
                  value={link.platform}
                  onChange={(v) => updateSocialLink(index, 'platform', v)}
                  style={{ width: 120 }}
                >
                  {SOCIAL_PLATFORMS.map(p => (
                    <Select.Option key={p.value} value={p.value}>{p.label}</Select.Option>
                  ))}
                </Select>
                <Input
                  value={link.url}
                  onChange={(e) => updateSocialLink(index, 'url', e.target.value)}
                  placeholder="粘贴链接URL"
                  style={{ flex: 1 }}
                />
                <Button type="text" danger icon={<DeleteOutlined />} onClick={() => removeSocialLink(index)} />
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 16 }}>
            <Form.Item name="personal_website" label="个人网站" style={{ flex: 1 }}>
              <Input placeholder="如：https://drzhang.com" prefix={<GlobalOutlined />} />
            </Form.Item>
            <Form.Item name="registration_url" label="挂号链接" style={{ flex: 1 }}>
              <Input placeholder="如：好大夫/微医挂号页URL" prefix={<LinkOutlined />} />
            </Form.Item>
          </div>
        </Space>
      ),
    },
    {
      key: 'practice',
      label: <span><span style={{ fontWeight: 600 }}>🏥 执业信息</span> <span style={{ color: '#999', fontSize: 12, marginLeft: 8 }}>可选，提升专业可信度</span></span>,
      children: (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontSize: 14, fontWeight: 500 }}>出诊时间</span>
              <Button type="dashed" size="small" icon={<PlusOutlined />} onClick={addClinicHour}>添加出诊</Button>
            </div>
            {clinicHours.length === 0 && (
              <div style={{ color: '#999', fontSize: 12, padding: '8px 0' }}>暂无出诊时间</div>
            )}
            {clinicHours.map((item, index) => (
              <div key={index} style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                <Select
                  value={item.day}
                  onChange={(v) => updateClinicHour(index, 'day', v)}
                  style={{ width: 100 }}
                >
                  {CLINIC_DAYS.map(d => <Select.Option key={d} value={d}>{d}</Select.Option>)}
                </Select>
                <Select
                  value={item.time}
                  onChange={(v) => updateClinicHour(index, 'time', v)}
                  style={{ width: 100 }}
                >
                  {CLINIC_TIMES.map(t => <Select.Option key={t} value={t}>{t}</Select.Option>)}
                </Select>
                <Button type="text" danger icon={<DeleteOutlined />} onClick={() => removeClinicHour(index)} />
              </div>
            ))}
          </div>
          <Form.Item name="case_history" label="治病履历/数据统计">
            <TextArea rows={2} placeholder="如：从业15年，累计接诊妇科炎症患者5000+例" />
          </Form.Item>
        </Space>
      ),
    },
    {
      key: 'academic',
      label: <span><span style={{ fontWeight: 600 }}>🏆 学术成果</span> <span style={{ color: '#999', fontSize: 12, marginLeft: 8 }}>可选，二期细化为动态添加</span></span>,
      children: (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Form.Item name="awards" label="获奖履历">
            <TextArea rows={2} placeholder="如：2023年深圳市优秀医师" />
          </Form.Item>
          <div style={{ background: '#F8FAFC', padding: '10px 14px', borderRadius: 8, fontSize: 12, color: '#64748B' }}>
            💡 论文、课题等复杂字段将在二期支持动态添加多条记录
          </div>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div className="page-title-bar">
        <div>
          <h2>我的资料</h2>
          <div className="page-desc">完善医生资料是 GEO 优化的基础，资料越完整，AI 识别越准确</div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start' }}>
        {/* 左侧：医生名片 + 完整度 + 快捷操作 */}
        <div style={{ width: 280, flexShrink: 0 }}>
          {/* 医生名片 */}
          <div className="geo-card" style={{ marginBottom: 16, padding: 20, textAlign: 'center' }}>
            <div style={{
              width: 80, height: 80, borderRadius: '50%', margin: '0 auto 12px',
              background: 'var(--primary-gradient)', display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 32, color: '#fff', overflow: 'hidden'
            }}>
              {formValues?.avatar_url ? (
                <img src={formValues.avatar_url} alt="avatar" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              ) : (
                <UserOutlined />
              )}
            </div>
            <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>
              {formValues?.real_name || '未填写姓名'}
            </div>
            <div style={{ fontSize: 13, color: '#64748B', marginBottom: 4 }}>
              {formValues?.title || '未填写职称'}
            </div>
            <div style={{ fontSize: 13, color: '#64748B', marginBottom: 2 }}>
              {formValues?.hospital || '未填写医院'}
            </div>
            <div style={{ fontSize: 13, color: '#64748B' }}>
              {formValues?.department || '未填写科室'}
            </div>
          </div>

          {/* 资料完整度 */}
          <div className="geo-card" style={{ marginBottom: 16, padding: 20 }}>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>📊 资料完整度</div>
            <Progress
              type="circle"
              percent={completeness.score}
              size={120}
              strokeColor={{
                '0%': '#10B981',
                '100%': '#3B82F6',
              }}
              format={(percent) => `${percent}%`}
              style={{ margin: '0 auto 12px', display: 'block' }}
            />
            {completeness.missing.length > 0 ? (
              <div>
                <div style={{ fontSize: 12, color: '#F59E0B', marginBottom: 6, fontWeight: 500 }}>
                  还差 {completeness.missing.length} 项可到100%：
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {completeness.missing.map(item => (
                    <Tag key={item} color="orange" style={{ fontSize: 11 }}>{item}</Tag>
                  ))}
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', color: '#10B981', fontSize: 13 }}>
                <CheckCircleOutlined /> 资料已完善
              </div>
            )}
          </div>

          {/* 实体一致性评分 */}
          {entityScore && (
            <div className="stat-card-gradient" style={{ background: scoreGradient, marginBottom: 16, padding: 16 }}>
              <div style={{ textAlign: 'center', marginBottom: 8 }}>
                <div style={{ fontSize: 28, fontWeight: 700 }}>{entityScore.score}</div>
                <div style={{ fontSize: 11, opacity: 0.9 }}>实体一致性评分</div>
              </div>
              <div style={{ fontSize: 12, opacity: 0.95 }}>
                {entityScore.passed ? (
                  <span><CheckCircleOutlined /> 实体信息完整，AI识别无歧义</span>
                ) : (
                  <span><WarningOutlined /> 存在 {entityScore.issues.filter((i:any)=>i.level!=='info').length} 个需优化问题</span>
                )}
              </div>
            </div>
          )}

          {/* 快捷操作 */}
          <div className="geo-card" style={{ padding: 16 }}>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>🎯 快捷操作</div>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button block icon={<EyeOutlined />} onClick={() => navigate('/data')}>
                去采集看AI效果
              </Button>
              <Button block icon={<DownloadOutlined />} onClick={handleDownloadLlms}>
                下载 llms.txt
              </Button>
              <Button block icon={<PlusOutlined />} onClick={() => navigate('/semantic')}>
                管理语义问题
              </Button>
            </Space>
          </div>
        </div>

        {/* 右侧：分组表单 */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="geo-card">
            <Spin spinning={loading}>
              <Form
                form={form}
                layout="vertical"
                onFinish={handleSave}
                initialValues={{ title: '主治医师' }}
              >
                <Collapse
                  defaultActiveKey={['basic', 'brand']}
                  items={collapseItems}
                  style={{ background: 'transparent', border: 'none' }}
                />

                <Divider style={{ margin: '16px 0' }} />

                <Form.Item>
                  <Space>
                    <Button type="primary" htmlType="submit" loading={saving} icon={<SaveOutlined />} className="btn-primary-gradient" size="large">
                      保存资料
                    </Button>
                    <Button size="large" onClick={() => message.info('已保存，可继续完善其他信息')}>
                      保存并继续编辑
                    </Button>
                  </Space>
                </Form.Item>
              </Form>
            </Spin>
          </div>
        </div>
      </div>

      {/* 保存成功引导弹窗 */}
      <Modal
        open={showSuccess}
        onCancel={() => setShowSuccess(false)}
        footer={null}
        width={500}
      >
        <div style={{ textAlign: 'center', padding: '20px 0' }}>
          <div style={{ fontSize: 48, color: '#10B981', marginBottom: 16 }}>
            <CheckCircleOutlined />
          </div>
          <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>资料保存成功！</div>
          <div style={{ fontSize: 14, color: '#64748B', marginBottom: 24 }}>
            医生资料已更新，系统正在后台生成语义问题，可在「任务中心」查看进度
          </div>
          <div style={{ background: '#F0F9FF', padding: 16, borderRadius: 12, textAlign: 'left', marginBottom: 20 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#0369A1', marginBottom: 8 }}>📋 下一步建议</div>
            <div style={{ fontSize: 12, color: '#0369A1', lineHeight: 1.8 }}>
              1. 去「语义库」查看和管理生成的语义问题<br />
              2. 去「数据中心」跑采集，查看 AI 搜索效果<br />
              3. 去「内容中心」基于内容机会生成文章
            </div>
          </div>
          <Space>
            <Button type="primary" onClick={() => { setShowSuccess(false); navigate('/semantic') }} className="btn-primary-gradient">
              去语义库
            </Button>
            <Button onClick={() => { setShowSuccess(false); navigate('/data') }}>
              去采集
            </Button>
            <Button onClick={() => setShowSuccess(false)}>
              继续编辑
            </Button>
          </Space>
        </div>
      </Modal>
    </div>
  )
}

export default Profile
