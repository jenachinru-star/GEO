import { useRef, useEffect, useState } from 'react'
import { Transformer } from 'markmap-lib'
import { Markmap } from 'markmap-view'

interface MindmapProps {
  content: string  // Markdown格式内容
}

const MindmapViewer = ({ content }: MindmapProps) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const mmRef = useRef<Markmap | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!containerRef.current || !content) return

    setLoading(true)
    setError('')

    try {
      // 创建transformer
      const transformer = new Transformer()
      const { root } = transformer.transform(content)

      // 清空容器
      containerRef.current.innerHTML = ''

      // 创建SVG元素
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
      svg.style.width = '100%'
      svg.style.height = '500px'
      containerRef.current.appendChild(svg)

      // 渲染markmap
      mmRef.current = Markmap.create(svg, {
        autoFit: true,
        duration: 300,
      }, root)

      setLoading(false)
    } catch (e: any) {
      console.error('Mindmap render error:', e)
      setError('思维导图渲染失败：' + e.message)
      setLoading(false)
    }

    return () => {
      if (mmRef.current) {
        mmRef.current.destroy()
      }
    }
  }, [content])

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 40 }}>加载思维导图中...</div>
  }

  if (error) {
    return <div style={{ textAlign: 'center', padding: 40, color: '#ff4d4f' }}>{error}</div>
  }

  return (
    <div>
      <div ref={containerRef} style={{ width: '100%' }} />
      <div style={{ textAlign: 'center', marginTop: 8 }}>
        <span style={{ fontSize: 12, color: '#999' }}>
          提示：滚轮缩放，拖拽平移，点击节点展开/折叠
        </span>
      </div>
    </div>
  )
}

export default MindmapViewer
