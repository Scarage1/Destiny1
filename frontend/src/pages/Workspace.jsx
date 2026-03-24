import React, { useState, useEffect, useRef, useCallback } from 'react'
import { Link } from 'react-router-dom'
import ForceGraph2D from 'react-force-graph-2d'
import { fetchGraphOverview, fetchNodeDetails, fetchNodeNeighbors, askQuery } from '../api'
import QueryMessage from '../components/Message'
import { formatLatencyMs } from '../utils/metricsUi'
import { buildSessionSnapshot, reviveMessagesFromSnapshot } from '../utils/sessionSnapshot'

const WORKSPACE_SESSION_KEY = 'o2c_workspace_v1'

function readWorkspaceSession() {
  try {
    const raw = sessionStorage.getItem(WORKSPACE_SESSION_KEY)
    if (!raw) return { messages: [], conversationId: null }
    const data = JSON.parse(raw)
    if (data.version !== '1.0') return { messages: [], conversationId: null }
    const msgs = Array.isArray(data.messages) && data.messages.length > 0
      ? reviveMessagesFromSnapshot(data.messages)
      : []
    return {
      messages: msgs,
      conversationId: data.conversation_id || null,
    }
  } catch {
    return { messages: [], conversationId: null }
  }
}

// Reduced palette — 5 primary colors
const NODE_COLORS = {
  Customer:            '#d4a66a',
  SalesOrder:          '#6f93d8',
  SalesOrderItem:      '#83a4e2',
  Delivery:            '#6cb68a',
  DeliveryItem:        '#84c7a0',
  BillingDocument:     '#9d8ec9',
  BillingDocumentItem: '#b5a8da',
  JournalEntry:        '#b2718b',
  Payment:             '#6caec3',
  Product:             '#c98f67',
  Plant:               '#93ad72',
}

const LEGEND_TYPES = ['Customer', 'SalesOrder', 'Delivery', 'BillingDocument', 'Payment', 'Product']

const EXAMPLE_QUERIES = [
  'Top products by billing documents',
  'Find sales orders with broken flow',
  'Show customers and their sales orders',
  'Trace invoice 90000322 end-to-end',
]

function getNodeType(id) {
  if (!id) return 'Unknown'
  const i = id.indexOf(':')
  return i > 0 ? id.substring(0, i) : 'Unknown'
}

function getShortId(id) {
  if (!id) return ''
  const i = id.indexOf(':')
  return i > 0 ? id.substring(i + 1) : id
}

