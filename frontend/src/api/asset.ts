import request from './index'

// ============ 数字资产 API ============

export const assetApi = {
  // ===== 资产源 CRUD =====
  getSources: (params?: {
    source_type?: string
    category?: string
    status?: string
    keyword?: string
    page?: number
    page_size?: number
  }) => request.get('/asset/sources', { params }),

  createSource: (data: {
    source_type?: string
    title?: string
    url?: string
    source_site?: string
    content?: string
    category?: string
    tags?: string
  }) => request.post('/asset/sources', data),

  getSourceDetail: (id: number) => request.get(`/asset/sources/${id}`),

  updateSource: (id: number, data: {
    title?: string
    category?: string
    tags?: string
  }) => request.put(`/asset/sources/${id}`, data),

  deleteSource: (id: number) => request.delete(`/asset/sources/${id}`),

  // ===== 笔记管理 =====
  createNote: (data: {
    document_id: number
    title?: string
    content?: string
    note_type?: string
  }) => request.post('/asset/notes', data),

  updateNote: (id: number, data: {
    title?: string
    content?: string
    note_type?: string
  }) => request.put(`/asset/notes/${id}`, data),

  deleteNote: (id: number) => request.delete(`/asset/notes/${id}`),

  // ===== AI 总结 =====
  generateSummary: (data: {
    document_id: number
    platform?: string
    prompt_template?: string
    custom_prompt?: string
  }) => request.post('/asset/summary', data),

  getSummaryHistory: (documentId: number) =>
    request.get(`/asset/summary/history/${documentId}`),

  getPromptTemplates: () => request.get('/asset/summary/templates'),

  // ===== 搜索与 RAG =====
  search: (q: string, top_k: number = 10) =>
    request.get('/asset/search', { params: { q, top_k } }),

  ragQuery: (data: {
    question: string
    platform?: string
    top_k?: number
    history?: Array<{ role: string; content: string }>
  }) => request.post('/asset/rag', data),

  // ===== 多模型对话 =====
  getChatModels: () => request.get('/asset/chat/models'),

  getChatTemplates: () => request.get('/asset/chat/templates'),

  getChatSessions: (documentId?: number, keyword?: string) =>
    request.get('/asset/chat/sessions', { params: { document_id: documentId, keyword } }),

  createChatSession: (data?: { document_id?: number; platform?: string }) =>
    request.post('/asset/chat/sessions', null, { params: data }),

  getChatMessages: (sessionId: number) =>
    request.get(`/asset/chat/sessions/${sessionId}/messages`),

  deleteChatSession: (sessionId: number) =>
    request.delete(`/asset/chat/sessions/${sessionId}`),

  renameChatSession: (sessionId: number, title: string) =>
    request.put(`/asset/chat/sessions/${sessionId}`, null, { params: { title } }),

  sendChatMessage: (data: {
    session_id?: number
    document_id?: number
    message: string
    platform?: string
    top_k?: number
  }) => request.post('/asset/chat/send', data),

  compareChatModels: (data: {
    message: string
    platforms: string[]
    document_id?: number
    top_k?: number
  }) => request.post('/asset/chat/compare', data),

  // ===== PubMed 文献导入 =====
  searchPubMed: (query: string, maxResults: number = 10) =>
    request.post('/asset/pubmed/search', { query, max_results: maxResults }),

  importPubMed: (pmid: string, category?: string, tags?: string) =>
    request.post('/asset/pubmed/import', { pmid, category, tags }),

  batchImportPubMed: (pmids: string[], category?: string) =>
    request.post('/asset/pubmed/batch-import', { pmids, category }),

  // ===== GEO发布 =====
  publishFromDocument: (data: {
    document_id: number
    title?: string
    platform?: string
    category?: string
    tags?: string
    auto_rewrite?: boolean
  }) => request.post('/asset/publish/from-document', data),

  getPublishedList: (params?: {
    status?: string
    category?: string
    keyword?: string
  }) => request.get('/asset/publish/list', { params }),

  getPublishedDetail: (id: number) =>
    request.get(`/asset/publish/${id}`),

  createPublished: (data: {
    title: string
    content: string
    summary?: string
    category?: string
    tags?: string
    keywords?: string
  }) => request.post('/asset/publish', data),

  updatePublished: (id: number, data: {
    title?: string
    content?: string
    summary?: string
    category?: string
    tags?: string
    keywords?: string
    status?: string
  }) => request.put(`/asset/publish/${id}`, data),

  deletePublished: (id: number) =>
    request.delete(`/asset/publish/${id}`),

  // ===== 内容导出 =====
  exportDocument: (data: {
    document_id: number
    format: 'md' | 'html' | 'pdf'
  }) => request.post('/asset/export/document', data, {
    responseType: 'blob',
  }),

  // ===== 文件夹管理 =====
  getFolderTree: () => request.get('/asset/folders/tree'),

  createFolder: (data: { name: string; parent_id?: number }) =>
    request.post('/asset/folders', data),

  updateFolder: (id: number, data: { name?: string }) =>
    request.put(`/asset/folders/${id}`, data),

  deleteFolder: (id: number) =>
    request.delete(`/asset/folders/${id}`),

  moveToFolder: (data: { source_ids: number[]; folder_id?: number | null }) =>
    request.post('/asset/folders/move', data),

  toggleStar: (sourceId: number) =>
    request.post(`/asset/sources/${sourceId}/star`),

  updateReadStatus: (sourceId: number, status: 'unread' | 'reading' | 'read') =>
    request.post(`/asset/sources/${sourceId}/read-status?status=${status}`),
}

