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
request.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code !== 0 && res.code !== undefined) {
      message.error(res.message || '请求失败')
      return Promise.reject(new Error(res.message || '请求失败'))
    }
    return res
  },
  (error) => {
    const msg = error.response?.data?.message || error.message || '网络错误'
    message.error(msg)
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
  return axios.get(`/api/v1${url}`, {
    responseType: 'blob',
    timeout: 120000
  }).then((response) => {
    const blob = new Blob([response.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
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
  getUserinfo: (token: string) => axios.get('/api/v1/auth/userinfo', {
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
    request.get(`/template/article/${semanticId}`, { params: opportunityId ? { opportunity_id: opportunityId } : {} }),
  generateLlms: () => request.get('/template/llms.txt', { responseType: 'text' }),
}

// ============ 文章分发 API ============
export const distributionApi = {
  getList: (params?: any) => request.get('/distribution', { params }),
  create: (data: any) => request.post('/distribution', data),
  delete: (id: number) => request.delete(`/distribution/${id}`),
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

export default request
