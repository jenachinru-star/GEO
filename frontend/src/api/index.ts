import axios from 'axios'
import { message } from 'antd'

const request = axios.create({
  baseURL: '/geo/api/v1',
  timeout: 180000,  // GEO/AEO閲囬泦鍙兘闇€瑕?-3鍒嗛挓
  headers: {
    'Content-Type': 'application/json'
  }
})

// 璇锋眰鎷︽埅鍣?
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

// 鍝嶅簲鎷︽埅鍣?
request.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code !== 0 && res.code !== undefined) {
      message.error(res.message || '璇锋眰澶辫触')
      return Promise.reject(new Error(res.message || '璇锋眰澶辫触'))
    }
    return res
  },
  (error) => {
    const msg = error.response?.data?.message || error.message || '缃戠粶閿欒'
    message.error(msg)
    return Promise.reject(error)
  }
)

// ============ 浠〃鐩?API ============
export const dashboardApi = {
  getStats: () => request.get('/dashboard/stats'),
  getDoctorStats: () => request.get('/dashboard/doctor-stats'),
}

// ============ GEO/AEO鏁版嵁 API ============
export const geoApi = {
  getOverview: () => request.get('/geo/overview'),
  getSemanticDetail: (id: number, days = 7) => request.get(`/geo/semantic/${id}`, { params: { days } }),
  getTrend: (days = 7) => request.get('/geo/trend', { params: { days } }),
  refresh: () => request.post('/geo/refresh'),
}

// ============ 鐩戞祴涓績 API ============
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

// ============ 鍐呭璧勪骇 API ============
export const contentApi = {
  getList: (params?: any) => request.get('/content', { params }),
  create: (data: any) => request.post('/content', data),
  getDetail: (id: number) => request.get(`/content/${id}`),
  delete: (id: number) => request.delete(`/content/${id}`)
}

// ============ 鐭ヨ瘑搴?API ============
export const knowledgeApi = {
  getList: (params?: any) => request.get('/knowledge', { params }),
  create: (data: any) => request.post('/knowledge', data),
  update: (id: number, data: any) => request.put(`/knowledge/${id}`, data),
  delete: (id: number) => request.delete(`/knowledge/${id}`),
  search: (query: string, level = 'public') =>
    request.post('/knowledge/search', null, { params: { query, level } }),
  rebuildEmbeddings: () => request.post('/knowledge/rebuild-embeddings')
}

// ============ 绔炲搧 API ============
export const competitorApi = {
  getList: (params?: any) => request.get('/competitor', { params }),
  create: (data: any) => request.post('/competitor', data),
  delete: (id: number) => request.delete(`/competitor/${id}`),
  getRecords: (params?: any) => request.get('/competitor/records', { params })
}

// ============ RAG闂瓟 API ============
export const ragApi = {
  query: (data: any) => request.post('/rag/query', data),
  getPlatforms: () => request.get('/rag/platforms')
}

// ============ 绯荤粺 API ============
export const systemApi = {
  getInfo: () => request.get('/system/info'),
  getPlatforms: () => request.get('/system/platforms'),
  initDemo: () => request.post('/system/init-demo')
}

// ============ 鏁版嵁瀵煎嚭 API ============
// 瀵煎嚭鏄枃浠朵笅杞斤紝闇€瑕佸崟鐙鐞嗭紙blob鍝嶅簲绫诲瀷锛屼笉璧扮粺涓€鎷︽埅鍣級
const downloadFile = (url: string, filename: string) => {
  return axios.get(`/geo/api/v1${url}`, {
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
    message.success('瀵煎嚭鎴愬姛')
  }).catch(() => {
    message.error('瀵煎嚭澶辫触')
  })
}

export const exportApi = {
  exportMonitor: (questionId?: number) => {
    const params = questionId ? `?question_id=${questionId}` : ''
    return downloadFile(`/export/monitor${params}`, `鐩戞祴璁板綍_${Date.now()}.xlsx`)
  },
  exportQuestions: () => downloadFile('/export/questions', `鐩戞祴闂_${Date.now()}.xlsx`),
  exportKnowledge: () => downloadFile('/export/knowledge', `鐭ヨ瘑搴揰${Date.now()}.xlsx`),
  exportContent: () => downloadFile('/export/content', `鍐呭璧勪骇_${Date.now()}.xlsx`),
  exportReport: () => downloadFile('/export/report', `GEO瀹屾暣鎶ュ憡_${Date.now()}.xlsx`),
  exportDoctorReport: () => downloadFile('/export/doctor-report', `GEO鍖荤敓鎶ュ憡_${Date.now()}.xlsx`),
}

// ============ 璁よ瘉 API ============
export const authApi = {
  getIamUrl: () => request.get('/auth/iam/url'),
  exchangeTicket: (ticket: string) => request.post('/auth/iam/exchange', null, { params: { ticket } }),
  getUserinfo: (token: string) => request.get('/auth/userinfo', {
    headers: { Authorization: `Bearer ${token}` }
  }),
  logout: () => request.post('/auth/logout'),
  getIamStatus: () => request.get('/auth/status')
}

// ============ 鍖荤敓Profile API ============
export const doctorApi = {
  getProfile: () => request.get('/doctor/profile'),
  saveProfile: (data: any) => request.post('/doctor/profile', data),
  regenerateSemantics: () => request.post('/doctor/regenerate-semantics'),
}

// ============ 璇箟搴?API ============
export const semanticApi = {
  getList: (params?: any) => request.get('/semantic', { params }),
  toggle: (id: number) => request.post(`/semantic/${id}/toggle`),
  addPaid: (question: string) => request.post('/semantic/add-paid', null, { params: { question } }),
  extend: (id: number) => request.post(`/semantic/${id}/extend`),
  extendBatch: () => request.post('/semantic/extend-batch'),
  saveExtended: (data: { questions: string[]; parent_id: number; extend_type: string }) =>
    request.post('/semantic/extend/save', data),
}

// ============ 鏂囩珷绠＄悊 API ============
export const articleApi = {
  getList: (params?: any) => request.get('/article', { params }),
  create: (data: any) => request.post('/article', data),
  getDetail: (id: number) => request.get(`/article/${id}`),
  update: (id: number, data: any) => request.put(`/article/${id}`, data),
  delete: (id: number) => request.delete(`/article/${id}`),
  validate: (id: number) => request.post(`/article/${id}/validate`),
}

// ============ 瀹炰綋涓€鑷存€?API ============
export const entityApi = {
  getProfileScore: () => request.get('/entity/profile-score'),
}

// ============ 鏂囩珷妯℃澘 API ============
export const templateApi = {
  generateArticle: (semanticId: number, opportunityId?: number) =>
    request.get(`/template/article/${semanticId}`, { params: opportunityId ? { opportunity_id: opportunityId } : {} }),
  generateLlms: () => request.get('/template/llms.txt', { responseType: 'text' }),
}

// ============ 鏂囩珷鍒嗗彂 API ============
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

// ============ 宸ュ叿閰嶇疆 API ============
export const toolsApi = {
  getConfig: () => request.get('/tools/config'),
}

// ============ 寮傛浠诲姟 API ============
export const taskApi = {
  get: (id: number) => request.get(`/task/${id}`),
  list: (params?: { task_type?: string; status?: string; page?: number; page_size?: number }) =>
    request.get('/task', { params }),
  cancel: (id: number) => request.post(`/task/${id}/cancel`),
}

// ============ 鍐呭鏈轰細 API ============
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

export default request


