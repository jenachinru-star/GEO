1	# GEO 项目 P1.5 执行手册：我的资料重设计 + 发布管理 + 效果追踪
2	
3	> **版本**：v1.0
4	> **创建时间**：2026-09-14
5	> **适用范围**：T10-T12（我的资料重新设计、发布管理前端、内容效果追踪基础版）
6	> **前置条件**：P0（T01-T06）+ P1（T07-T09）已全部完成并验证通过
7	> **执行方式**：分 2 个 Session 串行执行
8	
9	---
10	
11	## 一、项目状态快照
12	
13	### 已完成
14	- P0（T01-T06）：Workspace/AsyncTask/Worker框架、Distribution状态机、分析器bug修复、采集异步化、任务查询API+前端任务中心、P0联调验收
15	- P1（T07-T09）：内容机会识别模块、文章生成引擎升级（LLM驱动）、生图适配器框架（配置留空）
16	- P1.5 前置：语义延伸功能（semantic_extender引擎+API+前端抽屉）、语义问题统一问号、Dashboard删"最高"、ContentHub重构为3个Tab（智能创作/创作工具/内容机会）
17	
18	### 技术栈
19	- 后端：FastAPI + SQLAlchemy + SQLite + Python 3.11
20	- 前端：React 18 + TypeScript + Vite + AntD 5 + ECharts + Zustand
21	- 数据库：`backend/data/geo.db`（已备份 `geo.db.backup_before_upgrade`）
22	- Python环境：`C:\Users\jenac\AppData\Local\Programs\Python\Python311\python.exe`
23	
24	### 本轮目标
25	打通"资料完善 → 内容生成 → 发布管理 → 效果追踪"的完整GEO优化闭环。
26	
27	---
28	
29	## 二、决策点记录
30	
31	| # | 决策点 | 结论 |
32	|---|---|---|
33	| 1 | 我的资料设计范围 | 一期做：基本信息+个人品牌+资料完整度进度条+保存成功引导；二期做：执业经历/教育背景等复杂字段 |
34	| 2 | 头像上传 | 一期用URL输入，不做文件上传（需要后端存储接口，成本高） |
35	| 3 | AI识别效果预览 | 一期不做，加"去采集看效果"按钮跳数据中心（功能重叠） |
36	| 4 | 发布管理放置位置 | 独立页面 `/distribution`，左侧菜单加入口（Tab空间不够） |
37	| 5 | 发布方式 | 一期做"手动标记已发布"，不做实际API调用各平台（各平台API差异大） |
38	| 6 | 效果追踪 | 基础版：手动触发重新采集，对比发布前后GEO/AEO/排名变化 |
39	| 7 | 社交媒体链接存储 | 用JSON字段（简单，一期够用），二期规范化拆表 |
40	| 8 | Session划分 | 分2个Session：Session1=T10（资料重设计），Session2=T11+T12（发布管理+效果追踪） |
41	
42	---
43	
44	## 三、全局约定
45	
46	### 命名规范
47	- 后端模型字段：snake_case
48	- 前端变量/函数：camelCase
49	- 新文件：功能清晰的英文命名
50	
51	### 数据库迁移
52	- 所有表结构变更必须通过 `scripts/migrate_v2.py` 幂等迁移脚本
53	- 只加列/加表，不删列/不改列类型（安全第一）
54	- 迁移后必须验证二次运行无重复输出
55	
56	### 验证要求
57	- 后端：所有模块 `import` 无错误
58	- 前端：`npx tsc --noEmit` exit code 0
59	- 每个任务完成后必须按"完成标准"逐项验证
60	
61	### 运行命令
62	```bash
63	# 后端启动（带内嵌Worker）
64	cd C:\Users\jenac\Desktop\GEO\backend
65	C:\Users\jenac\AppData\Local\Programs\Python\Python311\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
66	
67	# 前端类型检查
68	cd C:\Users\jenac\Desktop\GEO\frontend
69	npx tsc --noEmit
70	
71	# 运行迁移
72	cd C:\Users\jenac\Desktop\GEO\backend
73	C:\Users\jenac\AppData\Local\Programs\Python\Python311\python.exe -m scripts.migrate_v2
74	```
75	
76	---
77	
78	## 四、Session 划分
79	
80	| Session | 任务 | 内容 | 预计工作量 |
81	|---|---|---|---|
82	| Session 1 | T10 | 我的资料重新设计（一期） | 后端加字段+迁移+API，前端完全重写Profile |
83	| Session 2 | T11+T12 | 发布管理前端 + 内容效果追踪 | 后端加2个端点，前端新建Distribution页面+EffectTracker组件 |
84	
85	---
86	
87	## 五、T10：我的资料重新设计（一期）
88	
89	### 5.1 任务目标
90	将"我的资料"页面从简单表单重构为"左侧名片+右侧分组表单"的专业医生资料管理页面，新增个人品牌字段（个人简介、社交媒体链接、个人网站、挂号链接），增加资料完整度进度条和保存成功引导。
91	
92	### 5.2 后端改动
93	
94	#### 5.2.1 修改模型：`backend/app/models/doctor.py`
95	
96	**修改点**：新增 6 个字段
97	
98	```python
99	# 在现有字段后追加：
100	    avatar_url = Column(String(500), default="")  # 头像URL（一期用URL，二期做上传）
101	    bio = Column(Text, default="")  # 个人简介
102	    social_links = Column(Text, default="[]")  # 社交媒体链接（JSON数组：[{"platform":"zhihu","url":"..."}]）
103	    personal_website = Column(String(500), default="")  # 个人网站
104	    registration_url = Column(String(500), default="")  # 挂号链接
105	    clinic_hours = Column(Text, default="[]")  # 出诊时间（JSON数组：[{"day":"周一","time":"上午"}]）
106	```
107	
108	**完整文件代码**：
109	
110	```python
111	from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
112	from sqlalchemy.sql import func
113	from app.database import Base
114	
115	
116	class DoctorProfile(Base):
117	    """医生个人资料（GEO基础数据）"""
118	    __tablename__ = "geo_doctor_profile"
119	
120	    id = Column(Integer, primary_key=True, index=True)
121	    user_id = Column(Integer, ForeignKey("geo_user.id"), unique=True, nullable=False, index=True)
122	    real_name = Column(String(100), nullable=False, default="")
123	    title = Column(String(100), default="")
124	    province = Column(String(50), default="")
125	    city = Column(String(50), default="")
126	    hospital = Column(String(200), default="")
127	    department = Column(String(100), default="")
128	    specialty = Column(String(500), default="")  # 逗号分隔
129	    awards = Column(Text, default="")
130	    case_history = Column(Text, default="")
131	    self_intro_template = Column(String(500), default="")
132	    # ===== V2.1 个人品牌新增字段 =====
133	    avatar_url = Column(String(500), default="")
134	    bio = Column(Text, default="")
135	    social_links = Column(Text, default="[]")
136	    personal_website = Column(String(500), default="")
137	    registration_url = Column(String(500), default="")
138	    clinic_hours = Column(Text, default="[]")
139	    created_at = Column(DateTime(timezone=True), server_default=func.now())
140	    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
141	```
142	
143	#### 5.2.2 修改迁移脚本：`backend/scripts/migrate_v2.py`
144	
145	**修改点**：在 `migrate()` 函数末尾追加医生资料新列迁移，新增迁移版本记录。
146	
147	在 `record_migration(conn, "v2.1_semantic_extend")` 后追加：
148	
149	```python
150	    # ===== 7. 医生资料个人品牌字段 =====
151	    print("[7/7] 医生资料个人品牌字段")
152	    ensure_column(conn, "geo_doctor_profile", "avatar_url", "TEXT DEFAULT ''")
153	    ensure_column(conn, "geo_doctor_profile", "bio", "TEXT DEFAULT ''")
154	    ensure_column(conn, "geo_doctor_profile", "social_links", "TEXT DEFAULT '[]'")
155	    ensure_column(conn, "geo_doctor_profile", "personal_website", "TEXT DEFAULT ''")
156	    ensure_column(conn, "geo_doctor_profile", "registration_url", "TEXT DEFAULT ''")
157	    ensure_column(conn, "geo_doctor_profile", "clinic_hours", "TEXT DEFAULT '[]'")
158	
159	    record_migration(conn, "v2.2_doctor_brand")
160	```
161	
162	同时把前面的 `[6/6]` 改成 `[6/7]`，`[5/6]` 改成 `[5/7]`（保持序号连续）。
163	
164	#### 5.2.3 修改API：`backend/app/api/doctor.py`
165	
166	**修改点1**：`get_profile` 返回新字段
167	
168	在 `data` 字典中追加：
169	```python
170	        "avatar_url": profile.avatar_url,
171	        "bio": profile.bio,
172	        "social_links": profile.social_links,
173	        "personal_website": profile.personal_website,
174	        "registration_url": profile.registration_url,
175	        "clinic_hours": profile.clinic_hours,
176	```
177	
178	**修改点2**：`save_profile` 的 `allowed_fields` 追加新字段
179	
180	```python
181	    allowed_fields = ["real_name", "title", "province", "city", "hospital",
182	                      "department", "specialty", "awards", "case_history",
183	                      "avatar_url", "bio", "social_links", "personal_website",
184	                      "registration_url", "clinic_hours"]
185	```
186	
187	**修改点3**：`save_profile` 返回的 profile 数据追加新字段（可选，前端用不到全部，但保持一致性）
188	
189	在返回的 `profile` 字典中追加：
190	```python
191	                "avatar_url": profile.avatar_url,
192	                "bio": profile.bio,
193	                "hospital": profile.hospital,
194	                "department": profile.department,
195	                "specialty": profile.specialty,
196	```
197	
198	### 5.3 前端改动
199	
200	#### 5.3.1 完全重写：`frontend/src/pages/Profile.tsx`
201	
202	**设计要点**：
203	- 左侧：医生名片（头像+姓名+职称+医院+科室）+ 资料完整度进度条 + 快捷操作
204	- 右侧：分组表单（基本信息/个人品牌/执业信息/学术成果），可折叠
205	- 专长疾病标签化输入
206	- 社交媒体链接动态添加
207	- 保存成功后不跳转，显示引导卡片
208	
209	**完整代码**：
210	
211	```tsx
212	import { useState, useEffect, useMemo } from 'react'
213	import {
214	  Form, Input, Select, Button, message, Spin, Space, Collapse,
215	  Tag, Tooltip, Divider, Card, Progress, Modal
216	} from 'antd'
217	import {
218	  CheckCircleOutlined, WarningOutlined, ExclamationCircleOutlined,
219	  PlusOutlined, DeleteOutlined, GlobalOutlined, LinkOutlined,
220	  ClockCircleOutlined, SaveOutlined, DownloadOutlined, EyeOutlined,
221	  UserOutlined
222	} from '@ant-design/icons'
223	import { useNavigate } from 'react-router-dom'
224	import { doctorApi, entityApi } from '@/api'
225	import { useAppStore } from '@/store/useStore'
226	
227	const { TextArea } = Input
228	
229	const TITLE_OPTIONS = ['主任医师', '副主任医师', '主治医师', '住院医师', '其他']
230	
231	const SOCIAL_PLATFORMS = [
232	  { value: 'zhihu', label: '知乎', color: '#0084FF' },
233	  { value: 'wechat', label: '公众号', color: '#07C160' },
234	  { value: 'xiaohongshu', label: '小红书', color: '#FF2442' },
235	  { value: 'weibo', label: '微博', color: '#E6162D' },
236	  { value: 'douyin', label: '抖音', color: '#000000' },
237	  { value: 'bilibili', label: 'B站', color: '#FB7299' },
238	  { value: 'haodf', label: '好大夫', color: '#1890FF' },
239	  { value: 'other', label: '其他', color: '#999' },
240	]
241	
242	const CLINIC_DAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
243	const CLINIC_TIMES = ['上午', '下午', '晚上', '全天']
244	
245	// 资料完整度检查项
246	const COMPLETENESS_CHECKS = [
247	  { key: 'real_name', label: '真实姓名', weight: 10 },
248	  { key: 'hospital', label: '医院全称', weight: 15 },
249	  { key: 'department', label: '科室', weight: 10 },
250	  { key: 'city', label: '城市', weight: 5 },
251	  { key: 'specialty', label: '专长疾病', weight: 15 },
252	  { key: 'title', label: '职称', weight: 5 },
253	  { key: 'bio', label: '个人简介', weight: 10 },
254	  { key: 'social_links', label: '社交媒体', weight: 10 },
255	  { key: 'avatar_url', label: '头像', weight: 5 },
256	  { key: 'personal_website', label: '个人网站', weight: 5 },
257	  { key: 'registration_url', label: '挂号链接', weight: 5 },
258	]
259	
260	const Profile = () => {
261	  const [form] = Form.useForm()
262	  const [loading, setLoading] = useState(false)
263	  const [saving, setSaving] = useState(false)
264	  const [entityScore, setEntityScore] = useState<any>(null)
265	  const [showSuccess, setShowSuccess] = useState(false)
266	  const [specialtyTags, setSpecialtyTags] = useState<string[]>([])
267	  const [socialLinks, setSocialLinks] = useState<Array<{ platform: string; url: string }>>([])
268	  const [clinicHours, setClinicHours] = useState<Array<{ day: string; time: string }>>([])
269	  const navigate = useNavigate()
270	  const { setDoctorProfile } = useAppStore()
271	
272	  // 监听表单变化，实时计算完整度
273	  const formValues = Form.useWatch((values: any) => values, form)
274	
275	  const completeness = useMemo(() => {
276	    if (!formValues) return { score: 0, missing: [] }
277	    let score = 0
278	    const missing: string[] = []
279	    for (const check of COMPLETENESS_CHECKS) {
280	      const val = formValues[check.key]
281	      const hasValue = val && (Array.isArray(val) ? val.length > 0 : String(val).trim() !== '')
282	      if (hasValue) {
283	        score += check.weight
284	      } else {
285	        missing.push(check.label)
286	      }
287	    }
288	    return { score, missing }
289	  }, [formValues])
290	
291	  useEffect(() => {
292	    loadProfile()
293	    loadEntityScore()
294	  }, [])
295	
296	  const loadEntityScore = async () => {
297	    try {
298	      const res: any = await entityApi.getProfileScore()
299	      setEntityScore(res.data)
300	    } catch (e) {}
301	  }
302	
303	  const loadProfile = async () => {
304	    setLoading(true)
305	    try {
306	      const res: any = await doctorApi.getProfile()
307	      if (res.data) {
308	        form.setFieldsValue(res.data)
309	        setDoctorProfile(res.data)
310	        // 解析专长标签
311	        if (res.data.specialty) {
312	          setSpecialtyTags(res.data.specialty.split(',').map((s: string) => s.trim()).filter(Boolean))
313	        }
314	        // 解析社交媒体链接
315	        try {
316	          if (res.data.social_links) {
317	            setSocialLinks(JSON.parse(res.data.social_links))
318	          }
319	        } catch (e) { setSocialLinks([]) }
320	        // 解析出诊时间
321	        try {
322	          if (res.data.clinic_hours) {
323	            setClinicHours(JSON.parse(res.data.clinic_hours))
324	          }
325	        } catch (e) { setClinicHours([]) }
326	      }
327	    } catch (e) {
328	      // 未创建Profile时返回null，正常
329	    } finally {
330	      setLoading(false)
331	    }
332	  }
333	
334	  const handleSave = async (values: any) => {
335	    setSaving(true)
336	    try {
337	      // 组装专长（标签转逗号分隔）
338	      values.specialty = specialtyTags.join(',')
339	      // 组装社交媒体链接
340	      values.social_links = JSON.stringify(socialLinks)
341	      // 组装出诊时间
342	      values.clinic_hours = JSON.stringify(clinicHours)
343	
344	      const res: any = await doctorApi.saveProfile(values)
345	      message.success(`保存成功，已自动生成 ${res.data?.semantic_generated || 0} 个语义问题`)
346	      setDoctorProfile(res.data?.profile)
347	      setShowSuccess(true)
348	    } catch (e) {
349	      // 拦截器已提示
350	    } finally {
351	      setSaving(false)
352	    }
353	  }
354	
355	  const handleDownloadLlms = () => {
356	    const token = localStorage.getItem('geo_token')
357	    fetch('/api/v1/template/llms.txt', {
358	      headers: { 'Authorization': `Bearer ${token}` }
359	    }).then(r => {
360	      if (!r.ok) throw new Error('下载失败')
361	      return r.text()
362	    }).then(text => {
363	      const blob = new Blob([text], { type: 'text/plain' })
364	      const url = URL.createObjectURL(blob)
365	      const a = document.createElement('a')
366	      a.href = url
367	      a.download = 'llms.txt'
368	      a.click()
369	      URL.revokeObjectURL(url)
370	      message.success('llms.txt 已下载，可部署到个人网站根目录帮助AI爬虫识别')
371	    }).catch(() => {
372	      message.error('下载失败，请先完善医生资料')
373	    })
374	  }
375	
376	  // 专长标签处理
377	  const handleSpecialtyInputConfirm = (inputValue: string) => {
378	    const trimmed = inputValue.trim()
379	    if (trimmed && !specialtyTags.includes(trimmed)) {
380	      setSpecialtyTags([...specialtyTags, trimmed])
381	    }
382	  }
383	
384	  const handleSpecialtyTagRemove = (tag: string) => {
385	    setSpecialtyTags(specialtyTags.filter(t => t !== tag))
386	  }
387	
388	  // 社交媒体链接处理
389	  const addSocialLink = () => {
390	    setSocialLinks([...socialLinks, { platform: 'zhihu', url: '' }])
391	  }
392	
393	  const updateSocialLink = (index: number, field: string, value: string) => {
394	    const updated = [...socialLinks]
395	    updated[index] = { ...updated[index], [field]: value }
396	    setSocialLinks(updated)
397	  }
398	
399	  const removeSocialLink = (index: number) => {
400	    setSocialLinks(socialLinks.filter((_, i) => i !== index))
401	  }
402	
403	  // 出诊时间处理
404	  const addClinicHour = () => {
405	    setClinicHours([...clinicHours, { day: '周一', time: '上午' }])
406	  }
407	
408	  const updateClinicHour = (index: number, field: string, value: string) => {
409	    const updated = [...clinicHours]
410	    updated[index] = { ...updated[index], [field]: value }
411	    setClinicHours(updated)
412	  }
413	
414	  const removeClinicHour = (index: number) => {
415	    setClinicHours(clinicHours.filter((_, i) => i !== index))
416	  }
417	
418	  const scoreGradient = entityScore?.score >= 80
419	    ? 'var(--success-gradient)'
420	    : entityScore?.score >= 60
421	      ? 'var(--warning-gradient)'
422	      : 'var(--danger-gradient)'
423	
424	  const collapseItems = [
425	    {
426	      key: 'basic',
427	      label: <span><span style={{ fontWeight: 600 }}>📋 基本信息</span> <span style={{ color: '#999', fontSize: 12, marginLeft: 8 }}>GEO核心，必填</span></span>,
428	      children: (
429	        <Space direction="vertical" style={{ width: '100%' }} size="large">
430	          <div style={{ display: 'flex', gap: 16 }}>
431	            <Form.Item name="real_name" label="真实姓名" rules={[{ required: true, message: '请输入真实姓名' }]} style={{ flex: 1 }}>
432	              <Input placeholder="如：张医生" />
433	            </Form.Item>
434	            <Form.Item name="title" label="职称" style={{ flex: 1 }}>
435	              <Select options={TITLE_OPTIONS.map(t => ({ label: t, value: t }))} />
436	            </Form.Item>
437	          </div>
438	          <div style={{ display: 'flex', gap: 16 }}>
439	            <Form.Item name="province" label="省份" style={{ flex: 1 }}>
440	              <Input placeholder="如：广东省" />
441	            </Form.Item>
442	            <Form.Item name="city" label="城市" rules={[{ required: true, message: '请输入城市' }]} style={{ flex: 1 }}>
443	              <Input placeholder="如：深圳市" />
444	            </Form.Item>
445	          </div>
446	          <Form.Item
447	            name="hospital"
448	            label="医院全称"
449	            rules={[{ required: true, message: '请输入医院全称' }]}
450	            extra={<span style={{ color: '#F59E0B' }}>请填写完整全称，不要用简称。AI会因为信息不一致而降权。</span>}
451	          >
452	            <Input placeholder="如：深圳市第一人民医院" />
453	          </Form.Item>
454	          <Form.Item name="department" label="科室" rules={[{ required: true, message: '请输入科室' }]}>
455	            <Input placeholder="如：妇科" />
456	          </Form.Item>
457	          <Form.Item
458	            label="专长疾病"
459	            extra="输入后回车添加标签，多个专长用标签管理，自动用于语义延伸和内容生成"
460	          >
461	            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
462	              {specialtyTags.map(tag => (
463	                <Tag
464	                  key={tag}
465	                  closable
466	                  onClose={() => handleSpecialtyTagRemove(tag)}
467	                  color="blue"
468	                  style={{ fontSize: 13, padding: '2px 8px' }}
469	                >
470	                  {tag}
471	                </Tag>
472	              ))}
473	              <Input
474	                placeholder="输入专长后回车添加，如：妇科炎症"
475	                size="small"
476	                style={{ width: 200 }}
477	                onPressEnter={(e) => {
478	                  handleSpecialtyInputConfirm((e.target as HTMLInputElement).value)
479	                  ;(e.target as HTMLInputElement).value = ''
480	                }}
481	              />
482	            </div>
483	          </Form.Item>
484	        </Space>
485	      ),
486	    },
487	    {
488	      key: 'brand',
489	      label: <span><span style={{ fontWeight: 600 }}>✍️ 个人品牌</span> <span style={{ color: '#999', fontSize: 12, marginLeft: 8 }}>AEO核心，提升引用率</span></span>,
490	      children: (
491	        <Space direction="vertical" style={{ width: '100%' }} size="large">
492	          <Form.Item name="avatar_url" label="头像URL">
493	            <Input placeholder="如：https://example.com/avatar.jpg（二期支持本地上传）" />
494	          </Form.Item>
495	          <Form.Item name="bio" label="个人简介">
496	            <TextArea rows={4} placeholder="200-500字，介绍您的执业经历、专业擅长、诊疗理念等。AI会引用这段内容。" showCount maxLength={500} />
497	          </Form.Item>
498	          <div>
499	            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
500	              <span style={{ fontSize: 14, fontWeight: 500 }}>社交媒体链接</span>
501	              <Button type="dashed" size="small" icon={<PlusOutlined />} onClick={addSocialLink}>添加链接</Button>
502	            </div>
503	            {socialLinks.length === 0 && (
504	              <div style={{ color: '#999', fontSize: 12, padding: '8px 0' }}>暂无社交媒体链接，点击"添加链接"添加知乎/公众号/小红书等</div>
505	            )}
506	            {socialLinks.map((link, index) => (
507	              <div key={index} style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
508	                <Select
509	                  value={link.platform}
510	                  onChange={(v) => updateSocialLink(index, 'platform', v)}
511	                  style={{ width: 120 }}
512	                >
513	                  {SOCIAL_PLATFORMS.map(p => (
514	                    <Select.Option key={p.value} value={p.value}>{p.label}</Select.Option>
515	                  ))}
516	                </Select>
517	                <Input
518	                  value={link.url}
519	                  onChange={(e) => updateSocialLink(index, 'url', e.target.value)}
520	                  placeholder="粘贴链接URL"
521	                  style={{ flex: 1 }}
522	                />
523	                <Button type="text" danger icon={<DeleteOutlined />} onClick={() => removeSocialLink(index)} />
524	              </div>
525	            ))}
526	          </div>
527	          <div style={{ display: 'flex', gap: 16 }}>
528	            <Form.Item name="personal_website" label="个人网站" style={{ flex: 1 }}>
529	              <Input placeholder="如：https://drzhang.com" prefix={<GlobalOutlined />} />
530	            </Form.Item>
531	            <Form.Item name="registration_url" label="挂号链接" style={{ flex: 1 }}>
532	              <Input placeholder="如：好大夫/微医挂号页URL" prefix={<LinkOutlined />} />
533	            </Form.Item>
534	          </div>
535	        </Space>
536	      ),
537	    },
538	    {
539	      key: 'practice',
540	      label: <span><span style={{ fontWeight: 600 }}>🏥 执业信息</span> <span style={{ color: '#999', fontSize: 12, marginLeft: 8 }}>可选，提升专业可信度</span></span>,
541	      children: (
542	        <Space direction="vertical" style={{ width: '100%' }} size="large">
543	          <div>
544	            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
545	              <span style={{ fontSize: 14, fontWeight: 500 }}>出诊时间</span>
546	              <Button type="dashed" size="small" icon={<PlusOutlined />} onClick={addClinicHour}>添加出诊</Button>
547	            </div>
548	            {clinicHours.length === 0 && (
549	              <div style={{ color: '#999', fontSize: 12, padding: '8px 0' }}>暂无出诊时间</div>
550	            )}
551	            {clinicHours.map((item, index) => (
552	              <div key={index} style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
553	                <Select
554	                  value={item.day}
555	                  onChange={(v) => updateClinicHour(index, 'day', v)}
556	                  style={{ width: 100 }}
557	                >
558	                  {CLINIC_DAYS.map(d => <Select.Option key={d} value={d}>{d}</Select.Option>)}
559	                </Select>
560	                <Select
561	                  value={item.time}
562	                  onChange={(v) => updateClinicHour(index, 'time', v)}
563	                  style={{ width: 100 }}
564	                >
565	                  {CLINIC_TIMES.map(t => <Select.Option key={t} value={t}>{t}</Select.Option>)}
566	                </Select>
567	                <Button type="text" danger icon={<DeleteOutlined />} onClick={() => removeClinicHour(index)} />
568	              </div>
569	            ))}
570	          </div>
571	          <Form.Item name="case_history" label="治病履历/数据统计">
572	            <TextArea rows={2} placeholder="如：从业15年，累计接诊妇科炎症患者5000+例" />
573	          </Form.Item>
574	        </Space>
575	      ),
576	    },
577	    {
578	      key: 'academic',
579	      label: <span><span style={{ fontWeight: 600 }}>🏆 学术成果</span> <span style={{ color: '#999', fontSize: 12, marginLeft: 8 }}>可选，二期细化为动态添加</span></span>,
580	      children: (
581	        <Space direction="vertical" style={{ width: '100%' }} size="large">
582	          <Form.Item name="awards" label="获奖履历">
583	            <TextArea rows={2} placeholder="如：2023年深圳市优秀医师" />
584	          </Form.Item>
585	          <div style={{ background: '#F8FAFC', padding: '10px 14px', borderRadius: 8, fontSize: 12, color: '#64748B' }}>
586	            💡 论文、课题等复杂字段将在二期支持动态添加多条记录
587	          </div>
588	        </Space>
589	      ),
590	    },
591	  ]
592	
593	  return (
594	    <div>
595	      <div className="page-title-bar">
596	        <div>
597	          <h2>我的资料</h2>
598	          <div className="page-desc">完善医生资料是 GEO 优化的基础，资料越完整，AI 识别越准确</div>
599	        </div>
600	      </div>
601	
602	      <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start' }}>
603	        {/* 左侧：医生名片 + 完整度 + 快捷操作 */}
604	        <div style={{ width: 280, flexShrink: 0 }}>
605	          {/* 医生名片 */}
606	          <div className="geo-card" style={{ marginBottom: 16, padding: 20, textAlign: 'center' }}>
607	            <div style={{
608	              width: 80, height: 80, borderRadius: '50%', margin: '0 auto 12px',
609	              background: 'var(--primary-gradient)', display: 'flex', alignItems: 'center', justifyContent: 'center',
610	              fontSize: 32, color: '#fff', overflow: 'hidden'
611	            }}>
612	              {formValues?.avatar_url ? (
613	                <img src={formValues.avatar_url} alt="avatar" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
614	              ) : (
615	                <UserOutlined />
616	              )}
617	            </div>
618	            <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>
619	              {formValues?.real_name || '未填写姓名'}
620	            </div>
621	            <div style={{ fontSize: 13, color: '#64748B', marginBottom: 4 }}>
622	              {formValues?.title || '未填写职称'}
623	            </div>
624	            <div style={{ fontSize: 13, color: '#64748B', marginBottom: 2 }}>
625	              {formValues?.hospital || '未填写医院'}
626	            </div>
627	            <div style={{ fontSize: 13, color: '#64748B' }}>
628	              {formValues?.department || '未填写科室'}
629	            </div>
630	          </div>
631	
632	          {/* 资料完整度 */}
633	          <div className="geo-card" style={{ marginBottom: 16, padding: 20 }}>
634	            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>📊 资料完整度</div>
635	            <Progress
636	              type="circle"
637	              percent={completeness.score}
638	              size={120}
639	              strokeColor={{
640	                '0%': '#10B981',
641	                '100%': '#3B82F6',
642	              }}
643	              format={(percent) => `${percent}%`}
644	              style={{ margin: '0 auto 12px', display: 'block' }}
645	            />
646	            {completeness.missing.length > 0 ? (
647	              <div>
648	                <div style={{ fontSize: 12, color: '#F59E0B', marginBottom: 6, fontWeight: 500 }}>
649	                  还差 {completeness.missing.length} 项可到100%：
650	                </div>
651	                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
652	                  {completeness.missing.map(item => (
653	                    <Tag key={item} color="orange" style={{ fontSize: 11 }}>{item}</Tag>
654	                  ))}
655	                </div>
656	              </div>
657	            ) : (
658	              <div style={{ textAlign: 'center', color: '#10B981', fontSize: 13 }}>
659	                <CheckCircleOutlined /> 资料已完善
660	              </div>
661	            )}
662	          </div>
663	
664	          {/* 实体一致性评分 */}
665	          {entityScore && (
666	            <div className="stat-card-gradient" style={{ background: scoreGradient, marginBottom: 16, padding: 16 }}>
667	              <div style={{ textAlign: 'center', marginBottom: 8 }}>
668	                <div style={{ fontSize: 28, fontWeight: 700 }}>{entityScore.score}</div>
669	                <div style={{ fontSize: 11, opacity: 0.9 }}>实体一致性评分</div>
670	              </div>
671	              <div style={{ fontSize: 12, opacity: 0.95 }}>
672	                {entityScore.passed ? (
673	                  <span><CheckCircleOutlined /> 实体信息完整，AI识别无歧义</span>
674	                ) : (
675	                  <span><WarningOutlined /> 存在 {entityScore.issues.filter((i:any)=>i.level!=='info').length} 个需优化问题</span>
676	                )}
677	              </div>
678	            </div>
679	          )}
680	
681	          {/* 快捷操作 */}
682	          <div className="geo-card" style={{ padding: 16 }}>
683	            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>🎯 快捷操作</div>
684	            <Space direction="vertical" style={{ width: '100%' }}>
685	              <Button block icon={<EyeOutlined />} onClick={() => navigate('/data')}>
686	                去采集看AI效果
687	              </Button>
688	              <Button block icon={<DownloadOutlined />} onClick={handleDownloadLlms}>
689	                下载 llms.txt
690	              </Button>
691	              <Button block icon={<PlusOutlined />} onClick={() => navigate('/semantic')}>
692	                管理语义问题
693	              </Button>
694	            </Space>
695	          </div>
696	        </div>
697	
698	        {/* 右侧：分组表单 */}
699	        <div style={{ flex: 1, minWidth: 0 }}>
700	          <div className="geo-card">
701	            <Spin spinning={loading}>
702	              <Form
703	                form={form}
704	                layout="vertical"
705	                onFinish={handleSave}
706	                initialValues={{ title: '主治医师' }}
707	              >
708	                <Collapse
709	                  defaultActiveKey={['basic', 'brand']}
710	                  items={collapseItems}
711	                  style={{ background: 'transparent', border: 'none' }}
712	                />
713	
714	                <Divider style={{ margin: '16px 0' }} />
715	
716	                <Form.Item>
717	                  <Space>
718	                    <Button type="primary" htmlType="submit" loading={saving} icon={<SaveOutlined />} className="btn-primary-gradient" size="large">
719	                      保存资料
720	                    </Button>
721	                    <Button size="large" onClick={() => message.info('已保存，可继续完善其他信息')}>
722	                      保存并继续编辑
723	                    </Button>
724	                  </Space>
725	                </Form.Item>
726	              </Form>
727	            </Spin>
728	          </div>
729	        </div>
730	      </div>
731	
732	      {/* 保存成功引导弹窗 */}
733	      <Modal
734	        open={showSuccess}
735	        onCancel={() => setShowSuccess(false)}
736	        footer={null}
737	        width={500}
738	      >
739	        <div style={{ textAlign: 'center', padding: '20px 0' }}>
740	          <div style={{ fontSize: 48, color: '#10B981', marginBottom: 16 }}>
741	            <CheckCircleOutlined />
742	          </div>
743	          <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>资料保存成功！</div>
744	          <div style={{ fontSize: 14, color: '#64748B', marginBottom: 24 }}>
745	            医生资料已更新，系统已自动生成相关语义问题
746	          </div>
747	          <div style={{ background: '#F0F9FF', padding: 16, borderRadius: 12, textAlign: 'left', marginBottom: 20 }}>
748	            <div style={{ fontSize: 13, fontWeight: 600, color: '#0369A1', marginBottom: 8 }}>📋 下一步建议</div>
749	            <div style={{ fontSize: 12, color: '#0369A1', lineHeight: 1.8 }}>
750	              1. 去「语义库」查看和管理生成的语义问题<br />
751	              2. 去「数据中心」跑采集，查看 AI 搜索效果<br />
752	              3. 去「内容中心」基于内容机会生成文章
753	            </div>
754	          </div>
755	          <Space>
756	            <Button type="primary" onClick={() => { setShowSuccess(false); navigate('/semantic') }} className="btn-primary-gradient">
757	              去语义库
758	            </Button>
759	            <Button onClick={() => { setShowSuccess(false); navigate('/data') }}>
760	              去采集
761	            </Button>
762	            <Button onClick={() => setShowSuccess(false)}>
763	              继续编辑
764	            </Button>
765	          </Space>
766	        </div>
767	      </Modal>
768	    </div>
769	  )
770	}
771	
772	export default Profile
773	```
774	
775	### 5.4 验证步骤
776	
777	1. **运行迁移**：
778	   ```bash
779	   cd C:\Users\jenac\Desktop\GEO\backend
780	   C:\Users\jenac\AppData\Local\Programs\Python\Python311\python.exe -m scripts.migrate_v2
781	   ```
782	   预期输出：`[7/7] 医生资料个人品牌字段` + 6个 `+ 列` + `+ 迁移记录 v2.2_doctor_brand`
783	
784	2. **验证模型import**：
785	   ```bash
786	   C:\Users\jenac\AppData\Local\Programs\Python\Python311\python.exe -c "from app.models.doctor import DoctorProfile; print([c.name for c in DoctorProfile.__table__.columns])"
787	   ```
788	   预期：包含 `avatar_url, bio, social_links, personal_website, registration_url, clinic_hours`
789	
790	3. **验证前端tsc**：
791	   ```bash
792	   cd C:\Users\jenac\Desktop\GEO\frontend
793	   npx tsc --noEmit
794	   ```
795	   预期：exit code 0
796	
797	4. **功能验证**：
798	   - 重启后端，访问 `/profile` 页面
799	   - 左侧显示医生名片（头像+姓名+职称+医院+科室）
800	   - 资料完整度进度条实时计算，显示缺失项
801	   - 右侧4个可折叠分组（基本信息/个人品牌/执业信息/学术成果）
802	   - 专长疾病标签化输入（回车添加，可删除）
803	   - 社交媒体链接动态添加/删除
804	   - 保存后弹出成功引导卡片（不跳转）
805	
806	### 5.5 完成标准
807	
808	- [ ] 迁移脚本运行成功，6个新列已添加，二次运行幂等
809	- [ ] 后端模型 import 无错误，新字段已注册
810	- [ ] 后端 API 支持新字段的读取和保存
811	- [ ] 前端 tsc --noEmit exit code 0
812	- [ ] 页面布局：左侧名片+完整度+快捷操作，右侧分组表单
813	- [ ] 专长疾病标签化输入正常工作
814	- [ ] 社交媒体链接动态添加/删除正常
815	- [ ] 资料完整度实时计算，显示缺失项
816	- [ ] 保存成功后弹出引导卡片，不直接跳转
817	- [ ] 实体一致性评分正常显示
818	
819	---
820	
821	## 六、T11：发布管理前端页面
822	
823	### 6.1 任务目标
824	新建独立的发布管理页面（`/distribution`），基于已有的 Distribution 状态机后端，实现文章多平台发布的排期、状态追踪、手动标记发布等功能。
825	
826	### 6.2 后端确认
827	
828	**后端已有（T02完成）**：
829	- 模型：`ArticleDistribution`（含状态机全部字段）
830	- 服务：`DistributionService`（合法流转校验、schedule/start/mark_published/mark_failed/retry/remove）
831	- API：
832	  - `GET /api/v1/distribution`（列表，支持 article_id/status 过滤）
833	  - `POST /api/v1/distribution`（创建）
834	  - `PATCH /api/v1/distribution/{id}/status`（状态流转）
835	  - `POST /api/v1/distribution/{id}/retry`（重试）
836	  - `DELETE /api/v1/distribution/{id}`（删除，仅 draft）
837	
838	**后端需要补充**：列表接口返回文章标题和语义问题（当前只返回 article_id，前端需要关联查询）。
839	
840	#### 6.2.1 修改API：`backend/app/api/distribution.py`
841	
842	**修改点**：`get_distributions` 返回结果追加文章标题和语义问题。
843	
844	在 `items = query.order_by(...).all()` 后，修改返回结构：
845	
846	```python
847	    # 批量查询文章标题和语义
848	    article_ids = [d.article_id for d in items]
849	    articles = {}
850	    if article_ids:
851	        for a in db.query(ArticleDraft).filter(ArticleDraft.id.in_(article_ids)).all():
852	            articles[a.id] = a
853	    semantic_ids = [a.semantic_id for a in articles.values()]
854	    semantics = {}
855	    if semantic_ids:
856	        from app.models.semantic import Semantic
857	        for s in db.query(Semantic).filter(Semantic.id.in_(semantic_ids)).all():
858	            semantics[s.id] = s.question
859	
860	    return {"code": 0, "message": "success", "data": {"items": [
861	        {
862	            "id": d.id,
863	            "article_id": d.article_id,
864	            "article_title": articles.get(d.article_id)?.title if hasattr(articles.get(d.article_id), 'title') else '',
865	            "semantic_id": articles.get(d.article_id)?.semantic_id if hasattr(articles.get(d.article_id), 'semantic_id') else None,
866	            "semantic_question": semantics.get(articles.get(d.article_id)?.semantic_id, '') if articles.get(d.article_id) else '',
867	            "platform": d.platform,
868	            "publish_url": d.publish_url,
869	            "status": d.status,
870	            "note": d.note,
871	            "publish_mode": d.publish_mode,
872	            "retry_count": d.retry_count,
873	            "failed_reason": d.failed_reason,
874	            "scheduled_at": d.scheduled_at.isoformat() if d.scheduled_at else None,
875	            "published_at": d.published_at.isoformat() if d.published_at else None,
876	            "verified_at": d.verified_at.isoformat() if d.verified_at else None,
877	            "created_at": d.created_at.isoformat() if d.created_at else None,
878	        }
879	        for d in items
880	    ]}}
881	```
882	
883	**注意**：Python 没有 `?.` 可选链，需要用普通写法。完整正确的代码：
884	
885	```python
886	    # 批量查询文章标题和语义
887	    article_ids = list(set([d.article_id for d in items]))
888	    articles = {}
889	    if article_ids:
890	        for a in db.query(ArticleDraft).filter(ArticleDraft.id.in_(article_ids)).all():
891	            articles[a.id] = a
892	    semantic_ids = list(set([a.semantic_id for a in articles.values()]))
893	    semantics = {}
894	    if semantic_ids:
895	        from app.models.semantic import Semantic
896	        for s in db.query(Semantic).filter(Semantic.id.in_(semantic_ids)).all():
897	            semantics[s.id] = s.question
898	
899	    result_items = []
900	    for d in items:
901	        article = articles.get(d.article_id)
902	        result_items.append({
903	            "id": d.id,
904	            "article_id": d.article_id,
905	            "article_title": article.title if article else '',
906	            "semantic_id": article.semantic_id if article else None,
907	            "semantic_question": semantics.get(article.semantic_id, '') if article else '',
908	            "platform": d.platform,
909	            "publish_url": d.publish_url,
910	            "status": d.status,
911	            "note": d.note,
912	            "publish_mode": d.publish_mode,
913	            "retry_count": d.retry_count,
914	            "failed_reason": d.failed_reason,
915	            "scheduled_at": d.scheduled_at.isoformat() if d.scheduled_at else None,
916	            "published_at": d.published_at.isoformat() if d.published_at else None,
917	            "verified_at": d.verified_at.isoformat() if d.verified_at else None,
918	            "created_at": d.created_at.isoformat() if d.created_at else None,
919	        })
920	
921	    return {"code": 0, "message": "success", "data": {"items": result_items}}
922	```
923	
924	### 6.3 前端改动
925	
926	#### 6.3.1 新增API方法：`frontend/src/api/index.ts`
927	
928	在 `articleApi` 后追加：
929	
930	```typescript
931	// ============ 发布管理 API ============
932	export const distributionApi = {
933	  getList: (params?: any) => request.get('/distribution', { params }),
934	  create: (data: any) => request.post('/distribution', data),
935	  updateStatus: (id: number, data: { status: string; publish_url?: string; note?: string }) =>
936	    request.patch(`/distribution/${id}/status`, data),
937	  retry: (id: number) => request.post(`/distribution/${id}/retry`),
938	  remove: (id: number) => request.delete(`/distribution/${id}`),
939	}
940	```
941	
942	#### 6.3.2 新建页面：`frontend/src/pages/Distribution.tsx`
943	
944	**完整代码**：
945	
946	```tsx
947	import { useState, useEffect } from 'react'
948	import {
949	  Table, Button, Space, Tag, Modal, Form, Select, Input,
950	  message, Popconfirm, Statistic, Row, Col, Drawer, Descriptions,
951	  Timeline, Tooltip
952	} from 'antd'
953	import {
954	  PlusOutlined, ReloadOutlined, EyeOutlined, CheckOutlined,
955	  ClockCircleOutlined, SyncOutlined, DeleteOutlined, LinkOutlined,
956	  FileTextOutlined, BarChartOutlined
957	} from '@ant-design/icons'
958	import { useNavigate } from 'react-router-dom'
959	import { distributionApi, articleApi } from '@/api'
960	import { PUBLISH_PLATFORMS, PUBLISH_PLATFORM_NAMES } from '@/store/useStore'
961	import EffectTracker from '@/components/EffectTracker'
962	
963	const { TextArea } = Input
964	
965	// 状态配置
966	const STATUS_CONFIG: Record<string, { label: string; color: string; icon: any }> = {
967	  draft: { label: '草稿', color: 'default', icon: FileTextOutlined },
968	  scheduled: { label: '已排期', color: 'blue', icon: ClockCircleOutlined },
969	  processing: { label: '发布中', color: 'processing', icon: SyncOutlined },
970	  published: { label: '已发布', color: 'success', icon: CheckOutlined },
971	  failed: { label: '失败', color: 'error', icon: CloseOutlined },
972	  removed: { label: '已移除', color: 'default', icon: DeleteOutlined },
973	}
974	
975	// 状态流转图
976	const STATUS_FLOW = ['draft', 'scheduled', 'processing', 'published']
977	
978	const Distribution = () => {
979	  const [list, setList] = useState<any[]>([])
980	  const [loading, setLoading] = useState(false)
981	  const [articles, setArticles] = useState<any[]>([])
982	  const [createModal, setCreateModal] = useState(false)
983	  const [detailDrawer, setDetailDrawer] = useState(false)
984	  const [currentRecord, setCurrentRecord] = useState<any>(null)
985	  const [effectVisible, setEffectVisible] = useState(false)
986	  const [form] = Form.useForm()
987	  const [filters, setFilters] = useState({ status: '' as string, platform: '' as string })
988	  const navigate = useNavigate()
989	
990	  useEffect(() => {
991	    loadArticles()
992	    loadList()
993	  }, [filters])
994	
995	  const loadArticles = async () => {
996	    try {
997	      const res: any = await articleApi.getList({ page_size: 100 })
998	      setArticles(res.data.items || res.data || [])
999	    } catch (e) {}
1000	  }
1001	
1002	  const loadList = async () => {
1003	    setLoading(true)
1004	    try {
1005	      const params: any = {}
1006	      if (filters.status) params.status = filters.status
1007	      if (filters.platform) params.platform = filters.platform
1008	      const res: any = await distributionApi.getList(params)
1009	      setList(res.data.items || [])
1010	    } catch (e) {
1011	      // 拦截器已提示
1012	    } finally {
1013	      setLoading(false)
1014	    }
1015	  }
1016	
1017	  const handleCreate = async (values: any) => {
1018	    try {
1019	      await distributionApi.create({
1020	        article_id: values.article_id,
1021	        platform: values.platform,
1022	        status: values.status || 'draft',
1023	        publish_url: values.publish_url || '',
1024	        note: values.note || '',
1025	      })
1026	      message.success('创建发布记录成功')
1027	      setCreateModal(false)
1028	      form.resetFields()
1029	      loadList()
1030	    } catch (e) {
1031	      // 拦截器已提示
1032	    }
1033	  }
1034	
1035	  const handleStatusUpdate = async (record: any, status: string, publish_url?: string) => {
1036	    try {
1037	      await distributionApi.updateStatus(record.id, { status, publish_url })
1038	      message.success(`状态已更新为「${STATUS_CONFIG[status]?.label}」`)
1039	      loadList()
1040	    } catch (e: any) {
1041	      message.error(e.response?.data?.detail || '状态更新失败')
1042	    }
1043	  }
1044	
1045	  const handleMarkPublished = (record: any) => {
1046	    Modal.confirm({
1047	      title: '标记为已发布',
1048	      content: (
1049	        <div>
1050	          <p style={{ marginBottom: 8 }}>请确认已在「{PUBLISH_PLATFORM_NAMES[record.platform] || record.platform}」手动发布了这篇文章。</p>
1051	          <Input
1052	            placeholder="粘贴发布后的URL（可选，用于效果追踪）"
1053	            id="publish_url_input"
1054	            style={{ marginTop: 8 }}
1055	          />
1056	        </div>
1057	      ),
1058	      okText: '确认已发布',
1059	      cancelText: '取消',
1060	      onOk: () => {
1061	        const url = (document.getElementById('publish_url_input') as HTMLInputElement)?.value || ''
1062	        handleStatusUpdate(record, 'published', url)
1063	      },
1064	    })
1065	  }
1066	
1067	  const handleRetry = async (record: any) => {
1068	    try {
1069	      await distributionApi.retry(record.id)
1070	      message.success('已重新加入发布队列')
1071	      loadList()
1072	    } catch (e) {
1073	      message.error('重试失败')
1074	    }
1075	  }
1076	
1077	  const handleViewDetail = (record: any) => {
1078	    setCurrentRecord(record)
1079	    setDetailDrawer(true)
1080	  }
1081	
1082	  // 统计
1083	  const stats = {
1084	    draft: list.filter(r => r.status === 'draft').length,
1085	    scheduled: list.filter(r => r.status === 'scheduled').length,
1086	    processing: list.filter(r => r.status === 'processing').length,
1087	    published: list.filter(r => r.status === 'published').length,
1088	    failed: list.filter(r => r.status === 'failed').length,
1089	  }
1090	
1091	  const columns = [
1092	    {
1093	      title: '文章标题', dataIndex: 'article_title', key: 'article_title',
1094	      ellipsis: true, width: 250,
1095	      render: (text: string, record: any) => (
1096	        <a onClick={() => handleViewDetail(record)} style={{ fontWeight: 500 }}>
1097	          {text || `文章#${record.article_id}`}
1098	        </a>
1099	      ),
1100	    },
1101	    {
1102	      title: '关联语义', dataIndex: 'semantic_question', key: 'semantic_question',
1103	      ellipsis: true, width: 200,
1104	      render: (text: string) => <span style={{ color: '#64748B', fontSize: 12 }}>{text || '-'}</span>,
1105	    },
1106	    {
1107	      title: '平台', dataIndex: 'platform', key: 'platform', width: 120,
1108	      render: (p: string) => {
1109	        const platform = PUBLISH_PLATFORMS.find((x: any) => x.code === p)
1110	        return <Tag color={platform?.tier === 1 ? 'red' : platform?.tier === 2 ? 'orange' : 'default'}>
1111	          {platform?.name || p}
1112	        </Tag>
1113	      },
1114	    },
1115	    {
1116	      title: '状态', dataIndex: 'status', key: 'status', width: 100,
1117	      render: (status: string) => {
1118	        const config = STATUS_CONFIG[status]
1119	        const Icon = config?.icon || FileTextOutlined
1120	        return <Tag color={config?.color} icon={<Icon />}>{config?.label || status}</Tag>
1121	      },
1122	    },
1123	    {
1124	      title: '排期时间', dataIndex: 'scheduled_at', key: 'scheduled_at', width: 160,
1125	      render: (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-',
1126	    },
1127	    {
1128	      title: '发布时间', dataIndex: 'published_at', key: 'published_at', width: 160,
1129	      render: (t: string) => t ? new Date(t).toLocaleString('zh-CN') : '-',
1130	    },
1131	    {
1132	      title: '操作', key: 'action', width: 280, fixed: 'right' as const,
1133	      render: (_: any, record: any) => {
1134	        const actions = []
1135	        // 草稿 → 排期
1136	        if (record.status === 'draft') {
1137	          actions.push(
1138	            <Button key="schedule" size="small" icon={<ClockCircleOutlined />} onClick={() => handleStatusUpdate(record, 'scheduled')}>
1139	              排期
1140	            </Button>
1141	          )
1142	        }
1143	        // 已排期 → 开始发布
1144	        if (record.status === 'scheduled') {
1145	          actions.push(
1146	            <Button key="start" size="small" type="primary" icon={<SyncOutlined />} onClick={() => handleStatusUpdate(record, 'processing')}>
1147	              开始发布
1148	            </Button>
1149	          )
1150	        }
1151	        // 发布中 → 标记已发布
1152	        if (record.status === 'processing') {
1153	          actions.push(
1154	            <Button key="publish" size="small" type="primary" icon={<CheckOutlined />} onClick={() => handleMarkPublished(record)}>
1155	              标记已发布
1156	            </Button>
1157	          )
1158	        }
1159	        // 失败 → 重试
1160	        if (record.status === 'failed') {
1161	          actions.push(
1162	            <Button key="retry" size="small" type="primary" icon={<SyncOutlined />} onClick={() => handleRetry(record)}>
1163	              重试
1164	            </Button>
1165	          )
1166	        }
1167	        // 已发布 → 查看效果
1168	        if (record.status === 'published') {
1169	          actions.push(
1170	            <Button key="effect" size="small" icon={<BarChartOutlined />} onClick={() => { setCurrentRecord(record); setEffectVisible(true) }}>
1171	              效果追踪
1172	            </Button>
1173	          )
1174	        }
1175	        // 查看详情
1176	        actions.push(
1177	          <Button key="detail" size="small" icon={<EyeOutlined />} onClick={() => handleViewDetail(record)}>
1178	            详情
1179	          </Button>
1180	        )
1181	        // 草稿可删除
1182	        if (record.status === 'draft') {
1183	          actions.push(
1184	            <Popconfirm key="delete" title="确定删除这条发布记录？" onConfirm={async () => {
1185	              try { await distributionApi.remove(record.id); message.success('已删除'); loadList() }
1186	              catch (e) { message.error('删除失败') }
1187	            }}>
1188	              <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
1189	            </Popconfirm>
1190	          )
1191	        }
1192	        return <Space size="small" wrap>{actions}</Space>
1193	      },
1194	    },
1195	  ]
1196	
1197	  return (
1198	    <div>
1199	      <div className="page-title-bar">
1200	        <div>
1201	          <h2>发布管理</h2>
1202	          <div className="page-desc">管理文章的多平台发布排期、状态追踪和效果验证</div>
1203	        </div>
1204	        <Space>
1205	          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModal(true)} className="btn-primary-gradient">
1206	            新建发布
1207	          </Button>
1208	          <Button icon={<ReloadOutlined />} onClick={loadList}>刷新</Button>
1209	        </Space>
1210	      </div>
1211	
1212	      {/* 统计卡片 */}
1213	      <Row gutter={16} style={{ marginBottom: 20 }}>
1214	        <Col xs={12} md={4}>
1215	          <div className="geo-card" style={{ padding: 16 }}>
1216	            <Statistic title="草稿" value={stats.draft} valueStyle={{ color: '#94A3B8' }} />
1217	          </div>
1218	        </Col>
1219	        <Col xs={12} md={4}>
1220	          <div className="geo-card" style={{ padding: 16 }}>
1221	            <Statistic title="已排期" value={stats.scheduled} valueStyle={{ color: '#3B82F6' }} />
1222	          </div>
1223	        </Col>
1224	        <Col xs={12} md={4}>
1225	          <div className="geo-card" style={{ padding: 16 }}>
1226	            <Statistic title="发布中" value={stats.processing} valueStyle={{ color: '#F59E0B' }} />
1227	          </div>
1228	        </Col>
1229	        <Col xs={12} md={4}>
1230	          <div className="geo-card" style={{ padding: 16 }}>
1231	            <Statistic title="已发布" value={stats.published} valueStyle={{ color: '#10B981' }} />
1232	          </div>
1233	        </Col>
1234	        <Col xs={12} md={4}>
1235	          <div className="geo-card" style={{ padding: 16 }}>
1236	            <Statistic title="失败" value={stats.failed} valueStyle={{ color: '#EF4444' }} />
1237	          </div>
1238	        </Col>
1239	      </Row>
1240	
1241	      {/* 筛选 */}
1242	      <div className="geo-card" style={{ marginBottom: 20, padding: '12px 16px' }}>
1243	        <Space wrap>
1244	          <Select
1245	            placeholder="状态筛选"
1246	            style={{ width: 140 }}
1247	            value={filters.status || undefined}
1248	            onChange={(v) => setFilters({ ...filters, status: v || '' })}
1249	            allowClear
1250	          >
1251	            {Object.entries(STATUS_CONFIG).map(([key, config]) => (
1252	              <Select.Option key={key} value={key}>{config.label}</Select.Option>
1253	            ))}
1254	          </Select>
1255	          <Select
1256	            placeholder="平台筛选"
1257	            style={{ width: 160 }}
1258	            value={filters.platform || undefined}
1259	            onChange={(v) => setFilters({ ...filters, platform: v || '' })}
1260	            allowClear
1261	            showSearch
1262	            optionFilterProp="label"
1263	          >
1264	            {PUBLISH_PLATFORMS.map((p: any) => (
1265	              <Select.Option key={p.code} value={p.code} label={p.name}>{p.name}</Select.Option>
1266	            ))}
1267	          </Select>
1268	        </Space>
1269	      </div>
1270	
1271	      {/* 状态流转图 */}
1272	      <div className="geo-card" style={{ marginBottom: 20, padding: '12px 16px' }}>
1273	        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
1274	          <span style={{ fontSize: 13, color: '#64748B', marginRight: 8 }}>发布流程：</span>
1275	          {STATUS_FLOW.map((status, idx) => (
1276	            <span key={status} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
1277	              <Tag color={STATUS_CONFIG[status].color}>{STATUS_CONFIG[status].label}</Tag>
1278	              {idx < STATUS_FLOW.length - 1 && <span style={{ color: '#CBD5E1' }}>→</span>}
1279	            </span>
1280	          ))}
1281	          <span style={{ color: '#CBD5E1', margin: '0 4px' }}>→</span>
1282	          <Tag color="error">失败（可重试）</Tag>
1283	        </div>
1284	      </div>
1285	
1286	      {/* 列表 */}
1287	      <div className="geo-card">
1288	        <Table
1289	          dataSource={list}
1290	          columns={columns}
1291	          rowKey="id"
1292	          loading={loading}
1293	          pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }}
1294	          scroll={{ x: 1200 }}
1295	          locale={{ emptyText: '暂无发布记录，点击「新建发布」开始管理文章发布' }}
1296	        />
1297	      </div>
1298	
1299	      {/* 新建发布弹窗 */}
1300	      <Modal
1301	        title="新建发布记录"
1302	        open={createModal}
1303	        onCancel={() => { setCreateModal(false); form.resetFields() }}
1304	        onOk={() => form.submit()}
1305	        okText="创建"
1306	        cancelText="取消"
1307	        width={560}
1308	      >
1309	        <Form form={form} layout="vertical" onFinish={handleCreate}>
1310	          <Form.Item name="article_id" label="选择文章" rules={[{ required: true, message: '请选择文章' }]}>
1311	            <Select
1312	              placeholder="请选择要发布的文章"
1313	              showSearch
1314	              optionFilterProp="label"
1315	              options={articles.map((a: any) => ({ value: a.id, label: a.title || `文章#${a.id}` }))}
1316	            />
1317	          </Form.Item>
1318	          <Form.Item name="platform" label="发布平台" rules={[{ required: true, message: '请选择平台' }]}>
1319	            <Select placeholder="请选择发布平台" showSearch optionFilterProp="label">
1320	              {PUBLISH_PLATFORMS.map((p: any) => (
1321	                <Select.Option key={p.code} value={p.code} label={p.name}>
1322	                  <span>{p.name}</span>
1323	                  <span style={{ color: '#999', fontSize: 12, marginLeft: 8 }}>{p.tierLabel}</span>
1324	                </Select.Option>
1325	              ))}
1326	            </Select>
1327	          </Form.Item>
1328	          <Form.Item name="status" label="初始状态" initialValue="draft">
1329	            <Select>
1330	              <Select.Option value="draft">草稿</Select.Option>
1331	              <Select.Option value="scheduled">已排期</Select.Option>
1332	            </Select>
1333	          </Form.Item>
1334	          <Form.Item name="publish_url" label="发布链接（可选）">
1335	            <Input placeholder="已发布的话可粘贴链接" prefix={<LinkOutlined />} />
1336	          </Form.Item>
1337	          <Form.Item name="note" label="备注（可选）">
1338	            <TextArea rows={2} placeholder="备注信息" />
1339	          </Form.Item>
1340	        </Form>
1341	      </Modal>
1342	
1343	      {/* 详情抽屉 */}
1344	      <Drawer
1345	        title="发布详情"
1346	        placement="right"
1347	        width={500}
1348	        open={detailDrawer}
1349	        onClose={() => setDetailDrawer(false)}
1350	      >
1351	        {currentRecord && (
1352	          <div>
1353	            <Descriptions title="基本信息" column={1} bordered size="small" style={{ marginBottom: 20 }}>
1354	              <Descriptions.Item label="文章标题">{currentRecord.article_title || '-'}</Descriptions.Item>
1355	              <Descriptions.Item label="关联语义">{currentRecord.semantic_question || '-'}</Descriptions.Item>
1356	              <Descriptions.Item label="发布平台">{PUBLISH_PLATFORM_NAMES[currentRecord.platform] || currentRecord.platform}</Descriptions.Item>
1357	              <Descriptions.Item label="状态">
1358	                <Tag color={STATUS_CONFIG[currentRecord.status]?.color}>
1359	                  {STATUS_CONFIG[currentRecord.status]?.label}
1360	                </Tag>
1361	              </Descriptions.Item>
1362	              <Descriptions.Item label="发布模式">{currentRecord.publish_mode === 'manual' ? '手动发布' : '自动发布'}</Descriptions.Item>
1363	              <Descriptions.Item label="重试次数">{currentRecord.retry_count}</Descriptions.Item>
1364	              <Descriptions.Item label="创建时间">{currentRecord.created_at ? new Date(currentRecord.created_at).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
1365	              <Descriptions.Item label="排期时间">{currentRecord.scheduled_at ? new Date(currentRecord.scheduled_at).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
1366	              <Descriptions.Item label="发布时间">{currentRecord.published_at ? new Date(currentRecord.published_at).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
1367	              <Descriptions.Item label="发布链接">
1368	                {currentRecord.publish_url ? (
1369	                  <a href={currentRecord.publish_url} target="_blank" rel="noreferrer">{currentRecord.publish_url}</a>
1370	                ) : '-'}
1371	              </Descriptions.Item>
1372	              {currentRecord.failed_reason && (
1373	                <Descriptions.Item label="失败原因"><span style={{ color: '#EF4444' }}>{currentRecord.failed_reason}</span></Descriptions.Item>
1374	              )}
1375	              {currentRecord.note && (
1376	                <Descriptions.Item label="备注">{currentRecord.note}</Descriptions.Item>
1377	              )}
1378	            </Descriptions>
1379	
1380	            <div style={{ marginBottom: 16 }}>
1381	              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>状态流转时间线</div>
1382	              <Timeline
1383	                items={[
1384	                  { color: 'blue', children: `创建记录 - ${currentRecord.created_at ? new Date(currentRecord.created_at).toLocaleString('zh-CN') : '-'}` },
1385	                  currentRecord.scheduled_at && { color: 'blue', children: `排期 - ${new Date(currentRecord.scheduled_at).toLocaleString('zh-CN')}` },
1386	                  currentRecord.published_at && { color: 'green', children: `发布完成 - ${new Date(currentRecord.published_at).toLocaleString('zh-CN')}` },
1387	                  currentRecord.status === 'failed' && { color: 'red', children: `发布失败 - ${currentRecord.failed_reason || '未知原因'}` },
1388	                ].filter(Boolean)}
1389	              />
1390	            </div>
1391	
1392	            {currentRecord.status === 'published' && (
1393	              <Button type="primary" block icon={<BarChartOutlined />} onClick={() => { setEffectVisible(true) }} className="btn-primary-gradient">
1394	                查看内容效果追踪
1395	              </Button>
1396	            )}
1397	          </div>
1398	        )}
1399	      </Drawer>
1400	
1401	      {/* 效果追踪抽屉（T12组件） */}
1402	      <EffectTracker
1403	        visible={effectVisible}
1404	        onClose={() => setEffectVisible(false)}
1405	        distribution={currentRecord}
1406	        onRefresh={loadList}
1407	      />
1408	    </div>
1409	  )
1410	}
1411	
1412	export default Distribution
1413	```
1414	
1415	#### 6.3.3 注册路由：`frontend/src/router/index.tsx`
1416	
1417	在 lazy 导入区追加：
1418	```typescript
1419	const Distribution = lazy(() => import('@/pages/Distribution'))
1420	```
1421	
1422	在路由区追加（放在 content 后面）：
1423	```typescript
1424	<Route path="distribution" element={<RequireAuth><Distribution /></RequireAuth>} />
1425	```
1426	
1427	#### 6.3.4 添加菜单：`frontend/src/components/Layout.tsx`
1428	
1429	在 `menuItems` 数组中，`内容中心` 后面追加：
1430	```typescript
1431	  { key: '/distribution', icon: <SendOutlined />, label: '发布管理' },
1432	```
1433	
1434	同时在图标导入中追加 `SendOutlined`。
1435	
1436	### 6.4 验证步骤
1437	
1438	1. **后端API验证**：重启后端，访问 `GET /api/v1/distribution`，确认返回 `article_title` 和 `semantic_question` 字段
1439	2. **前端tsc**：`npx tsc --noEmit` exit code 0
1440	3. **功能验证**：
1441	   - 左侧菜单出现"发布管理"入口
1442	   - 访问 `/distribution` 显示统计卡片、筛选、状态流转图、列表
1443	   - 点击"新建发布"可选择文章和平台，创建记录
1444	   - 状态流转正常：草稿→排期→发布中→已发布
1445	   - 失败可重试
1446	   - 已发布记录可点击"效果追踪"（T12功能）
1447	
1448	### 6.5 完成标准
1449	
1450	- [ ] 后端列表接口返回文章标题和语义问题
1451	- [ ] 前端 tsc exit code 0
1452	- [ ] 发布管理页面可访问，左侧菜单有入口
1453	- [ ] 统计卡片正确显示各状态数量
1454	- [ ] 新建发布弹窗正常，可选择文章和平台
1455	- [ ] 状态流转正常（草稿→排期→发布中→已发布）
1456	- [ ] 失败可重试，草稿可删除
1457	- [ ] 详情抽屉显示完整信息和时间线
1458	- [ ] 已发布记录有"效果追踪"入口
1459	
1460	---
1461	
1462	## 七、T12：内容效果追踪基础版
1463	
1464	### 7.1 任务目标
1465	实现内容效果追踪基础功能：对已发布的文章，手动触发重新采集关联语义，对比发布前后的 GEO 提及率、AEO 引用率、排名变化，用图表展示效果趋势。
1466	
1467	### 7.2 后端改动
1468	
1469	#### 7.2.1 新增端点：`backend/app/api/distribution.py`
1470	
1471	在文件末尾追加2个端点：
1472	
1473	```python
1474	@router.get("/{dist_id}/effect", summary="获取发布效果对比（发布前后GEO/AEO/排名变化）")
1475	def get_distribution_effect(
1476	    dist_id: int,
1477	    db: Session = Depends(get_db),
1478	    user_id: int = Depends(get_current_user_id)
1479	):
1480	    dist = DistributionService.get_or_404(db, dist_id, user_id)
1481	    if dist.status != 'published':
1482	        raise HTTPException(status_code=400, detail="仅已发布的记录可查看效果追踪")
1483	
1484	    # 获取关联文章和语义
1485	    article = db.query(ArticleDraft).filter(ArticleDraft.id == dist.article_id).first()
1486	    if not article:
1487	        raise HTTPException(status_code=404, detail="关联文章不存在")
1488	
1489	    semantic_id = article.semantic_id
1490	    publish_time = dist.published_at or dist.created_at
1491	
1492	    # 发布前数据（发布时间之前的采集记录）
1493	    before_records = db.query(MonitorRecord).filter(
1494	        MonitorRecord.semantic_id == semantic_id,
1495	        MonitorRecord.created_at < publish_time
1496	    ).all()
1497	
1498	    # 发布后数据（发布时间之后的采集记录）
1499	    after_records = db.query(MonitorRecord).filter(
1500	        MonitorRecord.semantic_id == semantic_id,
1501	        MonitorRecord.created_at >= publish_time
1502	    ).all()
1503	
1504	    def calc_stats(records):
1505	        if not records:
1506	            return {"total": 0, "mention_rate": 0, "citation_rate": 0, "avg_rank": None, "mentioned_count": 0}
1507	        total = len(records)
1508	        mentioned = sum(1 for r in records if r.mentioned)
1509	        cited = sum(1 for r in records if r.cite_count and r.cite_count > 0)
1510	        ranks = [r.rank for r in records if r.rank and r.rank > 0]
1511	        avg_rank = sum(ranks) / len(ranks) if ranks else None
1512	        return {
1513	            "total": total,
1514	            "mention_rate": round(mentioned / total * 100, 1),
1515	            "citation_rate": round(cited / total * 100, 1),
1516	            "avg_rank": round(avg_rank, 1) if avg_rank else None,
1517	            "mentioned_count": mentioned,
1518	        }
1519	
1520	    before = calc_stats(before_records)
1521	    after = calc_stats(after_records)
1522	
1523	    # 变化量
1524	    change = {
1525	        "mention_rate": round(after["mention_rate"] - before["mention_rate"], 1),
1526	        "citation_rate": round(after["citation_rate"] - before["citation_rate"], 1),
1527	        "avg_rank": round((before["avg_rank"] or 0) - (after["avg_rank"] or 0), 1) if before["avg_rank"] and after["avg_rank"] else None,
1528	    }
1529	
1530	    # 按日期统计趋势（最近30天）
1531	    from datetime import datetime, timedelta
1532	    thirty_days_ago = datetime.now() - timedelta(days=30)
1533	    trend_records = db.query(MonitorRecord).filter(
1534	        MonitorRecord.semantic_id == semantic_id,
1535	        MonitorRecord.created_at >= thirty_days_ago
1536	    ).all()
1537	
1538	    trend = {}
1539	    for r in trend_records:
1540	        date_str = r.created_at.strftime('%Y-%m-%d') if hasattr(r.created_at, 'strftime') else str(r.created_at)[:10]
1541	        if date_str not in trend:
1542	            trend[date_str] = {"total": 0, "mentioned": 0}
1543	        trend[date_str]["total"] += 1
1544	        if r.mentioned:
1545	            trend[date_str]["mentioned"] += 1
1546	
1547	    trend_data = sorted([
1548	        {"date": d, "mention_rate": round(v["mentioned"] / v["total"] * 100, 1)}
1549	        for d, v in trend.items()
1550	    ], key=lambda x: x["date"])
1551	
1552	    return {
1553	        "code": 0,
1554	        "message": "success",
1555	        "data": {
1556	            "semantic_id": semantic_id,
1557	            "semantic_question": article.title,  # 用文章标题，实际应查semantic
1558	            "publish_time": publish_time.isoformat() if publish_time else None,
1559	            "before": before,
1560	            "after": after,
1561	            "change": change,
1562	            "trend": trend_data,
1563	        }
1564	    }
1565	
1566	
1567	@router.post("/{dist_id}/recollect", summary="触发重新采集关联语义（用于效果验证）")
1568	def recollect_distribution(
1569	    dist_id: int,
1570	    db: Session = Depends(get_db),
1571	    user_id: int = Depends(get_current_user_id)
1572	):
1573	    dist = DistributionService.get_or_404(db, dist_id, user_id)
1574	    article = db.query(ArticleDraft).filter(ArticleDraft.id == dist.article_id).first()
1575	    if not article:
1576	        raise HTTPException(status_code=404, detail="关联文章不存在")
1577	
1578	    # 创建异步采集任务（复用 monitor_collect）
1579	    from app.models.task import AsyncTask
1580	    import json
1581	    task = AsyncTask(
1582	        workspace_id=None,  # TODO: 从workspace_member获取
1583	        task_type="monitor_collect",
1584	        status="queued",
1585	        progress=0,
1586	        progress_message="等待执行",
1587	        payload_json=json.dumps({"question_id": article.semantic_id, "detect_round": 99}),
1588	        created_by=user_id,
1589	    )
1590	    db.add(task)
1591	    db.commit()
1592	    db.refresh(task)
1593	
1594	    return {"code": 0, "message": "success", "data": {"task_id": task.id, "message": "已加入采集队列，完成后可查看最新效果"}}
1595	```
1596	
1597	**注意**：需要导入 MonitorRecord 模型。在文件顶部导入区追加：
1598	```python
1599	from app.models.monitor import MonitorRecord
1600	```
1601	
1602	同时，`semantic_question` 应该查语义表而不是用文章标题。修正：
1603	```python
1604	    from app.models.semantic import Semantic
1605	    semantic = db.query(Semantic).filter(Semantic.id == semantic_id).first()
1606	    semantic_question = semantic.question if semantic else ''
1607	```
1608	
1609	#### 7.2.2 确认 MonitorRecord 模型字段
1610	
1611	需要确认 `app/models/monitor.py` 中有 `semantic_id`、`mentioned`、`rank`、`cite_count`、`created_at` 字段。从之前的数据库检查看，这些字段都存在。
1612	
1613	### 7.3 前端改动
1614	
1615	#### 7.3.1 新增API方法：`frontend/src/api/index.ts`
1616	
1617	在 `distributionApi` 中追加：
1618	```typescript
1619	  getEffect: (id: number) => request.get(`/distribution/${id}/effect`),
1620	  recollect: (id: number) => request.post(`/distribution/${id}/recollect`),
1621	```
1622	
1623	#### 7.3.2 新建组件：`frontend/src/components/EffectTracker.tsx`
1624	
1625	**完整代码**：
1626	
1627	```tsx
1628	import { useState, useEffect } from 'react'
1629	import { Drawer, Button, Spin, Statistic, Row, Col, message, Empty, Tag, Space, Card } from 'antd'
1630	import {
1631	  ArrowUpOutlined, ArrowDownOutlined, MinusOutlined,
1632	  ReloadOutlined, BarChartOutlined, EyeOutlined
1633	} from '@ant-design/icons'
1634	import ReactECharts from 'echarts-for-react'
1635	import { distributionApi } from '@/api'
1636	
1637	interface EffectTrackerProps {
1638	  visible: boolean
1639	  onClose: () => void
1640	  distribution: any
1641	  onRefresh?: () => void
1642	}
1643	
1644	const EffectTracker: React.FC<EffectTrackerProps> = ({ visible, onClose, distribution, onRefresh }) => {
1645	  const [loading, setLoading] = useState(false)
1646	  const [recollecting, setRecollecting] = useState(false)
1647	  const [effectData, setEffectData] = useState<any>(null)
1648	
1649	  useEffect(() => {
1650	    if (visible && distribution?.id) {
1651	      loadEffect()
1652	    }
1653	  }, [visible, distribution?.id])
1654	
1655	  const loadEffect = async () => {
1656	    if (!distribution?.id) return
1657	    setLoading(true)
1658	    try {
1659	      const res: any = await distributionApi.getEffect(distribution.id)
1660	      setEffectData(res.data)
1661	    } catch (e: any) {
1662	      message.error(e.response?.data?.detail || '加载效果数据失败')
1663	    } finally {
1664	      setLoading(false)
1665	    }
1666	  }
1667	
1668	  const handleRecollect = async () => {
1669	    if (!distribution?.id) return
1670	    setRecollecting(true)
1671	    try {
1672	      const res: any = await distributionApi.recollect(distribution.id)
1673	      message.success(`已加入采集队列（任务#${res.data.task_id}），完成后点击刷新查看最新效果`)
1674	    } catch (e: any) {
1675	      message.error(e.response?.data?.detail || '触发采集失败')
1676	    } finally {
1677	      setRecollecting(false)
1678	    }
1679	  }
1680	
1681	  const renderChange = (value: number, isRank = false) => {
1682	    if (value === null || value === undefined) return <Tag>无数据</Tag>
1683	    if (value > 0) {
1684	      return <Tag color={isRank ? 'green' : 'green'} icon={<ArrowUpOutlined />}>{isRank ? `上升${value}位` : `+${value}%`}</Tag>
1685	    } else if (value < 0) {
1686	      return <Tag color={isRank ? 'red' : 'red'} icon={<ArrowDownOutlined />}>{isRank ? `下降${Math.abs(value)}位` : `${value}%`}</Tag>
1687	    }
1688	    return <Tag icon={<MinusOutlined />}>无变化</Tag>
1689	  }
1690	
1691	  // 趋势图配置
1692	  const getTrendOption = () => {
1693	    if (!effectData?.trend || effectData.trend.length === 0) return null
1694	    return {
1695	      tooltip: { trigger: 'axis' },
1696	      grid: { left: 40, right: 20, top: 30, bottom: 30 },
1697	      xAxis: {
1698	        type: 'category',
1699	        data: effectData.trend.map((d: any) => d.date),
1700	        axisLabel: { fontSize: 11, rotate: 30 },
1701	      },
1702	      yAxis: {
1703	        type: 'value',
1704	        name: '提及率(%)',
1705	        max: 100,
1706	        axisLabel: { fontSize: 11 },
1707	      },
1708	      series: [{
1709	        name: 'GEO提及率',
1710	        type: 'line',
1711	        data: effectData.trend.map((d: any) => d.mention_rate),
1712	        smooth: true,
1713	        symbol: 'circle',
1714	        symbolSize: 6,
1715	        lineStyle: { width: 2, color: '#3B82F6' },
1716	        itemStyle: { color: '#3B82F6' },
1717	        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(59,130,246,0.3)' }, { offset: 1, color: 'rgba(59,130,246,0.02)' }] } },
1718	        markLine: effectData.publish_time ? {
1719	          symbol: 'none',
1720	          data: [{ xAxis: effectData.publish_time?.slice(0, 10), label: { formatter: '发布时间', fontSize: 11 }, lineStyle: { color: '#10B981', type: 'dashed' } }],
1721	        } : undefined,
1722	      }],
1723	    }
1724	  }
1725	
1726	  return (
1727	    <Drawer
1728	      title={
1729	        <div>
1730	          <BarChartOutlined style={{ marginRight: 8, color: '#3B82F6' }} />
1731	          内容效果追踪
1732	          <div style={{ fontSize: 12, color: '#94A3B8', fontWeight: 400, marginTop: 4 }}>
1733	            {distribution?.article_title || '文章'}
1734	          </div>
1735	        </div>
1736	      }
1737	      placement="right"
1738	      width={640}
1739	      open={visible}
1740	      onClose={onClose}
1741	      extra={
1742	        <Space>
1743	          <Button icon={<ReloadOutlined />} onClick={loadEffect} loading={loading}>刷新</Button>
1744	          <Button type="primary" icon={<ReloadOutlined />} onClick={handleRecollect} loading={recollecting} className="btn-primary-gradient">
1745	            重新采集验证
1746	          </Button>
1747	        </Space>
1748	      }
1749	    >
1750	      <Spin spinning={loading}>
1751	        {!effectData ? (
1752	          <Empty description="暂无效果数据，点击「重新采集验证」开始追踪" />
1753	        ) : (
1754	          <div>
1755	            {/* 发布前后对比 */}
1756	            <Card title="📊 发布前后对比" size="small" style={{ marginBottom: 16 }}>
1757	              <Row gutter={16}>
1758	                <Col span={8}>
1759	                  <Statistic
1760	                    title="GEO提及率"
1761	                    value={effectData.after?.mention_rate || 0}
1762	                    suffix="%"
1763	                    valueStyle={{ color: '#3B82F6', fontSize: 24, fontWeight: 700 }}
1764	                  />
1765	                  <div style={{ marginTop: 4 }}>
1766	                    发布前 {effectData.before?.mention_rate || 0}%
1767	                    {renderChange(effectData.change?.mention_rate)}
1768	                  </div>
1769	                </Col>
1770	                <Col span={8}>
1771	                  <Statistic
1772	                    title="AEO引用率"
1773	                    value={effectData.after?.citation_rate || 0}
1774	                    suffix="%"
1775	                    valueStyle={{ color: '#8B5CF6', fontSize: 24, fontWeight: 700 }}
1776	                  />
1777	                  <div style={{ marginTop: 4 }}>
1778	                    发布前 {effectData.before?.citation_rate || 0}%
1779	                    {renderChange(effectData.change?.citation_rate)}
1780	                  </div>
1781	                </Col>
1782	                <Col span={8}>
1783	                  <Statistic
1784	                    title="平均排名"
1785	                    value={effectData.after?.avg_rank || '-'}
1786	                    suffix={effectData.after?.avg_rank ? '名' : ''}
1787	                    valueStyle={{ color: '#F59E0B', fontSize: 24, fontWeight: 700 }}
1788	                  />
1789	                  <div style={{ marginTop: 4 }}>
1790	                    发布前 {effectData.before?.avg_rank || '-'}
1791	                    {effectData.change?.avg_rank !== null && effectData.change?.avg_rank !== undefined && renderChange(effectData.change.avg_rank, true)}
1792	                  </div>
1793	                </Col>
1794	              </Row>
1795	            </Card>
1796	
1797	            {/* 样本量说明 */}
1798	            <div style={{ background: '#F0F9FF', padding: '10px 14px', borderRadius: 8, marginBottom: 16, fontSize: 12, color: '#0369A1' }}>
1799	              💡 数据样本：发布前 {effectData.before?.total || 0} 条采集记录，发布后 {effectData.after?.total || 0} 条采集记录。
1800	              {effectData.after?.total === 0 && ' 发布后暂无采集数据，建议点击「重新采集验证」获取最新数据。'}
1801	            </div>
1802	
1803	            {/* 趋势图 */}
1804	            <Card title="📈 最近30天GEO提及率趋势" size="small">
1805	              {effectData.trend && effectData.trend.length > 0 ? (
1806	                <ReactECharts option={getTrendOption()} style={{ height: 280 }} notMerge />
1807	              ) : (
1808	                <Empty description="暂无趋势数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
1809	              )}
1810	            </Card>
1811	
1812	            {/* 使用说明 */}
1813	            <div style={{ marginTop: 16, background: '#F8FAFC', padding: 16, borderRadius: 12 }}>
1814	              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: '#334155' }}>📋 效果追踪使用说明</div>
1815	              <div style={{ fontSize: 12, color: '#64748B', lineHeight: 1.8 }}>
1816	                1. 文章发布后，系统会对比发布前后的 GEO 提及率、AEO 引用率、排名变化<br />
1817	                2. 点击「重新采集验证」可触发一次新的采集，获取最新数据<br />
1818	                3. 趋势图展示最近30天的提及率变化，绿色虚线为发布时间点<br />
1819	                4. 建议发布后 3-7 天再查看效果，AI 搜索索引更新需要时间
1820	              </div>
1821	            </div>
1822	          </div>
1823	        )}
1824	      </Spin>
1825	    </Drawer>
1826	  )
1827	}
1828	
1829	export default EffectTracker
1830	```
1831	
1832	**注意**：需要确认项目已安装 `echarts-for-react`。如果没有，需要 `npm install echarts echarts-for-react`。从之前的项目结构看，项目已有 ECharts 依赖（Dashboard 用了），但可能用的是原生 echarts 而不是 echarts-for-react。需要确认。
1833	
1834	如果项目用的是原生 echarts（`import * as echarts from 'echarts'`），则需要改用 useRef + useEffect 的方式初始化图表，而不是 echarts-for-react。
1835	
1836	**备选方案（原生echarts）**：
1837	
1838	```tsx
1839	import { useRef, useEffect } from 'react'
1840	import * as echarts from 'echarts'
1841	
1842	// 在组件中：
1843	const chartRef = useRef<HTMLDivElement>(null)
1844	const chartInstance = useRef<any>(null)
1845	
1846	useEffect(() => {
1847	  if (chartRef.current && effectData?.trend?.length > 0) {
1848	    if (!chartInstance.current) {
1849	      chartInstance.current = echarts.init(chartRef.current)
1850	    }
1851	    chartInstance.current.setOption(getTrendOption())
1852	  }
1853	  return () => {
1854	    chartInstance.current?.dispose()
1855	    chartInstance.current = null
1856	  }
1857	}, [effectData])
1858	
1859	// JSX:
1860	<div ref={chartRef} style={{ height: 280 }} />
1861	```
1862	
1863	执行时需要先确认项目用的是哪种 ECharts 方式，选择对应的实现。
1864	
1865	### 7.4 验证步骤
1866	
1867	1. **后端API验证**：
1868	   - `GET /api/v1/distribution/{id}/effect` 返回发布前后对比数据
1869	   - `POST /api/v1/distribution/{id}/recollect` 创建采集任务
1870	
1871	2. **前端tsc**：`npx tsc --noEmit` exit code 0
1872	
1873	3. **功能验证**：
1874	   - 发布管理页面，已发布记录点击"效果追踪"打开抽屉
1875	   - 显示发布前后 GEO提及率/AEO引用率/排名对比
1876	   - 显示变化量（上升/下降标签）
1877	   - 显示最近30天趋势图
1878	   - 点击"重新采集验证"创建采集任务
1879	   - 采集完成后点击"刷新"查看最新效果
1880	
1881	### 7.5 完成标准
1882	
1883	- [ ] 后端2个新端点正常工作
1884	- [ ] 前端 tsc exit code 0
1885	- [ ] 效果追踪抽屉可从发布管理页面打开
1886	- [ ] 发布前后对比数据正确显示（GEO/AEO/排名）
1887	- [ ] 变化量标签正确（上升绿色/下降红色）
1888	- [ ] 趋势图正常渲染（如有数据）
1889	- [ ] "重新采集验证"按钮可创建采集任务
1890	- [ ] 空数据状态有友好提示
1891	
1892	---
1893	
1894	## 八、Session 划分与执行顺序
1895	
1896	### Session 1：T10 我的资料重新设计
1897	
1898	**执行前检查**：
1899	- 后端服务已停止（避免文件占用）
1900	- 数据库已备份
1901	
1902	**执行步骤**：
1903	1. 修改 `backend/app/models/doctor.py`（加6个字段）
1904	2. 修改 `backend/scripts/migrate_v2.py`（追加迁移）
1905	3. 运行迁移脚本，验证幂等
1906	4. 修改 `backend/app/api/doctor.py`（get/save支持新字段）
1907	5. 验证后端 import
1908	6. 完全重写 `frontend/src/pages/Profile.tsx`
1909	7. 前端 tsc 验证
1910	8. 启动后端，功能验证
1911	
1912	**完成标准**：见 5.5 节
1913	
1914	### Session 2：T11 发布管理 + T12 效果追踪
1915	
1916	**执行前检查**：
1917	- T10 已完成并验证
1918	- 确认项目 ECharts 使用方式（原生 or echarts-for-react）
1919	
1920	**执行步骤**：
1921	1. 修改 `backend/app/api/distribution.py`（列表返回文章标题+语义，新增2个端点）
1922	2. 验证后端 import
1923	3. 修改 `frontend/src/api/index.ts`（新增 distributionApi）
1924	4. 新建 `frontend/src/pages/Distribution.tsx`
1925	5. 新建 `frontend/src/components/EffectTracker.tsx`
1926	6. 修改 `frontend/src/router/index.tsx`（注册路由）
1927	7. 修改 `frontend/src/components/Layout.tsx`（加菜单）
1928	8. 前端 tsc 验证
1929	9. 启动后端，功能验证
1930	
1931	**完成标准**：见 6.5 和 7.5 节
1932	
1933	---
1934	
1935	## 九、常见问题排查
1936	
1937	### Q1：迁移脚本报错 "duplicate column name"
1938	**原因**：列已存在，ensure_column 应该幂等。检查 ensure_column 函数是否正确判断列存在。
1939	**解决**：手动检查数据库列，确认已存在后跳过。
1940	
1941	### Q2：前端 tsc 报错 "Cannot find module 'echarts-for-react'"
1942	**原因**：项目用的是原生 echarts，不是 echarts-for-react。
1943	**解决**：改用原生 echarts + useRef 方式初始化图表（见 7.3.2 备选方案）。
1944	
1945	### Q3：效果追踪接口返回 400 "仅已发布的记录可查看效果追踪"
1946	**原因**：该发布记录状态不是 published。
1947	**解决**：先将记录标记为已发布，再查看效果。
1948	
1949	### Q4：重新采集后任务一直等待中
1950	**原因**：Worker 进程未启动。
1951	**解决**：确认后端启动时 `AUTO_START_WORKER=true`（默认），查看日志是否有 "内嵌 Worker 线程已启动"。
1952	
1953	### Q5：资料完整度计算不准确
1954	**原因**：Form.useWatch 可能在表单未初始化时返回 undefined。
1955	**解决**：在 completeness 计算中加空值判断，`formValues || {}`。
1956	
1957	---
1958	
1959	## 十、完成检查表
1960	
1961	### T10 我的资料重新设计
1962	- [ ] 数据库迁移成功，6个新列已添加
1963	- [ ] 后端模型 import 无错误
1964	- [ ] 后端 API 支持新字段读写
1965	- [ ] 前端 Profile.tsx 完全重写
1966	- [ ] 前端 tsc exit code 0
1967	- [ ] 左侧名片显示（头像+姓名+职称+医院+科室）
1968	- [ ] 资料完整度进度条实时计算
1969	- [ ] 专长疾病标签化输入正常
1970	- [ ] 社交媒体链接动态添加/删除正常
1971	- [ ] 4个分组可折叠
1972	- [ ] 保存成功弹出引导卡片
1973	
1974	### T11 发布管理
1975	- [ ] 后端列表接口返回文章标题和语义
1976	- [ ] 前端 Distribution.tsx 新建完成
1977	- [ ] 路由注册，左侧菜单有入口
1978	- [ ] 前端 tsc exit code 0
1979	- [ ] 统计卡片正确显示
1980	- [ ] 新建发布弹窗正常
1981	- [ ] 状态流转正常（草稿→排期→发布中→已发布）
1982	- [ ] 失败可重试，草稿可删除
1983	- [ ] 详情抽屉显示完整信息
1984	
1985	### T12 效果追踪
1986	- [ ] 后端2个新端点正常工作
1987	- [ ] 前端 EffectTracker.tsx 新建完成
1988	- [ ] 前端 tsc exit code 0
1989	- [ ] 效果追踪抽屉可打开
1990	- [ ] 发布前后对比数据正确
1991	- [ ] 变化量标签正确
1992	- [ ] 趋势图正常渲染
1993	- [ ] 重新采集验证按钮可用
1994	
1995	---
1996	
1997	## 十一、问题记录区
1998	
1999	> 执行过程中遇到的问题和解决方案记录在此
2000	
2001	| # | 问题 | 解决方案 | 发现时间 |
2002	|---|---|---|---|
2003	| 1 | （待记录） | | |
2004	
2005	---
2006	
2007	**手册版本**：v1.0
2008	**创建时间**：2026-09-14
2009	**最后更新**：2026-09-14
2010	

[End of file.]