import axios from 'axios'
import { message } from 'antd'

const request = axios.create({
  baseURL: '/geo/api/v1',
  timeout: 180000,  // GEO/AEO采集可能需要1-3分钟
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('geo_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
// 友好错误提示映射
const friendlyErrorMap: Record<number, string> = {
  400: '请求参数有误，请检查后重试',
  401: '登录已过期，请重新登录',
  403: '您没有权限执行此操作',
  404: '请求的内容不存在',
  429: '操作太频繁，请稍后再试',
  500: '服务器开小差了，请稍后再试',
  502: '服务器暂时不可用，请稍后再试',
  503: '服务维护中，请稍后再试',
  504: '请求超时，请检查网络后重试',
}

const getFriendlyError = (error: any): string => {
  const status = error.response?.status
  const backendMsg = error.response?.data?.detail || error.response?.data?.message || ''

  // 登录相关错误特殊处理
  if (backendMsg.includes('邮箱或密码') || backendMsg.includes('用户名或密码')) {
    return '邮箱或密码不正确，请检查后重试'
  }
  // 登录接口的401也按密码错误处理
  if (status === 401 && error.config?.url?.includes('/auth/local/login')) {
    return '邮箱或密码不正确，请检查后重试'
  }
  if (backendMsg.includes('未注册')) {
    return '该邮箱尚未注册，请先注册账号'
  }
  if (backendMsg.includes('已注册')) {
    return '该邮箱已被注册，请直接登录'
  }
  if (backendMsg.includes('验证码')) {
    return '验证码错误或已过期，请重新获取'
  }

  // 网络错误
  if (error.message === 'Network Error') {
    return '网络连接失败，请检查网络后重试'
  }
  if (error.message.includes('timeout')) {
    return '请求超时，请检查网络后重试'
  }

  // 按状态码映射
  if (status && friendlyErrorMap[status]) {
    return friendlyErrorMap[status]
  }

  // 默认提示
  return '操作失败，请稍后再试'
}

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code !== 0 && res.code !== undefined && res.code !== 1 && res.code !== 2) {
      const friendlyMsg = getFriendlyError(res)
      message.error(friendlyMsg)
      return Promise.reject(new Error(friendlyMsg))
    }
    return res
  },
  (error) => {
    const friendlyMsg = getFriendlyError(error)
    message.error(friendlyMsg)

    // 401 自动跳转登录页
    if (error.response?.status === 401 && !error.config?.url?.includes('/auth/local/login')) {
      setTimeout(() => {
        localStorage.removeItem('geo_token')
        window.location.href = '/geo/login'
      }, 1500)
    }

    return Promise.reject(error)
  }
)

// ============ 仪表盘 API ============
export const dashboardApi = {
  getStats: () => request.get('/dashboard/stats'),
  getDoctorStats: () => request.get('/dashboard/doctor-stats'),
}

// ============ GEO/AEO数据 API ============
export const geoApi = {
  getOverview: () => request.get('/geo/overview'),
  getSemanticDetail: (id: number, days = 7) => request.get(`/geo/semantic/${id}`, { params: { days } }),
  getTrend: (days = 7) => request.get('/geo/trend', { params: { days } }),
  refresh: () => request.post('/geo/refresh'),
}

// ============ 监测中心 API ============
export const monitorApi = {
  getQuestions: (params?: any) => request.get('/monitor/questions', { params }),
  createQuestion: (data: any) => request.post('/monitor/questions', data),
  updateQuestion: (id: number, data: any) => request.put(`/monitor/questions/${id}`, data),
  deleteQuestion: (id: number) => request.delete(`/monitor/questions/${id}`),
  getRecords: (params?: any) => request.get('/monitor/records', { params }),
  getMatrix: (date?: string) => request.get('/monitor/matrix', { params: { date } }),
  getTrend: (id: number, params?: any) => request.get(`/monitor/trend/${id}`, { params }),
  collect: (data: any) => request.post('/monitor/collect', data)
}

// ============ 内容资产 API ============
export const contentApi = {
  getList: (params?: any) => request.get('/content', { params }),
  create: (data: any) => request.post('/content', data),
  getDetail: (id: number) => request.get(`/content/${id}`),
  delete: (id: number) => request.delete(`/content/${id}`)
}

