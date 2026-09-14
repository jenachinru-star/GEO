import { create } from 'zustand'

interface AppState {
  // 系统信息
  systemInfo: any
  platformList: any[]
  // 加载状态
  loading: boolean
  // 用户认证
  token: string | null
  user: any | null
  // GEO医生数据
  doctorProfile: any | null
  semantics: any[]
  // 方法
  setSystemInfo: (info: any) => void
  setPlatformList: (list: any[]) => void
  setLoading: (loading: boolean) => void
  setAuth: (token: string, user: any) => void
  clearAuth: () => void
  setDoctorProfile: (p: any | null) => void
  setSemantics: (list: any[]) => void
}

const TOKEN_KEY = 'geo_token'
const USER_KEY = 'geo_user'

export const useAppStore = create<AppState>((set) => ({
  systemInfo: null,
  platformList: [],
  loading: false,
  token: localStorage.getItem(TOKEN_KEY),
  user: JSON.parse(localStorage.getItem(USER_KEY) || 'null'),
  doctorProfile: null,
  semantics: [],
  setSystemInfo: (info) => set({ systemInfo: info }),
  setPlatformList: (list) => set({ platformList: list }),
  setLoading: (loading) => set({ loading }),
  setAuth: (token, user) => {
    localStorage.setItem(TOKEN_KEY, token)
    localStorage.setItem(USER_KEY, JSON.stringify(user))
    set({ token, user })
  },
  clearAuth: () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    set({ token: null, user: null })
  },
  setDoctorProfile: (p) => set({ doctorProfile: p }),
  setSemantics: (list) => set({ semantics: list }),
}))

// 平台名称映射
export const PLATFORM_NAMES: Record<string, string> = {
  deepseek: 'DeepSeek',
  glm: 'GLM',
  minimax: 'MiniMax',
  doubao: '豆包',
  qwen: '通义千问'
}

// 分类名称映射
export const CATEGORY_NAMES: Record<string, string> = {
  brand: '品牌类',
  tech: '技术类',
  industry: '行业类',
  competitor: '竞品类',
  general: '综合类',
  company: '公司简介',
  business: '业务线',
  case: '项目案例',
  qualification: '资质专利',
  team: '团队信息',
  article: '文章',
  whitepaper: '白皮书',
  news: '新闻稿'
}

// 发布平台配置（按AI抓取价值分层）
export interface PublishPlatform {
  code: string
  name: string
  tier: 1 | 2 | 3  // AI抓取价值层级
  tierLabel: string
  aiValue: string  // AI抓取价值说明
  rules: string[]  // 平台违规规则
}

export const PUBLISH_PLATFORMS: PublishPlatform[] = [
  // 第一层：搜索引擎自有内容平台（AI抓取优先级最高）
  { code: 'baijiahao', name: '百家号', tier: 1, tierLabel: 'AI高优先抓取', aiValue: '百度生态核心，文心一言/百度搜索AI优先抓取，GEO地域匹配能力极强', rules: ['医疗内容需资质认证', '禁止绝对化用语（最/第一）', '需标注信息来源'] },
  { code: 'dayu', name: '大鱼号', tier: 1, tierLabel: 'AI高优先抓取', aiValue: 'UC/阿里生态，通义千问/UC搜索爬虫抓取，省内跨城曝光效果好', rules: ['禁止医疗广告', '需原创声明', '标题党限流'] },
  { code: 'qiehao', name: '企鹅号', tier: 1, tierLabel: 'AI高优先抓取', aiValue: '腾讯生态，同步腾讯新闻，混元/微信搜一搜AI抓取，与公众号联动', rules: ['医疗内容需审核', '禁止导流私域', '需标注作者身份'] },
  { code: 'sohu', name: '搜狐号', tier: 1, tierLabel: 'AI高优先抓取', aiValue: '全网大模型爬虫（豆包/文心/GPT）高频抓取，文章长期在线，长尾搜索持续生效', rules: ['医疗科普需免责声明', '禁止虚假宣传', '引用需注明出处'] },
  { code: 'wangyi', name: '网易号', tier: 1, tierLabel: 'AI高优先抓取', aiValue: '内容可被全网检索AI收录，适合做科普内容存档', rules: ['医疗内容需资质', '禁止绝对化用语', '需标注审核状态'] },
  // 第二层：医疗垂直平台（医生身份可信度最高）
  { code: 'haodf', name: '好大夫在线', tier: 2, tierLabel: '医疗权威引用', aiValue: '医疗权威源，各大AI医疗问答库优先引用，自带医生主页+医院属地，GEO属性天然强化', rules: ['需医生实名认证', '内容需专业审核', '禁止个人联系方式'] },
  { code: 'dxy', name: '丁香医生/丁香园', tier: 2, tierLabel: '医疗权威引用', aiValue: '专业医疗内容源，垂直医疗知识库抓取，专业受众强', rules: ['需执业医师认证', '内容需同行评议', '禁止商业推广'] },
  { code: 'medlive', name: '医脉通', tier: 2, tierLabel: '医疗权威引用', aiValue: '面向同行+患者科普，专业权重高，AI会将其作为医疗权威参考源', rules: ['需专业资质', '引用指南需标注', '禁止非循证内容'] },
  { code: 'xywy', name: '寻医问药网', tier: 2, tierLabel: '医疗权威引用', aiValue: '老牌健康门户，爬虫收录稳定，适合病种科普发布', rules: ['医疗内容需审核', '禁止处方药推荐', '需免责声明'] },
  // 第三层：论坛类（补充收录）
  { code: 'douban', name: '豆瓣小组', tier: 3, tierLabel: '补充收录', aiValue: '适合轻科普，可带属地信息，全网爬虫抓取，注意不能硬广只能科普', rules: ['禁止硬广', '只能科普', '需符合小组规则'] },
  { code: 'maimai', name: '脉脉', tier: 3, tierLabel: '补充收录', aiValue: '偏行业，但科普内容可被检索抓取，适合专业向内容', rules: ['禁止营销', '需专业身份', '内容需有价值'] },
  // 原有平台保留
  { code: 'wechat', name: '微信公众号', tier: 2, tierLabel: '私域+搜一搜', aiValue: '微信生态，搜一搜AI抓取，私域转化强', rules: ['医疗广告需资质', '禁止诱导分享', '需标注原创'] },
  { code: 'xiaohongshu', name: '小红书', tier: 3, tierLabel: '补充收录', aiValue: '年轻女性用户多，种草型科普，AI抓取率中等', rules: ['禁止医疗广告', '需个人经验分享', '禁止导流'] },
  { code: 'zhihu', name: '知乎', tier: 2, tierLabel: '问答型引用', aiValue: '问答型内容，AI优先引用长文回答，专业权重高', rules: ['需专业认证', '禁止软文', '引用需标注'] },
]

// 兼容旧代码：名称映射
export const PUBLISH_PLATFORM_NAMES: Record<string, string> = Object.fromEntries(
  PUBLISH_PLATFORMS.map(p => [p.code, p.name])
)

// 文章状态映射
export const ARTICLE_STATUS_NAMES: Record<string, string> = {
  draft: '草稿',
  published: '已发布'
}
