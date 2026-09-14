# GEO 项目 P1.5 执行手册：我的资料重设计 + 发布管理 + 效果追踪

> **版本**：v1.0
> **创建时间**：2026-09-14
> **适用范围**：T10-T12（我的资料重新设计、发布管理前端、内容效果追踪基础版）
> **前置条件**：P0（T01-T06）+ P1（T07-T09）已全部完成并验证通过
> **执行方式**：分 2 个 Session 串行执行

---

## 一、项目状态快照

### 已完成
- P0（T01-T06）：Workspace/AsyncTask/Worker框架、Distribution状态机、分析器bug修复、采集异步化、任务查询API+前端任务中心、P0联调验收
- P1（T07-T09）：内容机会识别模块、文章生成引擎升级（LLM驱动）、生图适配器框架（配置留空）
- P1.5 前置：语义延伸功能（semantic_extender引擎+API+前端抽屉）、语义问题统一问号、Dashboard删"最高"、ContentHub重构为3个Tab（智能创作/创作工具/内容机会）

### 技术栈
- 后端：FastAPI + SQLAlchemy + SQLite + Python 3.11
- 前端：React 18 + TypeScript + Vite + AntD 5 + ECharts + Zustand
- 数据库：`backend/data/geo.db`（已备份 `geo.db.backup_before_upgrade`）
- Python环境：`C:\Users\jenac\AppData\Local\Programs\Python\Python311\python.exe`

### 本轮目标
打通"资料完善 → 内容生成 → 发布管理 → 效果追踪"的完整GEO优化闭环。

---

## 二、决策点记录

| # | 决策点 | 结论 |
|---|---|---|
| 1 | 我的资料设计范围 | 一期做：基本信息+个人品牌+资料完整度进度条+保存成功引导；二期做：执业经历/教育背景等复杂字段 |
| 2 | 头像上传 | 一期用URL输入，不做文件上传（需要后端存储接口，成本高） |
| 3 | AI识别效果预览 | 一期不做，加"去采集看效果"按钮跳数据中心（功能重叠） |
| 4 | 发布管理放置位置 | 独立页面 `/distribution`，左侧菜单加入口（Tab空间不够） |
| 5 | 发布方式 | 一期做"手动标记已发布"，不做实际API调用各平台（各平台API差异大） |
| 6 | 效果追踪 | 基础版：手动触发重新采集，对比发布前后GEO/AEO/排名变化 |
| 7 | 社交媒体链接存储 | 用JSON字段（简单，一期够用），二期规范化拆表 |
| 8 | Session划分 | 分2个Session：Session1=T10（资料重设计），Session2=T11+T12（发布管理+效果追踪） |

---

## 三、全局约定

### 命名规范
- 后端模型字段：snake_case
- 前端变量/函数：camelCase
- 新文件：功能清晰的英文命名

### 数据库迁移
- 所有表结构变更必须通过 `scripts/migrate_v2.py` 幂等迁移脚本
- 只加列/加表，不删列/不改列类型（安全第一）
- 迁移后必须验证二次运行无重复输出

### 验证要求
- 后端：所有模块 `import` 无错误
- 前端：`npx tsc --noEmit` exit code 0
- 每个任务完成后必须按"完成标准"逐项验证

### 运行命令
```bash
# 后端启动（带内嵌Worker）
cd C:\Users\jenac\Desktop\GEO\backend
C:\Users\jenac\AppData\Local\Programs\Python\Python311\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 前端类型检查
cd C:\Users\jenac\Desktop\GEO\frontend
npx tsc --noEmit

# 运行迁移
cd C:\Users\jenac\Desktop\GEO\backend
C:\Users\jenac\AppData\Local\Programs\Python\Python311\python.exe -m scripts.migrate_v2
```

---

## 四、Session 划分

| Session | 任务 | 内容 | 预计工作量 |
|---|---|---|---|
| Session 1 | T10 | 我的资料重新设计（一期） | 后端加字段+迁移+API，前端完全重写Profile |
| Session 2 | T11+T12 | 发布管理前端 + 内容效果追踪 | 后端加2个端点，前端新建Distribution页面+EffectTracker组件 |

---

## 五、T10：我的资料重新设计（一期）

### 5.1 任务目标
将"我的资料"页面从简单表单重构为"左侧名片+右侧分组表单"的专业医生资料管理页面，新增个人品牌字段（个人简介、社交媒体链接、个人网站、挂号链接），增加资料完整度进度条和保存成功引导。

### 5.2 后端改动

#### 5.2.1 修改模型：`backend/app/models/doctor.py`

**修改点**：新增 6 个字段

```python
# 在现有字段后追加：
    avatar_url = Column(String(500), default="")  # 头像URL（一期用URL，二期做上传）
    bio = Column(Text, default="")  # 个人简介
    social_links = Column(Text, default="[]")  # 社交媒体链接（JSON数组：[{"platform":"zhihu","url":"..."}]）
    personal_website = Column(String(500), default="")  # 个人网站
    registration_url = Column(String(500), default="")  # 挂号链接
    clinic_hours = Column(Text, default="[]")  # 出诊时间（JSON数组：[{"day":"周一","time":"上午"}]）
```

**完整文件代码**：

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class DoctorProfile(Base):
    """医生个人资料（GEO基础数据）"""
    __tablename__ = "geo_doctor_profile"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("geo_user.id"), unique=True, nullable=False, index=True)
    real_name = Column(String(100), nullable=False, default="")
    title = Column(String(100), default="")
    province = Column(String(50), default="")
    city = Column(String(50), default="")
    hospital = Column(String(200), default="")
    department = Column(String(100), default="")
    specialty = Column(String(500), default="")  # 逗号分隔
    awards = Column(Text, default="")
    case_history = Column(Text, default="")
    self_intro_template = Column(String(500), default="")
    # ===== V2.1 个人品牌新增字段 =====
    avatar_url = Column(String(500), default="")
    bio = Column(Text, default="")
    social_links = Column(Text, default="[]")
    personal_website = Column(String(500), default="")
    registration_url = Column(String(500), default="")
    clinic_hours = Column(Text, default="[]")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

#### 5.2.2 修改迁移脚本：`backend/scripts/migrate_v2.py`

**修改点**：在 `migrate()` 函数末尾追加医生资料新列迁移，新增迁移版本记录。

在 `record_migration(conn, "v2.1_semantic_extend")` 后追加：

