import React, { useState, useEffect, useRef, useCallback } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import { fetchGraphOverview, fetchNodeDetails, fetchNodeNeighbors, askQuery } from './api'

// ─── Node type styling map ───
const NODE_COLORS = {
  Customer: '#f59e0b',
  SalesOrder: '#3b82f6',
  SalesOrderItem: '#60a5fa',
  Delivery: '#10b981',
  DeliveryItem: '#34d399',
  BillingDocument: '#8b5cf6',
  BillingDocumentItem: '#a78bfa',
  JournalEntry: '#f43f5e',
  Payment: '#06b6d4',
  Product: '#f97316',
  Plant: '#84cc16',
}

const NODE_LABELS = {
  Customer: '👤',
  SalesOrder: '📋',
  SalesOrderItem: '📦',
  Delivery: '🚚',
  DeliveryItem: '📦',
  BillingDocument: '💰',
  BillingDocumentItem: '🧾',
  JournalEntry: '📒',
  Payment: '💳',
  Product: '🏭',
  Plant: '🏢',
}

const EXAMPLE_QUERIES = [
  'Which products are associated with the highest number of billing documents?',
  'Identify sales orders that have broken or incomplete flows',
  'Show me all customers with their sales orders',
  'Trace the full flow of a billing document',
]

function getNodeType(id) {
  if (!id) return 'Unknown'
  const sep = id.indexOf(':')
  return sep > 0 ? id.substring(0, sep) : 'Unknown'
}

function getNodeShortId(id) {
  if (!id) return ''
  const sep = id.indexOf(':')
  return sep > 0 ? id.substring(sep + 1) : id
}