// ============ 知识库 API ============
export const knowledgeApi = {
  getList: (params?: any) => request.get('/knowledge', { params }),
  create: (data: any) => request.post('/knowledge', data),
  update: (id: number, data: any) => request.put(`/knowledge/${id}`, data),
  delete: (id: number) => request.delete(`/knowledge/${id}`),
  search: (query: string, level = 'public') =>
    request.post('/knowledge/search', null, { params: { query, level } }),
  rebuildEmbeddings: () => request.post('/knowledge/rebuild-embeddings')
}

// ============ 竞品 API ============
export const competitorApi = {
  getList: (params?: any) => request.get('/competitor', { params }),
  create: (data: any) => request.post('/competitor', data),
  delete: (id: number) => request.delete(`/competitor/${id}`),
  getRecords: (params?: any) => request.get('/competitor/records', { params })
}

// ============ RAG问答 API ============
export const ragApi = {
  query: (data: any) => request.post('/rag/query', data),
  getPlatforms: () => request.get('/rag/platforms')
}

// ============ 系统 API ============
export const systemApi = {
  getInfo: () => request.get('/system/info'),
  getPlatforms: () => request.get('/system/platforms'),
  initDemo: () => request.post('/system/init-demo')
}

// ============ 数据导出 API ============
// 导出是文件下载，需要单独处理（blob响应类型，不走统一拦截器）
const downloadFile = (url: string, filename: string) => {
  return request.get(url, {
    responseType: 'blob',
    timeout: 120000
  }).then((blob: any) => {
    const file = new Blob([blob], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(file)
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(link.href)
    message.success('导出成功')
  }).catch(() => {
    message.error('导出失败')
  })
}

export const exportApi = {
  exportMonitor: (questionId?: number) => {
    const params = questionId ? `?question_id=${questionId}` : ''
    return downloadFile(`/export/monitor${params}`, `监测记录_${Date.now()}.xlsx`)
  },
  exportQuestions: () => downloadFile('/export/questions', `监测问题_${Date.now()}.xlsx`),
  exportKnowledge: () => downloadFile('/export/knowledge', `知识库_${Date.now()}.xlsx`),
  exportContent: () => downloadFile('/export/content', `内容资产_${Date.now()}.xlsx`),
  exportReport: () => downloadFile('/export/report', `GEO完整报告_${Date.now()}.xlsx`),
  exportDoctorReport: () => downloadFile('/export/doctor-report', `GEO医生报告_${Date.now()}.xlsx`),
}

// ============ 认证 API ============
export const authApi = {
  getIamUrl: () => request.get('/auth/iam/url'),
  exchangeTicket: (ticket: string) => request.post('/auth/iam/exchange', null, { params: { ticket } }),
  getUserinfo: (token: string) => request.get('/auth/userinfo', {
    headers: { Authorization: `Bearer ${token}` }
  }),
  logout: () => request.post('/auth/logout'),
  getIamStatus: () => request.get('/auth/status')
}

// ============ 医生Profile API ============
export const doctorApi = {
  getProfile: () => request.get('/doctor/profile'),
  saveProfile: (data: any) => request.post('/doctor/profile', data),
  regenerateSemantics: () => request.post('/doctor/regenerate-semantics'),
}

// ============ 语义库 API ============
export const semanticApi = {
  getList: (params?: any) => request.get('/semantic', { params }),
  toggle: (id: number) => request.post(`/semantic/${id}/toggle`),
  addPaid: (question: string) => request.post('/semantic/add-paid', null, { params: { question } }),
  extend: (id: number) => request.post(`/semantic/${id}/extend`),
  extendBatch: () => request.post('/semantic/extend-batch'),
  saveExtended: (data: { questions: string[]; parent_id: number; extend_type: string }) =>
    request.post('/semantic/extend/save', data),
}

// ============ 文章管理 API ============
export const articleApi = {
  getList: (params?: any) => request.get('/article', { params }),
  create: (data: any) => request.post('/article', data),
  getDetail: (id: number) => request.get(`/article/${id}`),
  update: (id: number, data: any) => request.put(`/article/${id}`, data),
  delete: (id: number) => request.delete(`/article/${id}`),
  validate: (id: number) => request.post(`/article/${id}/validate`),
}

// ============ 实体一致性 API ============
export const entityApi = {
  getProfileScore: () => request.get('/entity/profile-score'),
}

// ============ 文章模板 API ============
export const templateApi = {
  generateArticle: (semanticId: number, opportunityId?: number) =>
    request.post(`/template/article/${semanticId}`, null, { params: opportunityId ? { opportunity_id: opportunityId } : {} }),
  generateLlms: () => request.get('/template/llms.txt', { responseType: 'text' }),
}

// ============ 文章分发 API ============
export const distributionApi = {
  getList: (params?: any) => request.get('/distribution', { params }),
  create: (data: any) => request.post('/distribution', data),
  updateStatus: (id: number, data: { status: string; publish_url?: string; note?: string }) =>
    request.patch(`/distribution/${id}/status`, data),
  retry: (id: number) => request.post(`/distribution/${id}/retry`),
  delete: (id: number) => request.delete(`/distribution/${id}`),
  getEffect: (id: number) => request.get(`/distribution/${id}/effect`),
  recollect: (id: number) => request.post(`/distribution/${id}/recollect`),
}

// ============ 工具配置 API ============
export const toolsApi = {
  getConfig: () => request.get('/tools/config'),
}

// ============ 异步任务 API ============
export const taskApi = {
  get: (id: number) => request.get(`/task/${id}`),
  list: (params?: { task_type?: string; status?: string; page?: number; page_size?: number }) =>
    request.get('/task', { params }),
  cancel: (id: number) => request.post(`/task/${id}/cancel`),
}

// ============ 内容机会 API ============
export const opportunityApi = {
  list: (params?: { status?: string; opportunity_type?: string }) =>
    request.get('/opportunity', { params }),
  scan: () => request.post('/opportunity/scan'),
  dismiss: (id: number) => request.post(`/opportunity/${id}/dismiss`),
}


// ============ 本地账号认证 API（邮箱注册/登录） ============
export const localAuthApi = {
  checkEmail: (email: string) =>
    request.get('/auth/local/check-email', { params: { email } }),
  sendCode: (email: string, type: 'register' | 'reset' = 'register') =>
    request.post('/auth/local/send-code', { email, type }),
  register: (email: string, code: string, password: string, username?: string) =>
    request.post('/auth/local/register', { email, code, password, username }),
  login: (email: string, password: string) =>
    request.post('/auth/local/login', { email, password }),
  resetPassword: (email: string, code: string, new_password: string) =>
    request.post('/auth/local/reset-password', { email, code, new_password }),
  changePassword: (old_password: string, new_password: string) =>
    request.post('/auth/local/change-password', { old_password, new_password }),
}

export const usageApi = {
  getOverview: (days: number) => request.get('/usage/overview', { params: { days } }),
  getTrend: (days: number) => request.get('/usage/trend', { params: { days } }),
  getByTaskType: (days: number) => request.get('/usage/by-task-type', { params: { days } }),
  getByPlatform: (days: number) => request.get('/usage/by-platform', { params: { days } }),
  getByUser: (days: number, limit: number) => request.get('/usage/by-user', { params: { days, limit } }),
  getLogs: (params: any) => request.get('/usage/logs', { params }),
}

// 用量治理：平台开关 + 配额
export const usageGovernanceApi = {
  getAvailablePlatforms: () => request.get('/usage/platforms/available'),
  getMyPref: () => request.get('/usage/platforms/pref'),
  updatePref: (platform_code: string, enabled: boolean) =>
    request.put('/usage/platforms/pref', { platform_code, enabled }),
  getMyQuota: () => request.get('/usage/quota/my'),
  adminListUsersQuota: () => request.get('/usage/quota/admin/users'),
  adminUpdateQuota: (user_id: number, monthly_cost_limit: number) =>
    request.put(`/usage/quota/admin/${user_id}`, { monthly_cost_limit }),
  adminUsageReport: () => request.get('/usage/admin/user-platform'),
  adminListUsers: () => request.get('/usage/admin/users'),
  adminChangeRole: (user_id: number, role: string) =>
    request.put(`/usage/admin/users/${user_id}/role`, { role }),
}

export const platformsApi = {
  getList: () => request.get('/platforms'),
  getDetail: (code: string) => request.get(`/platforms/${code}`),
  create: (data: any) => request.post('/platforms', data),
  update: (code: string, data: any) => request.put(`/platforms/${code}`, data),
  delete: (code: string) => request.delete(`/platforms/${code}`),
  toggle: (code: string) => request.post(`/platforms/${code}/toggle`),
  test: (data: any) => request.post('/platforms/test', data),
  reload: () => request.post('/platforms/reload'),
}

export default request