```python
    # ===== 7. 医生资料个人品牌字段 =====
    print("[7/7] 医生资料个人品牌字段")
    ensure_column(conn, "geo_doctor_profile", "avatar_url", "TEXT DEFAULT ''")
    ensure_column(conn, "geo_doctor_profile", "bio", "TEXT DEFAULT ''")
    ensure_column(conn, "geo_doctor_profile", "social_links", "TEXT DEFAULT '[]'")
    ensure_column(conn, "geo_doctor_profile", "personal_website", "TEXT DEFAULT ''")
    ensure_column(conn, "geo_doctor_profile", "registration_url", "TEXT DEFAULT ''")
    ensure_column(conn, "geo_doctor_profile", "clinic_hours", "TEXT DEFAULT '[]'")

    record_migration(conn, "v2.2_doctor_brand")
```

同时把前面的 `[6/6]` 改成 `[6/7]`，`[5/6]` 改成 `[5/7]`（保持序号连续）。

#### 5.2.3 修改API：`backend/app/api/doctor.py`

**修改点1**：`get_profile` 返回新字段

在 `data` 字典中追加：
```python
        "avatar_url": profile.avatar_url,
        "bio": profile.bio,
        "social_links": profile.social_links,
        "personal_website": profile.personal_website,
        "registration_url": profile.registration_url,
        "clinic_hours": profile.clinic_hours,
```

**修改点2**：`save_profile` 的 `allowed_fields` 追加新字段

```python
    allowed_fields = ["real_name", "title", "province", "city", "hospital",
                      "department", "specialty", "awards", "case_history",
                      "avatar_url", "bio", "social_links", "personal_website",
                      "registration_url", "clinic_hours"]
```

**修改点3**：`save_profile` 返回的 profile 数据追加新字段（可选，前端用不到全部，但保持一致性）

在返回的 `profile` 字典中追加：
```python
                "avatar_url": profile.avatar_url,
                "bio": profile.bio,
                "hospital": profile.hospital,
                "department": profile.department,
                "specialty": profile.specialty,
```

### 5.3 前端改动

#### 5.3.1 完全重写：`frontend/src/pages/Profile.tsx`

**设计要点**：
- 左侧：医生名片（头像+姓名+职称+医院+科室）+ 资料完整度进度条 + 快捷操作
- 右侧：分组表单（基本信息/个人品牌/执业信息/学术成果），可折叠
- 专长疾病标签化输入
- 社交媒体链接动态添加
- 保存成功后不跳转，显示引导卡片

**完整代码**：

```tsx
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
      message.success(`保存成功，已自动生成 ${res.data?.semantic_generated || 0} 个语义问题`)
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
            医生资料已更新，系统已自动生成相关语义问题
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
```

### 5.4 验证步骤

1. **运行迁移**：
   ```bash
   cd C:\Users\jenac\Desktop\GEO\backend
   C:\Users\jenac\AppData\Local\Programs\Python\Python311\python.exe -m scripts.migrate_v2
   ```
   预期输出：`[7/7] 医生资料个人品牌字段` + 6个 `+ 列` + `+ 迁移记录 v2.2_doctor_brand`

2. **验证模型import**：
   ```bash
   C:\Users\jenac\AppData\Local\Programs\Python\Python311\python.exe -c "from app.models.doctor import DoctorProfile; print([c.name for c in DoctorProfile.__table__.columns])"
   ```
   预期：包含 `avatar_url, bio, social_links, personal_website, registration_url, clinic_hours`

3. **验证前端tsc**：
   ```bash
   cd C:\Users\jenac\Desktop\GEO\frontend
   npx tsc --noEmit
   ```
   预期：exit code 0

4. **功能验证**：
   - 重启后端，访问 `/profile` 页面
   - 左侧显示医生名片（头像+姓名+职称+医院+科室）
   - 资料完整度进度条实时计算，显示缺失项
   - 右侧4个可折叠分组（基本信息/个人品牌/执业信息/学术成果）
   - 专长疾病标签化输入（回车添加，可删除）
   - 社交媒体链接动态添加/删除
   - 保存后弹出成功引导卡片（不跳转）

### 5.5 完成标准

- [ ] 迁移脚本运行成功，6个新列已添加，二次运行幂等
- [ ] 后端模型 import 无错误，新字段已注册
- [ ] 后端 API 支持新字段的读取和保存
- [ ] 前端 tsc --noEmit exit code 0
- [ ] 页面布局：左侧名片+完整度+快捷操作，右侧分组表单
- [ ] 专长疾病标签化输入正常工作
- [ ] 社交媒体链接动态添加/删除正常
- [ ] 资料完整度实时计算，显示缺失项
- [ ] 保存成功后弹出引导卡片，不直接跳转
- [ ] 实体一致性评分正常显示

---

## 六、T11：发布管理前端页面

### 6.1 任务目标
新建独立的发布管理页面（`/distribution`），基于已有的 Distribution 状态机后端，实现文章多平台发布的排期、状态追踪、手动标记发布等功能。

### 6.2 后端确认

**后端已有（T02完成）**：
- 模型：`ArticleDistribution`（含状态机全部字段）
- 服务：`DistributionService`（合法流转校验、schedule/start/mark_published/mark_failed/retry/remove）
- API：
  - `GET /api/v1/distribution`（列表，支持 article_id/status 过滤）
  - `POST /api/v1/distribution`（创建）
  - `PATCH /api/v1/distribution/{id}/status`（状态流转）
  - `POST /api/v1/distribution/{id}/retry`（重试）
  - `DELETE /api/v1/distribution/{id}`（删除，仅 draft）

**后端需要补充**：列表接口返回文章标题和语义问题（当前只返回 article_id，前端需要关联查询）。

#### 6.2.1 修改API：`backend/app/api/distribution.py`

**修改点**：`get_distributions` 返回结果追加文章标题和语义问题。

在 `items = query.order_by(...).all()` 后，修改返回结构：

