import { useState, useEffect, useRef } from 'react'
import { Card, Input, Button, Space, Typography, Tag, Empty, Spin, Pagination, Modal, Form, Upload, message, Tabs, Divider, Layout, Tree, Popconfirm } from 'antd'
import { PlusOutlined, SearchOutlined, LinkOutlined, FileTextOutlined, BookOutlined, UploadOutlined, LoadingOutlined, FolderOutlined, StarOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { assetApi } from '@/api/asset'
import { formatUtcDate } from '@/utils/time'

const { Sider } = Layout
const { Title, Text } = Typography
const { TextArea } = Input

const AssetHub = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [keyword, setKeyword] = useState('')

  // 文件夹和标签
  const [folderTree, setFolderTree] = useState<any[]>([])
  const [tags, setTags] = useState<any[]>([])
  const [selectedFolder, setSelectedFolder] = useState<string | number>('all')
  const [selectedTag, setSelectedTag] = useState<number | null>(null)

  // 用ref保存最新的items，避免useEffect无限循环
  const itemsRef = useRef<any[]>([])
  itemsRef.current = items

  // 模态框状态
  const [modalOpen, setModalOpen] = useState(false)
  const [modalTab, setModalTab] = useState('url')
  const [submitting, setSubmitting] = useState(false)

  // 表单
  const [urlForm] = Form.useForm()
  const [manualForm] = Form.useForm()

  // PubMed导入状态
  const [pmidInput, setPmidInput] = useState('')
  const [pubmedSearchQuery, setPubmedSearchQuery] = useState('')
  const [pubmedResults, setPubmedResults] = useState<any[]>([])
  const [pubmedSearching, setPubmedSearching] = useState(false)
  const [importingPmid, setImportingPmid] = useState<string | null>(null)

  const fetchData = async (pageNum = 1, kw = '') => {
    setLoading(true)
    try {
      const params: any = {
        page: pageNum,
        page_size: 20,
        keyword: kw || undefined,
      }
      // 文件夹筛选
      if (selectedFolder !== 'all') {
        params.folder_id = selectedFolder
      }
      // 标签筛选
      if (selectedTag) {
        params.tag_id = selectedTag
      }
      const res: any = await assetApi.getSources(params)
      setItems(res.data.items || [])
      setTotal(res.data.total || 0)
      setPage(pageNum)
    } catch (e) {
      message.error('加载失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchFolders = async () => {
    try {
      const res: any = await assetApi.getFolderTree()
      setFolderTree(res.data.folders || [])
    } catch (e) {
      // 静默失败
    }
  }

  const fetchTags = async () => {
    try {
      const res: any = await assetApi.getTags()
      setTags(res.data.tags || [])
    } catch (e) {
      // 静默失败
    }
  }

  useEffect(() => {
    fetchData()
    // 每10秒轮询一次，更新处理中的任务状态
    const timer = setInterval(() => {
      const hasProcessing = itemsRef.current.some(i => i.status === 'pending' || i.status === 'processing')
      if (hasProcessing) {
        fetchData(page, keyword)
      }
    }, 10000)
    return () => clearInterval(timer)
  }, [page, keyword, selectedFolder, selectedTag])

  const handleSearch = () => {
    fetchData(1, keyword)
  }

  const handleAddUrl = () => {
    setModalOpen(true)
    setModalTab('url')
  }

  const handleSubmitUrl = async (forceRefresh = false) => {
    try {
      const values = await urlForm.validateFields()
      setSubmitting(true)
      const res: any = await assetApi.createSource({
        source_type: 'url',
        url: values.url,
        title: values.title || '',
        force_refresh: forceRefresh,
      })
      if (res.code === 1) {
        // 已采集完成，弹确认框
        Modal.confirm({
          title: '该URL已采集',
          content: res.message,
          okText: '重新采集',
          cancelText: '取消',
          onOk: () => handleSubmitUrl(true),
        })
        return
      }
      if (res.code === 2) {
        message.warning(res.message)
        return
      }
      message.success(res.message || '已提交，正在后台采集网页内容')
      setModalOpen(false)
      urlForm.resetFields()
      fetchData()
    } catch (e) {
      // 错误已在拦截器提示
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation()
    Modal.confirm({
      title: '确认删除',
      content: '删除后该资产及其所有版本、笔记将被移除，已发布的内容不受影响。',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await assetApi.deleteSource(id)
          message.success('已删除')
          fetchData()
        } catch (e) {
          message.error('删除失败')
        }
      },
    })
  }

  const handleRetry = async (id: number, url: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      const res: any = await assetApi.createSource({
        source_type: 'url',
        url: url,
        force_refresh: true,
      })
      message.success(res.message || '已重新提交采集')
      fetchData()
    } catch (e) {
      message.error('重试失败')
    }
  }

  const handlePubmedSearch = async () => {
    if (!pubmedSearchQuery.trim()) {
      message.warning('请输入搜索关键词')
      return
    }
    setPubmedSearching(true)
    try {
      const res: any = await assetApi.searchPubMed(pubmedSearchQuery, 10)
      setPubmedResults(res.data.papers || [])
    } catch (e) {
      message.error('PubMed搜索失败')
    } finally {
      setPubmedSearching(false)
    }
  }

  const handleSubmitManual = async () => {
    try {
      const values = await manualForm.validateFields()
      setSubmitting(true)
      await assetApi.createSource({
        source_type: 'manual',
        title: values.title || '未命名文档',
        content: values.content,
      })
      message.success('已保存')
      setModalOpen(false)
      manualForm.resetFields()
      fetchData()
    } catch (e) {
      // 错误已在拦截器提示
    } finally {
      setSubmitting(false)
    }
  }

  const handleFileUpload = async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    try {
      setSubmitting(true)
      // 直接用axios上传
      const { default: request } = await import('@/api/index')
      await request.post('/asset/sources/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      message.success('文件已上传，正在后台解析')
      setModalOpen(false)
      fetchData()
    } catch (e) {
      message.error('上传失败')
    } finally {
      setSubmitting(false)
    }
    return false // 阻止自动上传
  }

  const handleCardClick = (id: number, status: string) => {
    navigate(`/asset/${id}`)
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'url': return <LinkOutlined />
      case 'file': return <FileTextOutlined />
      default: return <BookOutlined />
    }
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'url': return 'blue'
      case 'file': return 'green'
      default: return 'default'
    }
  }

  // 把文件夹树转成AntD Tree需要的格式
  const buildTreeData = (folders: any[]) => {
    const result: any[] = [
      { key: 'all', title: '全部资产', icon: <FolderOutlined /> },
      { key: 'starred', title: '星标收藏', icon: <StarOutlined /> },
    ]
    if (folders.length > 0) {
      result.push({
        key: 'divider',
        title: '文件夹',
        selectable: false,
        children: folders.map((f: any) => ({
          key: f.id,
          title: f.name,
          children: f.children?.map((c: any) => ({
            key: c.id,
            title: c.name,
          })),
        })),
      })
    }
    return result
  }

  return (
    <Layout style={{ minHeight: 'calc(100vh - 64px)', background: '#fff' }}>
      {/* 左侧边栏：文件夹树 + 标签云 */}
      <Sider width={220} style={{ background: '#fff', borderRight: '1px solid #f0f0f0', padding: '16px 0' }}>
        {/* 文件夹树 */}
        <div style={{ padding: '0 16px', marginBottom: 16 }}>
          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>文件夹</Text>
          <Tree
            treeData={buildTreeData(folderTree)}
            selectedKeys={[selectedFolder]}
            onSelect={(keys) => {
              if (keys.length > 0) {
                setSelectedFolder(keys[0] as any)
                setSelectedTag(null)
              }
            }}
            defaultExpandAll
          />
        </div>

        {/* 标签云 */}
        <div style={{ padding: '0 16px', borderTop: '1px solid #f0f0f0', paddingTop: 16 }}>
          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>标签</Text>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {tags.length === 0 ? (
              <Text type="secondary" style={{ fontSize: 12 }}>暂无标签</Text>
            ) : (
              tags.map((tag: any) => (
                <Tag
                  key={tag.id}
                  color={selectedTag === tag.id ? tag.color : 'default'}
                  style={{ cursor: 'pointer', margin: 0 }}
                  onClick={() => {
                    if (selectedTag === tag.id) {
                      setSelectedTag(null)
                    } else {
                      setSelectedTag(tag.id)
                      setSelectedFolder('all')
                    }
                  }}
                >
                  {tag.name} ({tag.count})
                </Tag>
              ))
            )}
          </div>
        </div>
      </Sider>

      {/* 右侧主内容区 */}
      <div style={{ padding: '24px', flex: 1 }}>
        {/* 顶部标题栏 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <div>
            <Title level={3} style={{ margin: 0 }}>数字资产库</Title>
            <Text type="secondary">收藏文章、文献、网页，沉淀您的个人知识资产</Text>
          </div>
          <Space>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAddUrl}>
              添加资产
            </Button>
          </Space>
        </div>

        {/* 搜索栏 */}
        <Card size="small" style={{ marginBottom: 16 }}>
          <Space style={{ width: '100%' }}>
            <Input
              placeholder="搜索标题、标签、URL..."
              prefix={<SearchOutlined />}
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onPressEnter={handleSearch}
              style={{ maxWidth: 400 }}
            />
            <Button type="primary" onClick={handleSearch}>搜索</Button>
          </Space>
        </Card>

        {/* 资产列表 */}
        <Spin spinning={loading}>
          {items.length === 0 ? (
            <Card>
              <Empty
                description="还没有收藏任何内容"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              >
                <p style={{ color: '#999', marginBottom: 16 }}>
                  开始收藏您关注的文章、文献和网页，打造您的个人数字资产库
                </p>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleAddUrl}>
                  添加第一个资产
                </Button>
              </Empty>
            </Card>
          ) : (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 16 }}>
                {items.map((item) => (
                  <Card
                    key={item.id}
                    hoverable
                    size="small"
                    onClick={() => handleCardClick(item.id, item.status)}
                    style={{ height: 180 }}
                  >
                    <div style={{ marginBottom: 8 }}>
                      <Tag color={getTypeColor(item.source_type)} icon={getTypeIcon(item.source_type)}>
                        {item.source_type}
                      </Tag>
                      {item.category && <Tag>{item.category}</Tag>}
                      {item.status === 'processing' && (
                        <Tag icon={<LoadingOutlined />} color="orange">解析中</Tag>
                      )}
                    </div>
                    <div style={{
                      fontSize: 14,
                      fontWeight: 500,
                      marginBottom: 8,
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                    }}>
                      {item.title || '未命名'}
                    </div>
                    {item.url && (
                      <Text type="secondary" style={{
                        fontSize: 12,
                        display: 'block',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}>
                        {item.url}
                      </Text>
                    )}
                    <div style={{ marginTop: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {item.updated_at ? formatUtcDate(item.updated_at) : ''}
                      </Text>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        {item.status === 'failed' && (
                          <Button type="link" size="small" style={{ padding: 0, fontSize: 12 }} onClick={(e) => handleRetry(item.id, item.url, e)}>
                            重试
                          </Button>
                        )}
                        <Button type="link" size="small" danger style={{ padding: 0, fontSize: 12 }} onClick={(e) => handleDelete(item.id, e)}>
                          删除
                        </Button>
                        <Tag color={item.status === 'completed' ? 'green' : item.status === 'failed' ? 'red' : 'orange'}>
                          {item.status}
                        </Tag>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
              {total > 20 && (
                <div style={{ textAlign: 'center', marginTop: 24 }}>
                  <Pagination
                    current={page}
                    total={total}
                    pageSize={20}
                    onChange={(p) => fetchData(p, keyword)}
                  />
                </div>
              )}
            </>
          )}
        </Spin>

        {/* 添加资产模态框 */}
        <Modal
          title="添加数字资产"
          open={modalOpen}
          onCancel={() => setModalOpen(false)}
          footer={null}
          width={600}
        >
          <Tabs
            activeKey={modalTab}
            onChange={setModalTab}
            items={[
              {
                key: 'url',
                label: '收藏网页',
                children: (
                  <Form form={urlForm} layout="vertical">
                    <Form.Item
                      name="url"
                      label="网页URL"
                      rules={[
                        { required: true, message: '请输入网页URL' },
                        { type: 'url', message: '请输入正确的URL格式' },
                      ]}
                    >
                      <Input placeholder="https://example.com/article/123" />
                    </Form.Item>
                    <Form.Item name="title" label="自定义标题（可选）">
                      <Input placeholder="留空则自动提取网页标题" />
                    </Form.Item>
                    <Button
                      type="primary"
                      block
                      loading={submitting}
                      onClick={() => handleSubmitUrl()}
                      style={{ marginTop: 8 }}
                    >
                      收藏并自动解析
                    </Button>
                  </Form>
                ),
              },
              {
                key: 'file',
                label: '上传文件',
                children: (
                  <div>
                    <Upload.Dragger
                      accept=".txt,.md,.markdown,.pdf,.doc,.docx"
                      beforeUpload={handleFileUpload}
                      showUploadList={false}
                      maxCount={1}
                    >
                      <p style={{ fontSize: 40, color: '#1677ff', margin: '24px 0' }}>
                        <UploadOutlined />
                      </p>
                      <p>点击或拖拽文件到此处上传</p>
                      <p style={{ color: '#999', fontSize: 12 }}>
                        支持 TXT / MD / PDF / Word，最大 20MB
                      </p>
                    </Upload.Dragger>
                  </div>
                ),
              },
              {
                key: 'manual',
                label: '手动记录',
                children: (
                  <Form form={manualForm} layout="vertical">
                    <Form.Item name="title" label="标题">
                      <Input placeholder="文档标题" />
                    </Form.Item>
                    <Form.Item
                      name="content"
                      label="内容"
                      rules={[{ required: true, message: '请输入内容' }]}
                    >
                      <TextArea rows={8} placeholder="粘贴或输入您想记录的内容..." />
                    </Form.Item>
                    <Button
                      type="primary"
                      block
                      loading={submitting}
                      onClick={handleSubmitManual}
                    >
                      保存
                    </Button>
                  </Form>
                ),
              },
              {
                key: 'pubmed',
                label: 'PubMed文献',
                children: (
                  <div>
                    <div style={{ marginBottom: 16 }}>
                      <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 8 }}>
                        方式一：按PMID导入
                      </Text>
                      <Space.Compact style={{ width: '100%' }}>
                        <Input
                          placeholder="输入PMID，如: 37212345"
                          value={pmidInput}
                          onChange={(e) => setPmidInput(e.target.value)}
                        />
                        <Button
                          type="primary"
                          loading={submitting}
                          onClick={async () => {
                            if (!pmidInput.trim()) {
                              message.warning('请输入PMID')
                              return
                            }
                            setSubmitting(true)
                            try {
                              await assetApi.importPubMed(pmidInput.trim())
                              message.success('导入成功')
                              setPmidInput('')
                              setModalOpen(false)
                              fetchData()
                            } catch (e) {
                              message.error('导入失败')
                            } finally {
                              setSubmitting(false)
                            }
                          }}
                        >
                          导入
                        </Button>
                      </Space.Compact>
                    </div>

                    <Divider style={{ margin: '16px 0' }} />

                    <div>
                      <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 8 }}>
                        方式二：关键词搜索导入
                      </Text>
                      <Space.Compact style={{ width: '100%', marginBottom: 12 }}>
                        <Input
                          placeholder="输入关键词，如: 高血压 治疗"
                          value={pubmedSearchQuery}
                          onChange={(e) => setPubmedSearchQuery(e.target.value)}
                          onPressEnter={handlePubmedSearch}
                        />
                        <Button
                          type="default"
                          loading={pubmedSearching}
                          onClick={handlePubmedSearch}
                        >
                          搜索
                        </Button>
                      </Space.Compact>

                      {pubmedResults.length > 0 && (
                        <div style={{ maxHeight: 300, overflowY: 'auto' }}>
                          {pubmedResults.map((paper: any) => (
                            <Card key={paper.pmid} size="small" style={{ marginBottom: 8 }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                <div style={{ flex: 1, marginRight: 12 }}>
                                  <div style={{ fontWeight: 500, marginBottom: 4, fontSize: 13 }}>
                                    {paper.title}
                                  </div>
                                  <Text type="secondary" style={{ fontSize: 12 }}>
                                    {paper.journal} · {paper.publish_date} · PMID: {paper.pmid}
                                  </Text>
                                </div>
                                {paper.imported ? (
                                  <Tag color="green">已导入</Tag>
                                ) : (
                                  <Button
                                    size="small"
                                    type="primary"
                                    loading={importingPmid === paper.pmid}
                                    onClick={async () => {
                                      setImportingPmid(paper.pmid)
                                      try {
                                        await assetApi.importPubMed(paper.pmid)
                                        message.success('导入成功')
                                        setPubmedResults(prev =>
                                          prev.map(p => p.pmid === paper.pmid ? { ...p, imported: true } : p)
                                        )
                                        fetchData()
                                      } catch (e) {
                                        message.error('导入失败')
                                      } finally {
                                        setImportingPmid(null)
                                      }
                                    }}
                                  >
                                    导入
                                  </Button>
                                )}
                              </div>
                            </Card>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ),
              },
            ]}
          />
        </Modal>
      </div>
    </Layout>
  )
}

export default AssetHub