export default function Workspace() {
  // Graph
  const [graphData, setGraphData] = useState({ nodes: [], links: [] })
  const [graphStats, setGraphStats] = useState({ total_nodes: 0, total_edges: 0 })
  const [loadingGraph, setLoadingGraph] = useState(true)
  const [expandedNodes, setExpandedNodes] = useState(new Set())

  // Inspector
  const [selectedNode, setSelectedNode] = useState(null)
  const [nodeDetails, setNodeDetails] = useState(null)

  // Chat (restore synchronously so session is not clobbered by a first-blank persist)
  const initialSession = typeof sessionStorage !== 'undefined' ? readWorkspaceSession() : { messages: [], conversationId: null }
  const [messages, setMessages] = useState(initialSession.messages)
  const [input, setInput] = useState('')
  const [isQuerying, setIsQuerying] = useState(false)
  const [highlightedNodes, setHighlightedNodes] = useState(new Set())
  const [queryLatencyMs, setQueryLatencyMs] = useState(null)
  const [conversationId, setConversationId] = useState(initialSession.conversationId)

  // Refs
  const graphRef = useRef()
  const messagesEndRef = useRef()
  const inputRef = useRef(null)
  const nodeSet = useRef(new Set())
  const expandedNodesRef = useRef(new Set())
  useEffect(() => {
    try {
      const snap = buildSessionSnapshot({
        conversationId,
        messages,
        queryHistory: [],
        uiMode: 'standard',
        runtimeMetrics: null,
      })
      sessionStorage.setItem(WORKSPACE_SESSION_KEY, JSON.stringify(snap))
    } catch {
      /* ignore quota / serialization errors */
    }
  }, [messages, conversationId])

  // Load graph
  useEffect(() => {
    let cancelled = false
    setLoadingGraph(true)
    fetchGraphOverview()
      .then(data => {
        if (cancelled) return
        const nodes = (data.nodes || []).map(n => ({
          id: n.id,
          type: n.type || getNodeType(n.id),
          label: n.label || getShortId(n.id),
        }))
        const links = (data.edges || []).map(e => ({
          source: e.source,
          target: e.target,
          relationship: e.relationship || '',
        }))
        nodeSet.current = new Set(nodes.map(n => n.id))
        setGraphData({ nodes, links })
        setGraphStats(data.stats || { total_nodes: nodes.length, total_edges: links.length })
        setLoadingGraph(false)
      })
      .catch(() => setLoadingGraph(false))
    return () => { cancelled = true }
  }, [])

  // Auto-scroll chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Focus query input with '/' shortcut
  useEffect(() => {
    const onKeyDown = (event) => {
      const target = event.target
      const isTypingTarget = target instanceof HTMLElement
        && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)
      if (event.key === '/' && !isTypingTarget) {
        event.preventDefault()
        inputRef.current?.focus()
      }
      if (event.key === 'Escape') {
        setSelectedNode(null)
        setNodeDetails(null)
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  // Expand node
  const expandNode = useCallback(async (nodeId) => {
    if (expandedNodesRef.current.has(nodeId)) return
    expandedNodesRef.current.add(nodeId)
    try {
      const data = await fetchNodeNeighbors(nodeId)
      const newNodes = []
      const newLinks = []
      for (const n of (data.nodes || [])) {
        if (!nodeSet.current.has(n.id)) {
          newNodes.push({ id: n.id, type: n.type || getNodeType(n.id), label: n.label || getShortId(n.id) })
          nodeSet.current.add(n.id)
        }
      }
      for (const e of (data.edges || [])) {
        newLinks.push({ source: e.source, target: e.target, relationship: e.relationship || '' })
      }
      if (newNodes.length || newLinks.length) {
        setGraphData(prev => ({
          nodes: [...prev.nodes, ...newNodes],
          links: [...prev.links, ...newLinks],
        }))
      }
      setExpandedNodes(prev => new Set(prev).add(nodeId))
    } catch (err) {
      expandedNodesRef.current.delete(nodeId)
      console.error('Expand failed:', err)
    }
  }, [])

  // Node click
  const handleNodeClick = useCallback(async (node) => {
    setSelectedNode(node)
    expandNode(node.id)
    try {
      const details = await fetchNodeDetails(node.id)
      setNodeDetails(details)
    } catch {
      setNodeDetails(null)
    }
  }, [expandNode])

  // Chat send
  const handleSend = async (queryText) => {
    const q = (queryText || input).trim()
    if (!q || isQuerying) return
    const startedAt = performance.now()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', text: q }])
    setIsQuerying(true)
    try {
      const res = await askQuery(q, conversationId)
      if (res.conversation_id) {
        setConversationId(res.conversation_id)
      }
      setMessages(prev => [...prev, {
        role: 'system',
        text: res.answer,
        sql: res.query,
        totalResults: res.total_results,
        status: res.status,
        intent: res.intent,
        traceId: res.trace_id,
        plan: res.plan,
        verification: res.verification,
        traceEvents: (res.agent_trace && res.agent_trace.events) ? res.agent_trace.events : [],
        referencedNodes: res.referenced_nodes || [],
      }])
      if (res.referenced_nodes?.length > 0) {
        setHighlightedNodes(new Set(res.referenced_nodes))
      } else {
        setHighlightedNodes(new Set())
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'system',
        text: `Query failed: ${err?.message || 'Unknown error'}`,
        status: 'error',
      }])
    } finally {
      setQueryLatencyMs(Math.round(performance.now() - startedAt))
      setIsQuerying(false)
    }
  }

  // Node painting
  const paintNode = useCallback((node, ctx, globalScale) => {
    const type = node.type || getNodeType(node.id)
    const color = NODE_COLORS[type] || '#52525b'
    const isHighlighted = highlightedNodes.has(node.id)
    const isSelected = selectedNode?.id === node.id
    const r = isHighlighted ? 6 : (isSelected ? 5 : 3.5)

    // Subtle glow for highlighted
    if (isHighlighted) {
      ctx.beginPath()
      ctx.arc(node.x, node.y, r + 3, 0, 2 * Math.PI)
      ctx.fillStyle = `${color}22`
      ctx.fill()
    }

    // Node
    ctx.beginPath()
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI)
    ctx.fillStyle = isHighlighted ? color : `${color}cc`
    ctx.fill()

    // Selection ring
    if (isSelected) {
      ctx.strokeStyle = '#1f2937'
      ctx.lineWidth = 1
      ctx.stroke()
    }

    // Label on zoom
    if (globalScale > 2) {
      const label = getShortId(node.id)
      const truncated = label.length > 10 ? label.slice(0, 8) + '…' : label
      ctx.font = `${Math.max(3, 9 / globalScale)}px Inter, system-ui, sans-serif`
      ctx.fillStyle = '#6b7280'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'top'
      ctx.fillText(truncated, node.x, node.y + r + 2)
    }
  }, [highlightedNodes, selectedNode])

  return (
    <div className="workspace">
      {/* Top bar */}
      <div className="topbar">
        <div className="topbar__left">
          <Link to="/" className="topbar__brand">O2C Graph Intelligence</Link>
          <div className="topbar__stats">
            <span className="topbar__stat">Nodes<span className="topbar__stat-value">{graphStats.total_nodes || graphData.nodes.length}</span></span>
            <span className="topbar__stat">Edges<span className="topbar__stat-value">{graphStats.total_edges || graphData.links.length}</span></span>
            <span className="topbar__stat">Latency<span className="topbar__stat-value">{queryLatencyMs == null ? '—' : formatLatencyMs(queryLatencyMs)}</span></span>
          </div>
        </div>
        <div className="topbar__right">
          <div className="topbar__status">
            <span className="topbar__status-dot" />
            Live
          </div>
        </div>
      </div>

      {/* Graph */}
      <div className="graph-panel">
        {loadingGraph ? (
          <div className="graph-loading">Loading graph…</div>
        ) : (
          <ForceGraph2D
            ref={graphRef}
            graphData={graphData}
            nodeCanvasObject={paintNode}
            nodePointerAreaPaint={(node, color, ctx) => {
              ctx.beginPath()
              ctx.arc(node.x, node.y, 7, 0, 2 * Math.PI)
              ctx.fillStyle = color
              ctx.fill()
            }}
            linkColor={() => 'rgba(17, 24, 39, 0.1)'}
            linkWidth={0.4}
            linkDirectionalArrowLength={2.5}
            linkDirectionalArrowRelPos={1}
            onNodeClick={handleNodeClick}
            cooldownTicks={80}
            d3AlphaDecay={0.04}
            d3VelocityDecay={0.3}
            backgroundColor="#f6f8fc"
            enableZoomInteraction={true}
            enablePanInteraction={true}
          />
        )}

        {/* Legend */}
        <div className="graph-legend">
          {LEGEND_TYPES.map(type => (
            <div className="legend-item" key={type}>
              <span className="legend-dot" style={{ background: NODE_COLORS[type] }} />
              {type}
            </div>
          ))}
        </div>

        {/* Node tooltip */}
        {selectedNode && (
          <NodeTooltip
            node={selectedNode}
            details={nodeDetails}
            onClose={() => { setSelectedNode(null); setNodeDetails(null) }}
            onNodeClick={(id) => {
              const n = graphData.nodes.find(n => n.id === id)
              if (n) handleNodeClick(n)
            }}
          />
        )}
      </div>

      {/* Chat */}
      <div className="chat-panel">
        <div className="chat__header">
          <div className="chat__header-main">
            <div className="chat__header-title">Query</div>
            <div className="chat__header-subtitle">Deterministic answers grounded in your data.</div>
          </div>
        </div>

        <div className="chat__messages">
          {messages.length === 0 ? (
            <div className="chat__welcome">
              <div className="chat__welcome-title">Query your system</div>
              <div className="chat__welcome-desc">
                Ask about sales orders, deliveries, billing, and payments.
              </div>
              <div className="chat__examples">
                {EXAMPLE_QUERIES.map((q, i) => (
                  <button type="button" key={i} className="chat__example" onClick={() => handleSend(q)}>
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, i) => (
              <QueryMessage key={`${msg.traceId || 'm'}-${i}`} msg={msg} onSend={(q) => handleSend(q)} />
            ))
          )}
          {isQuerying && (
            <div className="message message--system">
              <div className="message__bubble">
                <div className="loading-dots"><span /><span /><span /></div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat__input-area">
          <form className="chat__input-form" onSubmit={e => { e.preventDefault(); handleSend() }}>
            <input
              ref={inputRef}
              className="chat__input"
              type="text"
              placeholder="Query your system…"
              value={input}
              onChange={e => setInput(e.target.value)}
              disabled={isQuerying}
            />
            <button className="chat__send-btn" type="submit" disabled={isQuerying || !input.trim()}>
              Send
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}


// ─── Node Tooltip ───
function NodeTooltip({ node, details, onClose, onNodeClick }) {
  const type = node.type || getNodeType(node.id)
  const color = NODE_COLORS[type] || '#52525b'
  const props = details?.properties || node || {}
  const neighbors = details?.neighbors || {}

  const skipKeys = new Set(['id', 'type', 'x', 'y', 'vx', 'vy', 'fx', 'fy', 'index', '__indexColor', 'label'])

  return (
    <div className="node-tooltip">
      <div className="tooltip__header">
        <div className="tooltip__type">
          <span className="tooltip__type-dot" style={{ background: color }} />
          {type}
          <span className="tooltip__id">{getShortId(node.id)}</span>
        </div>
        <button type="button" className="tooltip__close" onClick={onClose}>×</button>
      </div>
      <div className="tooltip__body">
        <div className="tooltip__section">
          <div className="tooltip__section-title">Properties</div>
          {Object.entries(props)
            .filter(([k]) => !skipKeys.has(k))
            .map(([k, v]) => (
              <div className="tooltip__prop" key={k}>
                <span className="tooltip__prop-key">{k}</span>
                <span className="tooltip__prop-value">{String(v ?? '—')}</span>
              </div>
            ))
          }
        </div>
        {Object.keys(neighbors).length > 0 && (
          <div className="tooltip__section">
            <div className="tooltip__section-title">Connections</div>
            {Object.entries(neighbors).map(([rel, items]) =>
              items.map((item, i) => (
                <button
                  type="button"
                  className="tooltip__neighbor"
                  key={`${rel}-${i}`}
                  onClick={() => onNodeClick(item.id)}
                >
                  <span className="legend-dot" style={{ background: NODE_COLORS[item.type || getNodeType(item.id)] || '#52525b' }} />
                  {getShortId(item.id)}
                  <span className="tooltip__neighbor-rel">{item.relationship || rel}</span>
                </button>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}