```python
    # 批量查询文章标题和语义
    article_ids = [d.article_id for d in items]
    articles = {}
    if article_ids:
        for a in db.query(ArticleDraft).filter(ArticleDraft.id.in_(article_ids)).all():
            articles[a.id] = a
    semantic_ids = [a.semantic_id for a in articles.values()]
    semantics = {}
    if semantic_ids:
        from app.models.semantic import Semantic
        for s in db.query(Semantic).filter(Semantic.id.in_(semantic_ids)).all():
            semantics[s.id] = s.question

    return {"code": 0, "message": "success", "data": {"items": [
        {
            "id": d.id,
            "article_id": d.article_id,
            "article_title": articles.get(d.article_id)?.title if hasattr(articles.get(d.article_id), 'title') else '',
            "semantic_id": articles.get(d.article_id)?.semantic_id if hasattr(articles.get(d.article_id), 'semantic_id') else None,
            "semantic_question": semantics.get(articles.get(d.article_id)?.semantic_id, '') if articles.get(d.article_id) else '',
            "platform": d.platform,
            "publish_url": d.publish_url,
            "status": d.status,
            "note": d.note,
            "publish_mode": d.publish_mode,
            "retry_count": d.retry_count,
            "failed_reason": d.failed_reason,
            "scheduled_at": d.scheduled_at.isoformat() if d.scheduled_at else None,
            "published_at": d.published_at.isoformat() if d.published_at else None,
            "verified_at": d.verified_at.isoformat() if d.verified_at else None,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in items
    ]}}
```

**注意**：Python 没有 `?.` 可选链，需要用普通写法。完整正确的代码：

```python
    # 批量查询文章标题和语义
    article_ids = list(set([d.article_id for d in items]))
    articles = {}
    if article_ids:
        for a in db.query(ArticleDraft).filter(ArticleDraft.id.in_(article_ids)).all():
            articles[a.id] = a
    semantic_ids = list(set([a.semantic_id for a in articles.values()]))
    semantics = {}
    if semantic_ids:
        from app.models.semantic import Semantic
        for s in db.query(Semantic).filter(Semantic.id.in_(semantic_ids)).all():
            semantics[s.id] = s.question

    result_items = []
    for d in items:
        article = articles.get(d.article_id)
        result_items.append({
            "id": d.id,
            "article_id": d.article_id,
            "article_title": article.title if article else '',
            "semantic_id": article.semantic_id if article else None,
            "semantic_question": semantics.get(article.semantic_id, '') if article else '',
            "platform": d.platform,
            "publish_url": d.publish_url,
            "status": d.status,
            "note": d.note,
            "publish_mode": d.publish_mode,
            "retry_count": d.retry_count,
            "failed_reason": d.failed_reason,
            "scheduled_at": d.scheduled_at.isoformat() if d.scheduled_at else None,
            "published_at": d.published_at.isoformat() if d.published_at else None,
            "verified_at": d.verified_at.isoformat() if d.verified_at else None,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        })

    return {"code": 0, "message": "success", "data": {"items": result_items}}
```

### 6.3 前端改动

#### 6.3.1 新增API方法：`frontend/src/api/index.ts`

在 `articleApi` 后追加：

```typescript
// ============ 发布管理 API ============
export const distributionApi = {
  getList: (params?: any) => request.get('/distribution', { params }),
  create: (data: any) => request.post('/distribution', data),
  updateStatus: (id: number, data: { status: string; publish_url?: string; note?: string }) =>
    request.patch(`/distribution/${id}/status`, data),
  retry: (id: number) => request.post(`/distribution/${id}/retry`),
  remove: (id: number) => request.delete(`/distribution/${id}`),
}
```

#### 6.3.2 新建页面：`frontend/src/pages/Distribution.tsx`

**完整代码**：

