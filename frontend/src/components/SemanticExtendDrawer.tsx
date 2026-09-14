import React, { useState, useEffect } from 'react'
import { Drawer, Button, Checkbox, message, Spin, Tag, Empty, Divider } from 'antd'
import { ThunderboltOutlined, BranchesOutlined, SaveOutlined } from '@ant-design/icons'
import { semanticApi } from '@/api'

interface ExtendItem {
  question: string
  is_duplicate: boolean
  similarity: number
}

interface ExtendResult {
  synonyms: ExtendItem[]
  deep: ExtendItem[]
  source: string
}

interface Props {
  open: boolean
  onClose: () => void
  semanticId: number | null
  semanticQuestion: string
  onSaved: () => void
}

const SemanticExtendDrawer: React.FC<Props> = ({ open, onClose, semanticId, semanticQuestion, onSaved }) => {
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [result, setResult] = useState<ExtendResult | null>(null)
  const [selectedSynonyms, setSelectedSynonyms] = useState<Set<string>>(new Set())
  const [selectedDeep, setSelectedDeep] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (open && semanticId) {
      loadExtend()
    }
  }, [open, semanticId])

  const loadExtend = async () => {
    if (!semanticId) return
    setLoading(true)
    setResult(null)
    setSelectedSynonyms(new Set())
    setSelectedDeep(new Set())
    try {
      const res: any = await semanticApi.extend(semanticId)
      setResult(res.data)
      // 默认勾选非重复的
      const syn = new Set<string>()
      res.data.synonyms.forEach((item: ExtendItem) => {
        if (!item.is_duplicate) syn.add(item.question)
      })
      setSelectedSynonyms(syn)
      const deep = new Set<string>()
      res.data.deep.forEach((item: ExtendItem) => {
        if (!item.is_duplicate) deep.add(item.question)
      })
      setSelectedDeep(deep)
    } catch (e: any) {
      message.error('生成延伸失败：' + (e.response?.data?.detail || e.message))
    } finally {
      setLoading(false)
    }
  }

  const toggleItem = (question: string, type: 'synonym' | 'deep') => {
    if (type === 'synonym') {
      const next = new Set(selectedSynonyms)
      if (next.has(question)) next.delete(question)
      else next.add(question)
      setSelectedSynonyms(next)
    } else {
      const next = new Set(selectedDeep)
      if (next.has(question)) next.delete(question)
      else next.add(question)
      setSelectedDeep(next)
    }
  }

  const handleSave = async () => {
    if (!semanticId) return
    const allSelected = [...selectedSynonyms, ...selectedDeep]
    if (allSelected.length === 0) {
      message.warning('请至少选择一个要保存的问题')
      return
    }
    setSaving(true)
    try {
      // 分两次保存（同义变体和深度延伸）
      if (selectedSynonyms.size > 0) {
        await semanticApi.saveExtended({
          questions: [...selectedSynonyms],
          parent_id: semanticId,
          extend_type: 'synonym'
        })
      }
      if (selectedDeep.size > 0) {
        await semanticApi.saveExtended({
          questions: [...selectedDeep],
          parent_id: semanticId,
          extend_type: 'deep'
        })
      }
      message.success(`已保存 ${allSelected.length} 个延伸问题`)
      onSaved()
      onClose()
    } catch (e: any) {
      message.error('保存失败：' + (e.response?.data?.detail || e.message))
    } finally {
      setSaving(false)
    }
  }

  const totalSelected = selectedSynonyms.size + selectedDeep.size

  const renderItemList = (items: ExtendItem[], selected: Set<string>, type: 'synonym' | 'deep') => {
    if (items.length === 0) {
      return <Empty description="暂无生成结果" image={Empty.PRESENTED_IMAGE_SIMPLE} />
    }
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {items.map((item, idx) => (
          <div
            key={item.question}
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              padding: '10px 12px',
              background: selected.has(item.question) ? '#EFF6FF' : '#F8FAFC',
              borderRadius: 8,
              border: selected.has(item.question) ? '1px solid #3B82F6' : '1px solid transparent',
              cursor: 'pointer'
            }}
            onClick={() => toggleItem(item.question, type)}
          >
            <Checkbox
              checked={selected.has(item.question)}
              onChange={() => toggleItem(item.question, type)}
              style={{ marginRight: 10, marginTop: 2 }}
            />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14, color: '#1E293B' }}>{item.question}</div>
              {item.is_duplicate && (
                <div style={{ marginTop: 4 }}>
                  <Tag color="orange" style={{ fontSize: 11 }}>
                    可能重复（相似度 {Math.round(item.similarity * 100)}%）
                  </Tag>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <Drawer
      title={
        <div>
          <BranchesOutlined style={{ marginRight: 8, color: '#3B82F6' }} />
          语义延伸
          <div style={{ fontSize: 12, color: '#94A3B8', fontWeight: 400, marginTop: 4 }}>
            原问题：{semanticQuestion}
          </div>
        </div>
      }
      width={560}
      open={open}
      onClose={onClose}
      extra={
        <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave} disabled={totalSelected === 0}>
          保存选中（{totalSelected}）
        </Button>
      }
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: '#94A3B8' }}>AI 正在生成延伸问题...</div>
        </div>
      ) : result ? (
        <div>
          {/* 说明 */}
          <div style={{ background: '#F0F9FF', padding: '12px 16px', borderRadius: 8, marginBottom: 20 }}>
            <div style={{ fontSize: 13, color: '#0369A1', marginBottom: 6 }}>
              💡 语义延伸 = 覆盖更多用户真实搜索的问法，提升医生在 AI 搜索中的曝光率
            </div>
            <div style={{ fontSize: 12, color: '#64748B' }}>
              来源：{result.source === 'llm' ? 'AI 生成' : result.source === 'template' ? '模板降级' : '部分AI+部分模板'}
            </div>
          </div>

          {/* 同义变体 */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
              <ThunderboltOutlined style={{ color: '#F59E0B', marginRight: 8 }} />
              <span style={{ fontSize: 15, fontWeight: 600 }}>同义变体</span>
              <Tag color="blue" style={{ marginLeft: 8 }}>已选 {selectedSynonyms.size}/{result.synonyms.length}</Tag>
            </div>
            <div style={{ fontSize: 12, color: '#94A3B8', marginBottom: 10 }}>
              同一个问题，不同的问法，意思完全相同
            </div>
            {renderItemList(result.synonyms, selectedSynonyms, 'synonym')}
          </div>

          <Divider style={{ margin: '16px 0' }} />

          {/* 深度延伸 */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
              <BranchesOutlined style={{ color: '#8B5CF6', marginRight: 8 }} />
              <span style={{ fontSize: 15, fontWeight: 600 }}>深度延伸</span>
              <Tag color="purple" style={{ marginLeft: 8 }}>已选 {selectedDeep.size}/{result.deep.length}</Tag>
            </div>
            <div style={{ fontSize: 12, color: '#94A3B8', marginBottom: 10 }}>
              基于医生专长，把泛化问题具体化为疾病/场景
            </div>
            {result.deep.length === 0 ? (
              <Empty description="暂无深度延伸（需要完善医生专长）" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              renderItemList(result.deep, selectedDeep, 'deep')
            )}
          </div>
        </div>
      ) : (
        <Empty description="加载失败" />
      )}
    </Drawer>
  )
}

export default SemanticExtendDrawer