// ─────────────── App ───────────────
export default function App() {
  // Graph state
  const [graphData, setGraphData] = useState({ nodes: [], links: [] })
  const [graphStats, setGraphStats] = useState({})
  const [loadingGraph, setLoadingGraph] = useState(true)
  const [expandedNodes, setExpandedNodes] = useState(new Set())

  // Inspector state
  const [selectedNode, setSelectedNode] = useState(null)
  const [nodeDetails, setNodeDetails] = useState(null)
  const [loadingDetails, setLoadingDetails] = useState(false)

  // Chat state
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isQuerying, setIsQuerying] = useState(false)
  const [highlightedNodes, setHighlightedNodes] = useState(new Set())

  // Refs
  const graphRef = useRef()
  const messagesEndRef = useRef()
  const existingNodeIds = useRef(new Set())

  // ─── Load initial graph ───
  useEffect(() => {
    let cancelled = false
    setLoadingGraph(true)
    fetchGraphOverview()
      .then(data => {
        if (cancelled) return
        const nodes = (data.nodes || []).map(n => ({
          id: n.id,
          type: n.type || getNodeType(n.id),
          label: n.label || getNodeShortId(n.id),
          ...n,
        }))
        const links = (data.edges || []).map(e => ({
          source: e.source,
          target: e.target,
          relation: e.relation || e.label || '',
        }))
        const nodeSet = new Set(nodes.map(n => n.id))
        existingNodeIds.current = nodeSet
        setGraphData({ nodes, links })
        setGraphStats(data.stats || { nodes: nodes.length, edges: links.length })
        setLoadingGraph(false)
      })
      .catch(err => {
        console.error('Failed to load graph:', err)
        setLoadingGraph(false)
      })
    return () => { cancelled = true }
  }, [])

  // ─── Auto-scroll chat ───
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ─── Expand node (add neighbors to graph) ───
  const expandNode = useCallback(async (nodeId) => {
    if (expandedNodes.has(nodeId)) return
    try {
      const data = await fetchNodeNeighbors(nodeId)
      const newNodes = []
      const newLinks = []
      for (const n of (data.nodes || [])) {
        const nid = n.id
        if (!existingNodeIds.current.has(nid)) {
          newNodes.push({ id: nid, type: n.type || getNodeType(nid), label: n.label || getNodeShortId(nid), ...n })
          existingNodeIds.current.add(nid)
        }
      }
      for (const e of (data.edges || [])) {
        newLinks.push({ source: e.source, target: e.target, relation: e.relation || e.label || '' })
      }
      if (newNodes.length > 0 || newLinks.length > 0) {
        setGraphData(prev => ({
          nodes: [...prev.nodes, ...newNodes],
          links: [...prev.links, ...newLinks],
        }))
      }
      setExpandedNodes(prev => new Set(prev).add(nodeId))
    } catch (err) {
      console.error('Expand failed:', err)
    }
  }, [expandedNodes])

  // ─── Node click handler ───
  const handleNodeClick = useCallback(async (node) => {
    setSelectedNode(node)
    setLoadingDetails(true)
    expandNode(node.id)
    try {
      const details = await fetchNodeDetails(node.id)
      setNodeDetails(details)
    } catch {
      setNodeDetails(null)
    }
    setLoadingDetails(false)
  }, [expandNode])

  // ─── Chat submit ───
  const handleSend = async (queryText) => {
    const q = (queryText || input).trim()
    if (!q || isQuerying) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', text: q }])
    setIsQuerying(true)
    try {
      const res = await askQuery(q)
      setMessages(prev => [...prev, {
        role: 'system',
        text: res.answer,
        sql: res.query,
        totalResults: res.total_results,
        status: res.status,
        referencedNodes: res.referenced_nodes || [],
      }])
      // Highlight referenced nodes
      if (res.referenced_nodes && res.referenced_nodes.length > 0) {
        setHighlightedNodes(new Set(res.referenced_nodes))
      } else {
        setHighlightedNodes(new Set())
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'system',
        text: `Error: ${err.message}`,
        status: 'error',
      }])
    }
    setIsQuerying(false)
  }

  // ─── Canvas node painting ───
  const paintNode = useCallback((node, ctx, globalScale) => {
    const type = node.type || getNodeType(node.id)
    const color = NODE_COLORS[type] || '#64748b'
    const isHighlighted = highlightedNodes.has(node.id)
    const isSelected = selectedNode?.id === node.id
    const r = isHighlighted ? 7 : (isSelected ? 6 : 4)

    // Glow for highlighted
    if (isHighlighted) {
      ctx.beginPath()
      ctx.arc(node.x, node.y, r + 4, 0, 2 * Math.PI)
      ctx.fillStyle = `${color}33`
      ctx.fill()
      ctx.beginPath()
      ctx.arc(node.x, node.y, r + 2, 0, 2 * Math.PI)
      ctx.fillStyle = `${color}66`
      ctx.fill()
    }

    // Node circle
    ctx.beginPath()
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI)
    ctx.fillStyle = color
    ctx.fill()

    // Selection ring
    if (isSelected) {
      ctx.strokeStyle = '#fbbf24'
      ctx.lineWidth = 1.5
      ctx.stroke()
    }

    // Label (only when zoomed in enough)
    if (globalScale > 1.5) {
      const label = getNodeShortId(node.id)
      const truncated = label.length > 12 ? label.slice(0, 10) + '…' : label
      ctx.font = `${Math.max(3, 10 / globalScale)}px Inter, sans-serif`
      ctx.fillStyle = '#f1f5f9'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'top'
      ctx.fillText(truncated, node.x, node.y + r + 2)
    }
  }, [highlightedNodes, selectedNode])

  // ─── Render ───
  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="header">
        <div className="header__logo">
          <div className="header__icon">⬡</div>
          <div>
            <div className="header__title">SAP O2C Graph Explorer</div>
            <div className="header__subtitle">Order-to-Cash Intelligence</div>
          </div>
        </div>
        <div className="header__stats">
          <div className="header__stat">
            Nodes <span className="header__stat-value">{graphData.nodes.length}</span>
          </div>
          <div className="header__stat">
            Edges <span className="header__stat-value">{graphData.links.length}</span>
          </div>
        </div>
      </header>

      {/* ── Graph Panel ── */}
      <div className="graph-panel">
        {loadingGraph ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
            Loading graph…
          </div>
        ) : (
          <ForceGraph2D
            ref={graphRef}
            graphData={graphData}
            nodeCanvasObject={paintNode}
            nodePointerAreaPaint={(node, color, ctx) => {
              ctx.beginPath()
              ctx.arc(node.x, node.y, 8, 0, 2 * Math.PI)
              ctx.fillStyle = color
              ctx.fill()
            }}
            linkColor={() => 'rgba(148, 163, 184, 0.15)'}
            linkWidth={0.5}
            linkDirectionalArrowLength={3}
            linkDirectionalArrowRelPos={1}
            onNodeClick={handleNodeClick}
            cooldownTicks={80}
            d3AlphaDecay={0.04}
            d3VelocityDecay={0.3}
            backgroundColor="#0a0e1a"
            enableZoomInteraction={true}
            enablePanInteraction={true}
          />
        )}

        {/* Legend */}
        <div className="graph-legend">
          {Object.entries(NODE_COLORS).map(([type, color]) => (
            <div className="legend-item" key={type}>
              <span className="legend-dot" style={{ background: color }} />
              {type}
            </div>
          ))}
        </div>

        {/* Node Inspector */}
        {selectedNode && (
          <NodeInspector
            node={selectedNode}
            details={nodeDetails}
            loading={loadingDetails}
            onClose={() => { setSelectedNode(null); setNodeDetails(null) }}
            onNodeClick={(id) => {
              const n = graphData.nodes.find(n => n.id === id)
              if (n) handleNodeClick(n)
            }}
          />
        )}
      </div>

      {/* ── Chat Panel ── */}
      <div className="chat-panel">
        <div className="chat__header">
          <div className="chat__header-icon">🤖</div>
          <div className="chat__header-title">Query Assistant</div>
        </div>

        <div className="chat__messages">
          {messages.length === 0 ? (
            <div className="chat__welcome">
              <div className="chat__welcome-icon">💬</div>
              <div className="chat__welcome-title">Ask about your O2C data</div>
              <div className="chat__welcome-desc">
                Query sales orders, deliveries, billing documents, payments, and more using natural language.
              </div>
              <div className="chat__examples">
                {EXAMPLE_QUERIES.map((q, i) => (
                  <button
                    key={i}
                    className="chat__example"
                    onClick={() => handleSend(q)}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, i) => (
              <Message key={i} msg={msg} />
            ))
          )}
          {isQuerying && (
            <div className="message message--system">
              <div className="message__bubble">
                <div className="loading-dots">
                  <span /><span /><span />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat__input-area">
          <form
            className="chat__input-form"
            onSubmit={(e) => { e.preventDefault(); handleSend() }}
          >
            <input
              className="chat__input"
              type="text"
              placeholder="Ask a question about the dataset…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isQuerying}
            />
            <button
              className="chat__send-btn"
              type="submit"
              disabled={isQuerying || !input.trim()}
            >
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}


// ─── Message Component ───
function Message({ msg }) {
  const [showSql, setShowSql] = useState(false)

  const roleClass = msg.role === 'user' ? 'message--user' : 'message--system'
  const statusClass = msg.status === 'rejected' ? ' message--rejected' : msg.status === 'error' ? ' message--error' : ''

  return (
    <div className={`message ${roleClass}${statusClass}`}>
      <div className="message__bubble">
        <div style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</div>
        {msg.sql && (
          <>
            <button
              onClick={() => setShowSql(!showSql)}
              style={{
                background: 'none', border: 'none', color: 'var(--accent-cyan)',
                cursor: 'pointer', fontSize: '11px', marginTop: '6px', padding: 0,
                fontFamily: 'var(--font-sans)',
              }}
            >
              {showSql ? '▾ Hide SQL' : '▸ Show SQL'}
            </button>
            {showSql && (
              <div className="message__sql">
                <div className="message__sql-label">Generated SQL</div>
                {msg.sql}
              </div>
            )}
          </>
        )}
        {msg.totalResults != null && (
          <div className="message__results-count">
            {msg.totalResults} result{msg.totalResults !== 1 ? 's' : ''} returned
          </div>
        )}
      </div>
    </div>
  )
}


// ─── Node Inspector Component ───
function NodeInspector({ node, details, loading, onClose, onNodeClick }) {
  const type = node.type || getNodeType(node.id)
  const color = NODE_COLORS[type] || '#64748b'
  const shortId = getNodeShortId(node.id)

  // Merge node props + details
  const props = details?.properties || node || {}
  const neighbors = details?.neighbors || {}

  return (
    <div className="node-inspector">
      <div className="inspector__header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="inspector__type-badge" style={{ background: color }}>
            {NODE_LABELS[type] || '●'} {type}
          </span>
          <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
            {shortId}
          </span>
        </div>
        <button className="inspector__close" onClick={onClose}>✕</button>
      </div>
      <div className="inspector__body">
        {loading ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '12px', padding: '8px 0' }}>Loading…</div>
        ) : (
          <>
            <div className="inspector__section">
              <div className="inspector__section-title">Properties</div>
              <div className="inspector__props">
                {Object.entries(props)
                  .filter(([k]) => !['id', 'type', 'x', 'y', 'vx', 'vy', 'fx', 'fy', 'index', '__indexColor', 'label'].includes(k))
                  .map(([k, v]) => (
                    <div className="inspector__prop" key={k}>
                      <span className="inspector__prop-key">{k}</span>
                      <span className="inspector__prop-value">{String(v ?? '—')}</span>
                    </div>
                  ))
                }
              </div>
            </div>
            {Object.keys(neighbors).length > 0 && (
              <div className="inspector__section">
                <div className="inspector__section-title">Relationships</div>
                <div className="inspector__neighbors">
                  {Object.entries(neighbors).map(([rel, items]) =>
                    items.map((item, i) => (
                      <div
                        className="inspector__neighbor"
                        key={`${rel}-${i}`}
                        onClick={() => onNodeClick(item.id)}
                      >
                        <span className="legend-dot" style={{ background: NODE_COLORS[item.type || getNodeType(item.id)] || '#64748b' }} />
                        <span>{getNodeShortId(item.id)}</span>
                        <span className="inspector__neighbor-rel">{rel}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