```tsx
import { useState, useEffect } from 'react'
import {
  Table, Button, Space, Tag, Modal, Form, Select, Input,
  message, Popconfirm, Statistic, Row, Col, Drawer, Descriptions,
  Timeline, Tooltip
} from 'antd'
import {
  PlusOutlined, ReloadOutlined, EyeOutlined, CheckOutlined,
  ClockCircleOutlined, SyncOutlined, DeleteOutlined, LinkOutlined,
  FileTextOutlined, BarChartOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { distributionApi, articleApi } from '@/api'
import { PUBLISH_PLATFORMS, PUBLISH_PLATFORM_NAMES } from '@/store/useStore'
import EffectTracker from '@/components/EffectTracker'

const { TextArea } = Input

// 状态配置
const STATUS_CONFIG: Record<string, { label: string; color: string; icon: any }> = {
  draft: { label: '草稿', color: 'default', icon: FileTextOutlined },
  scheduled: { label: '已排期', color: 'blue', icon: ClockCircleOutlined },
  processing: { label: '发布中', color: 'processing', icon: SyncOutlined },
  published: { label: '已发布', color: 'success', icon: CheckOutlined },
  failed: { label: '失败', color: 'error', icon: CloseOutlined },
  removed: { label: '已移除', color: 'default', icon: DeleteOutlined },
}

// 状态流转图
const STATUS_FLOW = ['draft', 'scheduled', 'processing', 'published']

const Distribution = () => {
  const [list, setList] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [articles, setArticles] = useState<any[]>([])
  const [createModal, setCreateModal] = useState(false)
  const [detailDrawer, setDetailDrawer] = useState(false)
  const [currentRecord, setCurrentRecord] = useState<any>(null)
  const [effectVisible, setEffectVisible] = useState(false)
  const [form] = Form.useForm()
  const [filters, setFilters] = useState({ status: '' as string, platform: '' as string })
  const navigate = useNavigate()

  useEffect(() => {
    loadArticles()
    loadList()
  }, [filters])

  const loadArticles = async () => {
    try {
      const res: any = await articleApi.getList({ page_size: 100 })
      setArticles(res.data.items || res.data || [])
    } catch (e) {}
  }

  const loadList = async () => {
    setLoading(true)
    try {
      const params: any = {}
      if (filters.status) params.status = filters.status
      if (filters.platform) params.platform = filters.platform
      const res: any = await distributionApi.getList(params)
      setList(res.data.items || [])
    } catch (e) {
      // 拦截器已提示
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (values: any) => {
    try {
      await distributionApi.create({
        article_id: values.article_id,
        platform: values.platform,
        status: values.status || 'draft',
        publish_url: values.publish_url || '',
        note: values.note || '',
      })
      message.success('创建发布记录成功')
      setCreateModal(false)
      form.resetFields()
      loadList()
    } catch (e) {
      // 拦截器已提示
    }
  }

  const handleStatusUpdate = async (record: any, status: string, publish_url?: string) => {
    try {
      await distributionApi.updateStatus(record.id, { status, publish_url })
      message.success(`状态已更新为「${STATUS_CONFIG[status]?.label}」`)
      loadList()
    } catch (e: any) {
      message.error(e.response?.data?.detail || '状态更新失败')
    }
  }

  const handleMarkPublished = (record: any) => {
    Modal.confirm({
      title: '标记为已发布',
      content: (
        <div>
          <p style={{ marginBottom: 8 }}>请确认已在「{PUBLISH_PLATFORM_NAMES[record.platform] || record.platform}」手动发布了这篇文章。</p>
          <Input
            placeholder="粘贴发布后的URL（可选，用于效果追踪）"
            id="publish_url_input"
            style={{ marginTop: 8 }}
          />
        </div>
      ),
      okText: '确认已发布',
      cancelText: '取消',
      onOk: () => {
        const url = (document.getElementById('publish_url_input') as HTMLInputElement)?.value || ''
        handleStatusUpdate(record, 'published', url)
      },
    })
  }

  const handleRetry = async (record: any) => {
    try {
      await distributionApi.retry(record.id)
      message.success('已重新加入发布队列')
      loadList()
    } catch (e) {
      message.error('重试失败')
    }
  }

  const handleViewDetail = (record: any) => {
    setCurrentRecord(record)
    setDetailDrawer(true)
  }

  // 统计
  const stats = {
    draft: list.filter(r => r.status === 'draft').length,
    scheduled: list.filter(r => r.status === 'scheduled').length,
    processing: list.filter(r => r.status === 'processing').length,
    published: list.filter(r => r.status === 'published').length,
    failed: list.filter(r => r.status === 'failed').length,
  }

  const columns = [
    {
      title: '文章标题', dataIndex: 'article_title', key: 'article_title',
      ellipsis: true, width: 250,
      render: (text: string, record: any) => (
        <a onClick={() => handleViewDetail(record)} style={{ fontWeight: 500 }}>
          {text || `文章#${record.article_id}`}
        </a>
      ),
    },
    {
      title: '关联语义', dataIndex: 'semantic_question', key: 'semantic_question',
      ellipsis: true, width: 200,
      render: (text: string) => <span style={{ color: '#64748B', fontSize: 12 }}>{text || '-'}</span>,
    },
    {
      title: '平台', dataIndex: 'platform', key: 'platform', width: 120,
      render: (p: string) => {
        const platform = PUBLISH_PLATFORMS.find((x: any) => x.code === p)
        return <Tag color={platform?.tier === 1 ? 'red' : platform?.tier === 2 ? 'orange' : 'default'}>
          {platform?.name || p}
        </Tag>
      },
    },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (status: string) => {
        const config = STATUS_CONFIG[status]
        const Icon = config?.icon || FileTextOutlined
        return <Tag color={config?.color} icon={<Icon />}>{config?.label || status}</Tag>
      },
    },
    {
      title: '排期时间', dataIndex: 'scheduled_at', key: 'scheduled_at', width: 160,
      render: (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-',
    },
    {
      title: '发布时间', dataIndex: 'published_at', key: 'published_at', width: 160,
      render: (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作', key: 'action', width: 280, fixed: 'right' as const,
      render: (_: any, record: any) => {
        const actions = []
        // 草稿 → 排期
        if (record.status === 'draft') {
          actions.push(
            <Button key="schedule" size="small" icon={<ClockCircleOutlined />} onClick={() => handleStatusUpdate(record, 'scheduled')}>
              排期
            </Button>
          )
        }
        // 已排期 → 开始发布
        if (record.status === 'scheduled') {
          actions.push(
            <Button key="start" size="small" type="primary" icon={<SyncOutlined />} onClick={() => handleStatusUpdate(record, 'processing')}>
              开始发布
            </Button>
          )
        }
        // 发布中 → 标记已发布
        if (record.status === 'processing') {
          actions.push(
            <Button key="publish" size="small" type="primary" icon={<CheckOutlined />} onClick={() => handleMarkPublished(record)}>
              标记已发布
            </Button>
          )
        }
        // 失败 → 重试
        if (record.status === 'failed') {
          actions.push(
            <Button key="retry" size="small" type="primary" icon={<SyncOutlined />} onClick={() => handleRetry(record)}>
              重试
            </Button>
          )
        }
        // 已发布 → 查看效果
        if (record.status === 'published') {
          actions.push(
            <Button key="effect" size="small" icon={<BarChartOutlined />} onClick={() => { setCurrentRecord(record); setEffectVisible(true) }}>
              效果追踪
            </Button>
          )
        }
        // 查看详情
        actions.push(
          <Button key="detail" size="small" icon={<EyeOutlined />} onClick={() => handleViewDetail(record)}>
            详情
          </Button>
        )
        // 草稿可删除
        if (record.status === 'draft') {
          actions.push(
            <Popconfirm key="delete" title="确定删除这条发布记录？" onConfirm={async () => {
              try { await distributionApi.remove(record.id); message.success('已删除'); loadList() }
              catch (e) { message.error('删除失败') }
            }}>
              <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
            </Popconfirm>
          )
        }
        return <Space size="small" wrap>{actions}</Space>
      },
    },
  ]

  return (
    <div>
      <div className="page-title-bar">
        <div>
          <h2>发布管理</h2>
          <div className="page-desc">管理文章的多平台发布排期、状态追踪和效果验证</div>
        </div>
        <Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModal(true)} className="btn-primary-gradient">
            新建发布
          </Button>
          <Button icon={<ReloadOutlined />} onClick={loadList}>刷新</Button>
        </Space>
      </div>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 20 }}>
        <Col xs={12} md={4}>
          <div className="geo-card" style={{ padding: 16 }}>
            <Statistic title="草稿" value={stats.draft} valueStyle={{ color: '#94A3B8' }} />
          </div>
        </Col>
        <Col xs={12} md={4}>
          <div className="geo-card" style={{ padding: 16 }}>
            <Statistic title="已排期" value={stats.scheduled} valueStyle={{ color: '#3B82F6' }} />
          </div>
        </Col>
        <Col xs={12} md={4}>
          <div className="geo-card" style={{ padding: 16 }}>
            <Statistic title="发布中" value={stats.processing} valueStyle={{ color: '#F59E0B' }} />
          </div>
        </Col>
        <Col xs={12} md={4}>
          <div className="geo-card" style={{ padding: 16 }}>
            <Statistic title="已发布" value={stats.published} valueStyle={{ color: '#10B981' }} />
          </div>
        </Col>
        <Col xs={12} md={4}>
          <div className="geo-card" style={{ padding: 16 }}>
            <Statistic title="失败" value={stats.failed} valueStyle={{ color: '#EF4444' }} />
          </div>
        </Col>
      </Row>

      {/* 筛选 */}
      <div className="geo-card" style={{ marginBottom: 20, padding: '12px 16px' }}>
        <Space wrap>
          <Select
            placeholder="状态筛选"
            style={{ width: 140 }}
            value={filters.status || undefined}
            onChange={(v) => setFilters({ ...filters, status: v || '' })}
            allowClear
          >
            {Object.entries(STATUS_CONFIG).map(([key, config]) => (
              <Select.Option key={key} value={key}>{config.label}</Select.Option>
            ))}
          </Select>
          <Select
            placeholder="平台筛选"
            style={{ width: 160 }}
            value={filters.platform || undefined}
            onChange={(v) => setFilters({ ...filters, platform: v || '' })}
            allowClear
            showSearch
            optionFilterProp="label"
          >
            {PUBLISH_PLATFORMS.map((p: any) => (
              <Select.Option key={p.code} value={p.code} label={p.name}>{p.name}</Select.Option>
            ))}
          </Select>
        </Space>
      </div>

      {/* 状态流转图 */}
      <div className="geo-card" style={{ marginBottom: 20, padding: '12px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 13, color: '#64748B', marginRight: 8 }}>发布流程：</span>
          {STATUS_FLOW.map((status, idx) => (
            <span key={status} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Tag color={STATUS_CONFIG[status].color}>{STATUS_CONFIG[status].label}</Tag>
              {idx < STATUS_FLOW.length - 1 && <span style={{ color: '#CBD5E1' }}>→</span>}
            </span>
          ))}
          <span style={{ color: '#CBD5E1', margin: '0 4px' }}>→</span>
          <Tag color="error">失败（可重试）</Tag>
        </div>
      </div>

      {/* 列表 */}
      <div className="geo-card">
        <Table
          dataSource={list}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }}
          scroll={{ x: 1200 }}
          locale={{ emptyText: '暂无发布记录，点击「新建发布」开始管理文章发布' }}
        />
      </div>

      {/* 新建发布弹窗 */}
      <Modal
        title="新建发布记录"
        open={createModal}
        onCancel={() => { setCreateModal(false); form.resetFields() }}
        onOk={() => form.submit()}
        okText="创建"
        cancelText="取消"
        width={560}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="article_id" label="选择文章" rules={[{ required: true, message: '请选择文章' }]}>
            <Select
              placeholder="请选择要发布的文章"
              showSearch
              optionFilterProp="label"
              options={articles.map((a: any) => ({ value: a.id, label: a.title || `文章#${a.id}` }))}
            />
          </Form.Item>
          <Form.Item name="platform" label="发布平台" rules={[{ required: true, message: '请选择平台' }]}>
            <Select placeholder="请选择发布平台" showSearch optionFilterProp="label">
              {PUBLISH_PLATFORMS.map((p: any) => (
                <Select.Option key={p.code} value={p.code} label={p.name}>
                  <span>{p.name}</span>
                  <span style={{ color: '#999', fontSize: 12, marginLeft: 8 }}>{p.tierLabel}</span>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="status" label="初始状态" initialValue="draft">
            <Select>
              <Select.Option value="draft">草稿</Select.Option>
              <Select.Option value="scheduled">已排期</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="publish_url" label="发布链接（可选）">
            <Input placeholder="已发布的话可粘贴链接" prefix={<LinkOutlined />} />
          </Form.Item>
          <Form.Item name="note" label="备注（可选）">
            <TextArea rows={2} placeholder="备注信息" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 详情抽屉 */}
      <Drawer
        title="发布详情"
        placement="right"
        width={500}
        open={detailDrawer}
        onClose={() => setDetailDrawer(false)}
      >
        {currentRecord && (
          <div>
            <Descriptions title="基本信息" column={1} bordered size="small" style={{ marginBottom: 20 }}>
              <Descriptions.Item label="文章标题">{currentRecord.article_title || '-'}</Descriptions.Item>
              <Descriptions.Item label="关联语义">{currentRecord.semantic_question || '-'}</Descriptions.Item>
              <Descriptions.Item label="发布平台">{PUBLISH_PLATFORM_NAMES[currentRecord.platform] || currentRecord.platform}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={STATUS_CONFIG[currentRecord.status]?.color}>
                  {STATUS_CONFIG[currentRecord.status]?.label}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="发布模式">{currentRecord.publish_mode === 'manual' ? '手动发布' : '自动发布'}</Descriptions.Item>
              <Descriptions.Item label="重试次数">{currentRecord.retry_count}</Descriptions.Item>
              <Descriptions.Item label="创建时间">{currentRecord.created_at ? new Date(currentRecord.created_at).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
              <Descriptions.Item label="排期时间">{currentRecord.scheduled_at ? new Date(currentRecord.scheduled_at).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
              <Descriptions.Item label="发布时间">{currentRecord.published_at ? new Date(currentRecord.published_at).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
              <Descriptions.Item label="发布链接">
                {currentRecord.publish_url ? (
                  <a href={currentRecord.publish_url} target="_blank" rel="noreferrer">{currentRecord.publish_url}</a>
                ) : '-'}
              </Descriptions.Item>
              {currentRecord.failed_reason && (
                <Descriptions.Item label="失败原因"><span style={{ color: '#EF4444' }}>{currentRecord.failed_reason}</span></Descriptions.Item>
              )}
              {currentRecord.note && (
                <Descriptions.Item label="备注">{currentRecord.note}</Descriptions.Item>
              )}
            </Descriptions>

            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>状态流转时间线</div>
              <Timeline
                items={[
                  { color: 'blue', children: `创建记录 - ${currentRecord.created_at ? new Date(currentRecord.created_at).toLocaleString('zh-CN') : '-'}` },
                  currentRecord.scheduled_at && { color: 'blue', children: `排期 - ${new Date(currentRecord.scheduled_at).toLocaleString('zh-CN')}` },
                  currentRecord.published_at && { color: 'green', children: `发布完成 - ${new Date(currentRecord.published_at).toLocaleString('zh-CN')}` },
                  currentRecord.status === 'failed' && { color: 'red', children: `发布失败 - ${currentRecord.failed_reason || '未知原因'}` },
                ].filter(Boolean)}
              />
            </div>

            {currentRecord.status === 'published' && (
              <Button type="primary" block icon={<BarChartOutlined />} onClick={() => { setEffectVisible(true) }} className="btn-primary-gradient">
                查看内容效果追踪
              </Button>
            )}
          </div>
        )}
      </Drawer>

      {/* 效果追踪抽屉（T12组件） */}
      <EffectTracker
        visible={effectVisible}
        onClose={() => setEffectVisible(false)}
        distribution={currentRecord}
        onRefresh={loadList}
      />
    </div>
  )
}

export default Distribution
```

#### 6.3.3 注册路由：`frontend/src/router/index.tsx`

在 lazy 导入区追加：
```typescript
const Distribution = lazy(() => import('@/pages/Distribution'))
```

在路由区追加（放在 content 后面）：
```typescript
<Route path="distribution" element={<RequireAuth><Distribution /></RequireAuth>} />
```

#### 6.3.4 添加菜单：`frontend/src/components/Layout.tsx`

在 `menuItems` 数组中，`内容中心` 后面追加：
```typescript
  { key: '/distribution', icon: <SendOutlined />, label: '发布管理' },
```

同时在图标导入中追加 `SendOutlined`。

### 6.4 验证步骤

1. **后端API验证**：重启后端，访问 `GET /api/v1/distribution`，确认返回 `article_title` 和 `semantic_question` 字段
2. **前端tsc**：`npx tsc --noEmit` exit code 0
3. **功能验证**：
   - 左侧菜单出现"发布管理"入口
   - 访问 `/distribution` 显示统计卡片、筛选、状态流转图、列表
   - 点击"新建发布"可选择文章和平台，创建记录
   - 状态流转正常：草稿→排期→发布中→已发布
   - 失败可重试
   - 已发布记录可点击"效果追踪"（T12功能）

### 6.5 完成标准

- [ ] 后端列表接口返回文章标题和语义问题
- [ ] 前端 tsc exit code 0
- [ ] 发布管理页面可访问，左侧菜单有入口
- [ ] 统计卡片正确显示各状态数量
- [ ] 新建发布弹窗正常，可选择文章和平台
- [ ] 状态流转正常（草稿→排期→发布中→已发布）
- [ ] 失败可重试，草稿可删除
- [ ] 详情抽屉显示完整信息和时间线
- [ ] 已发布记录有"效果追踪"入口

---

## 七、T12：内容效果追踪基础版

### 7.1 任务目标
实现内容效果追踪基础功能：对已发布的文章，手动触发重新采集关联语义，对比发布前后的 GEO 提及率、AEO 引用率、排名变化，用图表展示效果趋势。

### 7.2 后端改动

#### 7.2.1 新增端点：`backend/app/api/distribution.py`

在文件末尾追加2个端点：

```python
@router.get("/{dist_id}/effect", summary="获取发布效果对比（发布前后GEO/AEO/排名变化）")
def get_distribution_effect(
    dist_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    dist = DistributionService.get_or_404(db, dist_id, user_id)
    if dist.status != 'published':
        raise HTTPException(status_code=400, detail="仅已发布的记录可查看效果追踪")

    # 获取关联文章和语义
    article = db.query(ArticleDraft).filter(ArticleDraft.id == dist.article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="关联文章不存在")

    semantic_id = article.semantic_id
    publish_time = dist.published_at or dist.created_at

    # 发布前数据（发布时间之前的采集记录）
    before_records = db.query(MonitorRecord).filter(
        MonitorRecord.semantic_id == semantic_id,
        MonitorRecord.created_at < publish_time
    ).all()

    # 发布后数据（发布时间之后的采集记录）
    after_records = db.query(MonitorRecord).filter(
        MonitorRecord.semantic_id == semantic_id,
        MonitorRecord.created_at >= publish_time
    ).all()

    def calc_stats(records):
        if not records:
            return {"total": 0, "mention_rate": 0, "citation_rate": 0, "avg_rank": None, "mentioned_count": 0}
        total = len(records)
        mentioned = sum(1 for r in records if r.mentioned)
        cited = sum(1 for r in records if r.cite_count and r.cite_count > 0)
        ranks = [r.rank for r in records if r.rank and r.rank > 0]
        avg_rank = sum(ranks) / len(ranks) if ranks else None
        return {
            "total": total,
            "mention_rate": round(mentioned / total * 100, 1),
            "citation_rate": round(cited / total * 100, 1),
            "avg_rank": round(avg_rank, 1) if avg_rank else None,
            "mentioned_count": mentioned,
        }

    before = calc_stats(before_records)
    after = calc_stats(after_records)

    # 变化量
    change = {
        "mention_rate": round(after["mention_rate"] - before["mention_rate"], 1),
        "citation_rate": round(after["citation_rate"] - before["citation_rate"], 1),
        "avg_rank": round((before["avg_rank"] or 0) - (after["avg_rank"] or 0), 1) if before["avg_rank"] and after["avg_rank"] else None,
    }

    # 按日期统计趋势（最近30天）
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.now() - timedelta(days=30)
    trend_records = db.query(MonitorRecord).filter(
        MonitorRecord.semantic_id == semantic_id,
        MonitorRecord.created_at >= thirty_days_ago
    ).all()

    trend = {}
    for r in trend_records:
        date_str = r.created_at.strftime('%Y-%m-%d') if hasattr(r.created_at, 'strftime') else str(r.created_at)[:10]
        if date_str not in trend:
            trend[date_str] = {"total": 0, "mentioned": 0}
        trend[date_str]["total"] += 1
        if r.mentioned:
            trend[date_str]["mentioned"] += 1

    trend_data = sorted([
        {"date": d, "mention_rate": round(v["mentioned"] / v["total"] * 100, 1)}
        for d, v in trend.items()
    ], key=lambda x: x["date"])

    return {
        "code": 0,
        "message": "success",
        "data": {
            "semantic_id": semantic_id,
            "semantic_question": article.title,  # 用文章标题，实际应查semantic
            "publish_time": publish_time.isoformat() if publish_time else None,
            "before": before,
            "after": after,
            "change": change,
            "trend": trend_data,
        }
    }


@router.post("/{dist_id}/recollect", summary="触发重新采集关联语义（用于效果验证）")
def recollect_distribution(
    dist_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    dist = DistributionService.get_or_404(db, dist_id, user_id)
    article = db.query(ArticleDraft).filter(ArticleDraft.id == dist.article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="关联文章不存在")

    # 创建异步采集任务（复用 monitor_collect）
    from app.models.task import AsyncTask
    import json
    task = AsyncTask(
        workspace_id=None,  # TODO: 从workspace_member获取
        task_type="monitor_collect",
        status="queued",
        progress=0,
        progress_message="等待执行",
        payload_json=json.dumps({"question_id": article.semantic_id, "detect_round": 99}),
        created_by=user_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return {"code": 0, "message": "success", "data": {"task_id": task.id, "message": "已加入采集队列，完成后可查看最新效果"}}
```

**注意**：需要导入 MonitorRecord 模型。在文件顶部导入区追加：
```python
from app.models.monitor import MonitorRecord
```

同时，`semantic_question` 应该查语义表而不是用文章标题。修正：
```python
    from app.models.semantic import Semantic
    semantic = db.query(Semantic).filter(Semantic.id == semantic_id).first()
    semantic_question = semantic.question if semantic else ''
```

#### 7.2.2 确认 MonitorRecord 模型字段

需要确认 `app/models/monitor.py` 中有 `semantic_id`、`mentioned`、`rank`、`cite_count`、`created_at` 字段。从之前的数据库检查看，这些字段都存在。

### 7.3 前端改动

#### 7.3.1 新增API方法：`frontend/src/api/index.ts`

在 `distributionApi` 中追加：
```typescript
  getEffect: (id: number) => request.get(`/distribution/${id}/effect`),
  recollect: (id: number) => request.post(`/distribution/${id}/recollect`),
```

#### 7.3.2 新建组件：`frontend/src/components/EffectTracker.tsx`

**完整代码**：

```tsx
import { useState, useEffect } from 'react'
import { Drawer, Button, Spin, Statistic, Row, Col, message, Empty, Tag, Space, Card } from 'antd'
import {
  ArrowUpOutlined, ArrowDownOutlined, MinusOutlined,
  ReloadOutlined, BarChartOutlined, EyeOutlined
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

  const renderChange = (value: number, isRank = false) => {
    if (value === null || value === undefined) return <Tag>无数据</Tag>
    if (value > 0) {
      return <Tag color={isRank ? 'green' : 'green'} icon={<ArrowUpOutlined />}>{isRank ? `上升${value}位` : `+${value}%`}</Tag>
    } else if (value < 0) {
      return <Tag color={isRank ? 'red' : 'red'} icon={<ArrowDownOutlined />}>{isRank ? `下降${Math.abs(value)}位` : `${value}%`}</Tag>
    }
    return <Tag icon={<MinusOutlined />}>无变化</Tag>
  }

  // 趋势图配置
  const getTrendOption = () => {
    if (!effectData?.trend || effectData.trend.length === 0) return null
    return {
      tooltip: { trigger: 'axis' },
      grid: { left: 40, right: 20, top: 30, bottom: 30 },
      xAxis: {
        type: 'category',
        data: effectData.trend.map((d: any) => d.date),
        axisLabel: { fontSize: 11, rotate: 30 },
      },
      yAxis: {
        type: 'value',
        name: '提及率(%)',
        max: 100,
        axisLabel: { fontSize: 11 },
      },
      series: [{
        name: 'GEO提及率',
        type: 'line',
        data: effectData.trend.map((d: any) => d.mention_rate),
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { width: 2, color: '#3B82F6' },
        itemStyle: { color: '#3B82F6' },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(59,130,246,0.3)' }, { offset: 1, color: 'rgba(59,130,246,0.02)' }] } },
        markLine: effectData.publish_time ? {
          symbol: 'none',
          data: [{ xAxis: effectData.publish_time?.slice(0, 10), label: { formatter: '发布时间', fontSize: 11 }, lineStyle: { color: '#10B981', type: 'dashed' } }],
        } : undefined,
      }],
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
      width={640}
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
          <Empty description="暂无效果数据，点击「重新采集验证」开始追踪" />
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
                  <div style={{ marginTop: 4 }}>
                    发布前 {effectData.before?.mention_rate || 0}%
                    {renderChange(effectData.change?.mention_rate)}
                  </div>
                </Col>
                <Col span={8}>
                  <Statistic
                    title="AEO引用率"
                    value={effectData.after?.citation_rate || 0}
                    suffix="%"
                    valueStyle={{ color: '#8B5CF6', fontSize: 24, fontWeight: 700 }}
                  />
                  <div style={{ marginTop: 4 }}>
                    发布前 {effectData.before?.citation_rate || 0}%
                    {renderChange(effectData.change?.citation_rate)}
                  </div>
                </Col>
                <Col span={8}>
                  <Statistic
                    title="平均排名"
                    value={effectData.after?.avg_rank || '-'}
                    suffix={effectData.after?.avg_rank ? '名' : ''}
                    valueStyle={{ color: '#F59E0B', fontSize: 24, fontWeight: 700 }}
                  />
                  <div style={{ marginTop: 4 }}>
                    发布前 {effectData.before?.avg_rank || '-'}
                    {effectData.change?.avg_rank !== null && effectData.change?.avg_rank !== undefined && renderChange(effectData.change.avg_rank, true)}
                  </div>
                </Col>
              </Row>
            </Card>

            {/* 样本量说明 */}
            <div style={{ background: '#F0F9FF', padding: '10px 14px', borderRadius: 8, marginBottom: 16, fontSize: 12, color: '#0369A1' }}>
              💡 数据样本：发布前 {effectData.before?.total || 0} 条采集记录，发布后 {effectData.after?.total || 0} 条采集记录。
              {effectData.after?.total === 0 && ' 发布后暂无采集数据，建议点击「重新采集验证」获取最新数据。'}
            </div>

            {/* 趋势图 */}
            <Card title="📈 最近30天GEO提及率趋势" size="small">
              {effectData.trend && effectData.trend.length > 0 ? (
                <ReactECharts option={getTrendOption()} style={{ height: 280 }} notMerge />
              ) : (
                <Empty description="暂无趋势数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </Card>

            {/* 使用说明 */}
            <div style={{ marginTop: 16, background: '#F8FAFC', padding: 16, borderRadius: 12 }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: '#334155' }}>📋 效果追踪使用说明</div>
              <div style={{ fontSize: 12, color: '#64748B', lineHeight: 1.8 }}>
                1. 文章发布后，系统会对比发布前后的 GEO 提及率、AEO 引用率、排名变化<br />
                2. 点击「重新采集验证」可触发一次新的采集，获取最新数据<br />
                3. 趋势图展示最近30天的提及率变化，绿色虚线为发布时间点<br />
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
```

**注意**：需要确认项目已安装 `echarts-for-react`。如果没有，需要 `npm install echarts echarts-for-react`。从之前的项目结构看，项目已有 ECharts 依赖（Dashboard 用了），但可能用的是原生 echarts 而不是 echarts-for-react。需要确认。

如果项目用的是原生 echarts（`import * as echarts from 'echarts'`），则需要改用 useRef + useEffect 的方式初始化图表，而不是 echarts-for-react。

**备选方案（原生echarts）**：

```tsx
import { useRef, useEffect } from 'react'
import * as echarts from 'echarts'

// 在组件中：
const chartRef = useRef<HTMLDivElement>(null)
const chartInstance = useRef<any>(null)

useEffect(() => {
  if (chartRef.current && effectData?.trend?.length > 0) {
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current)
    }
    chartInstance.current.setOption(getTrendOption())
  }
  return () => {
    chartInstance.current?.dispose()
    chartInstance.current = null
  }
}, [effectData])

// JSX:
<div ref={chartRef} style={{ height: 280 }} />
```

执行时需要先确认项目用的是哪种 ECharts 方式，选择对应的实现。

### 7.4 验证步骤

1. **后端API验证**：
   - `GET /api/v1/distribution/{id}/effect` 返回发布前后对比数据
   - `POST /api/v1/distribution/{id}/recollect` 创建采集任务

2. **前端tsc**：`npx tsc --noEmit` exit code 0

3. **功能验证**：
   - 发布管理页面，已发布记录点击"效果追踪"打开抽屉
   - 显示发布前后 GEO提及率/AEO引用率/排名对比
   - 显示变化量（上升/下降标签）
   - 显示最近30天趋势图
   - 点击"重新采集验证"创建采集任务
   - 采集完成后点击"刷新"查看最新效果

### 7.5 完成标准

- [ ] 后端2个新端点正常工作
- [ ] 前端 tsc exit code 0
- [ ] 效果追踪抽屉可从发布管理页面打开
- [ ] 发布前后对比数据正确显示（GEO/AEO/排名）
- [ ] 变化量标签正确（上升绿色/下降红色）
- [ ] 趋势图正常渲染（如有数据）
- [ ] "重新采集验证"按钮可创建采集任务
- [ ] 空数据状态有友好提示

---

## 八、Session 划分与执行顺序

### Session 1：T10 我的资料重新设计

**执行前检查**：
- 后端服务已停止（避免文件占用）
- 数据库已备份

**执行步骤**：
1. 修改 `backend/app/models/doctor.py`（加6个字段）
2. 修改 `backend/scripts/migrate_v2.py`（追加迁移）
3. 运行迁移脚本，验证幂等
4. 修改 `backend/app/api/doctor.py`（get/save支持新字段）
5. 验证后端 import
6. 完全重写 `frontend/src/pages/Profile.tsx`
7. 前端 tsc 验证
8. 启动后端，功能验证

**完成标准**：见 5.5 节

### Session 2：T11 发布管理 + T12 效果追踪

**执行前检查**：
- T10 已完成并验证
- 确认项目 ECharts 使用方式（原生 or echarts-for-react）

**执行步骤**：
1. 修改 `backend/app/api/distribution.py`（列表返回文章标题+语义，新增2个端点）
2. 验证后端 import
3. 修改 `frontend/src/api/index.ts`（新增 distributionApi）
4. 新建 `frontend/src/pages/Distribution.tsx`
5. 新建 `frontend/src/components/EffectTracker.tsx`
6. 修改 `frontend/src/router/index.tsx`（注册路由）
7. 修改 `frontend/src/components/Layout.tsx`（加菜单）
8. 前端 tsc 验证
9. 启动后端，功能验证

**完成标准**：见 6.5 和 7.5 节

---

## 九、常见问题排查

### Q1：迁移脚本报错 "duplicate column name"
**原因**：列已存在，ensure_column 应该幂等。检查 ensure_column 函数是否正确判断列存在。
**解决**：手动检查数据库列，确认已存在后跳过。

### Q2：前端 tsc 报错 "Cannot find module 'echarts-for-react'"
**原因**：项目用的是原生 echarts，不是 echarts-for-react。
**解决**：改用原生 echarts + useRef 方式初始化图表（见 7.3.2 备选方案）。

### Q3：效果追踪接口返回 400 "仅已发布的记录可查看效果追踪"
**原因**：该发布记录状态不是 published。
**解决**：先将记录标记为已发布，再查看效果。

### Q4：重新采集后任务一直等待中
**原因**：Worker 进程未启动。
**解决**：确认后端启动时 `AUTO_START_WORKER=true`（默认），查看日志是否有 "内嵌 Worker 线程已启动"。

### Q5：资料完整度计算不准确
**原因**：Form.useWatch 可能在表单未初始化时返回 undefined。
**解决**：在 completeness 计算中加空值判断，`formValues || {}`。

---

## 十、完成检查表

### T10 我的资料重新设计
- [ ] 数据库迁移成功，6个新列已添加
- [ ] 后端模型 import 无错误
- [ ] 后端 API 支持新字段读写
- [ ] 前端 Profile.tsx 完全重写
- [ ] 前端 tsc exit code 0
- [ ] 左侧名片显示（头像+姓名+职称+医院+科室）
- [ ] 资料完整度进度条实时计算
- [ ] 专长疾病标签化输入正常
- [ ] 社交媒体链接动态添加/删除正常
- [ ] 4个分组可折叠
- [ ] 保存成功弹出引导卡片

### T11 发布管理
- [ ] 后端列表接口返回文章标题和语义
- [ ] 前端 Distribution.tsx 新建完成
- [ ] 路由注册，左侧菜单有入口
- [ ] 前端 tsc exit code 0
- [ ] 统计卡片正确显示
- [ ] 新建发布弹窗正常
- [ ] 状态流转正常（草稿→排期→发布中→已发布）
- [ ] 失败可重试，草稿可删除
- [ ] 详情抽屉显示完整信息

### T12 效果追踪
- [ ] 后端2个新端点正常工作
- [ ] 前端 EffectTracker.tsx 新建完成
- [ ] 前端 tsc exit code 0
- [ ] 效果追踪抽屉可打开
- [ ] 发布前后对比数据正确
- [ ] 变化量标签正确
- [ ] 趋势图正常渲染
- [ ] 重新采集验证按钮可用

---

## 十一、问题记录区

> 执行过程中遇到的问题和解决方案记录在此

| # | 问题 | 解决方案 | 发现时间 |
|---|---|---|---|
| 1 | （待记录） | | |

---

**手册版本**：v1.0
**创建时间**：2026-09-14
**最后更新**：2026-09-14
