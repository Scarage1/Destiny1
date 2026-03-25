import React, { useState, useEffect, useRef, useCallback } from 'react'
import QueryHistoryPanel, { addToHistory } from '../components/QueryHistoryPanel'
import { Link, useSearchParams } from 'react-router-dom'
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
  { icon: '📊', text: 'Top products by billing documents' },
  { icon: '🔍', text: 'Find sales orders with broken flow' },
  { icon: '👥', text: 'Show customers and their sales orders' },
  { icon: '🔗', text: 'Trace invoice 90000322 end-to-end' },
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
  const [graphError, setGraphError] = useState(false)
  const [expandedNodes, setExpandedNodes] = useState(new Set())
  const [backendOnline, setBackendOnline] = useState(true)

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

  // Mobile tab — 'graph' or 'chat'
  const [mobileTab, setMobileTab] = useState('chat')

  // Dark mode (T8)
  const [darkMode, setDarkMode] = useState(() => {
    try { return localStorage.getItem('o2c_dark_mode') === '1' } catch { return false }
  })

  // W3-1: Auto-send queries coming from landing page sample chips (?q=...)
  const [searchParams, setSearchParams] = useSearchParams()
  useEffect(() => {
    const presetQ = searchParams.get('q')
    if (presetQ) {
      setSearchParams({}, { replace: true }) // clear param from URL
      // Delay slightly so graph/session restore finishes first
      setTimeout(() => handleSend(presetQ), 600)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light')
    try { localStorage.setItem('o2c_dark_mode', darkMode ? '1' : '0') } catch {}
  }, [darkMode])

  // Dashboard KPI cards (T18)
  const [dashboardCards, setDashboardCards] = useState([])
  useEffect(() => {
    fetch('/api/dashboard')
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data?.cards) setDashboardCards(data.cards) })
      .catch(() => {})
  }, [])

  // T19: Anomaly badge — sum of never-billed + uncleared counts
  const anomalyCount = dashboardCards.reduce((acc, card) => {
    if (card.severity === 'warning' || card.severity === 'critical') {
      const n = parseInt(String(card.value), 10)
      return acc + (isNaN(n) ? 0 : n)
    }
    return acc
  }, 0)

  // Refs
  const graphRef = useRef()
  const messagesEndRef = useRef()
  const inputRef = useRef(null)
  const nodeSet = useRef(new Set())
  const expandedNodesRef = useRef(new Set())

  // Persist session
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
  const loadGraph = useCallback(() => {
    let cancelled = false
    setLoadingGraph(true)
    setGraphError(false)
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
        setBackendOnline(true)
        setLoadingGraph(false)
      })
      .catch(() => {
        if (cancelled) return
        setGraphError(true)
        setBackendOnline(false)
        setLoadingGraph(false)
      })
    return () => { cancelled = true }
  }, [])

  useEffect(() => loadGraph(), [loadGraph])

  // Health ping every 10s to drive the Live indicator
  useEffect(() => {
    const check = () =>
      fetch('/api/health', { method: 'GET' })
        .then(r => setBackendOnline(r.ok))
        .catch(() => setBackendOnline(false))
    const id = setInterval(check, 10000)
    return () => clearInterval(id)
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

  // Auto-expand textarea
  const handleInputChange = useCallback((e) => {
    setInput(e.target.value)
    const el = e.target
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
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
    // T12: switch to chat tab and send a trace query for the clicked node
    setMobileTab('chat')
    const nodeType = node.type || getNodeType(node.id)
    const shortId  = getShortId(node.id)
    const traceQ   = `Trace the full O2C flow for ${nodeType} ${shortId}`
    handleSend(traceQ)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // eslint-disable-next-line-ignore

  const handleNodeClickDetails = useCallback(async (node) => {
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
  const handleSend = async (queryText, fromHistory = false) => {
    const q = (queryText || input).trim()
    if (!q || isQuerying) return
    const startedAt = performance.now()
    setInput('')
    // Reset textarea height
    if (inputRef.current) {
      inputRef.current.style.height = 'auto'
    }
    setMessages(prev => [...prev, { role: 'user', text: q }])
    // W1-4: Immediately show loading bubble so user knows query was received
    const loadingId = `loading-${Date.now()}`
    setMessages(prev => [...prev, { role: 'system', _loading: true, _id: loadingId }])
    setIsQuerying(true)
    try {
      const res = await askQuery(q, conversationId)
      if (res.conversation_id) {
        setConversationId(res.conversation_id)
      }
      // T10: Record this query in history panel
      addToHistory({ query: q, intent: res.intent || res.plan?.intent || 'analyze', status: fromHistory ? 'rerun' : (res.status || 'success') })
      try { window.dispatchEvent(new CustomEvent('o2c_history_update')) } catch { /* ignore in test env */ }

      // W1-4: Replace loading bubble with real response
      setMessages(prev => {
        const withoutLoading = prev.filter(m => m._id !== loadingId)
        return [...withoutLoading, {
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
        }]
      })
      // W1-5: Only track latency for real query responses, not guard rejections
      if (res.status !== 'rejected') setQueryLatencyMs(Math.round(performance.now() - startedAt))
      if (res.referenced_nodes?.length > 0) {
        setHighlightedNodes(new Set(res.referenced_nodes))
      } else {
        setHighlightedNodes(new Set())
      }
    } catch (err) {
      setMessages(prev => {
        const withoutLoading = prev.filter(m => m._id !== loadingId)
        return [...withoutLoading, {
          role: 'system',
          text: `Something went wrong. ${err?.message || 'Please try again.'}`,
          status: 'error',
        }]
      })
    } finally {
      setIsQuerying(false)
    }
  }

  // Handle Enter/Shift+Enter
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Zoom controls
  const handleZoomIn = () => graphRef.current?.zoom(graphRef.current.zoom() * 1.4, 300)
  const handleZoomOut = () => graphRef.current?.zoom(graphRef.current.zoom() / 1.4, 300)

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
    <div className="workspace" data-tab={mobileTab}>
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
          {/* T19: Anomaly badge — only shown when live anomalies detected from dashboard */}
          {anomalyCount > 0 && (
            <button
              type="button"
              className="anomaly-badge"
              title={`${anomalyCount} process anomalies detected — click to investigate`}
              onClick={() => {
                setMobileTab('chat')
                handleSend('List all process anomalies and orphan records in the system')
              }}
            >
              ⚠️ {anomalyCount}
            </button>
          )}
          <QueryHistoryPanel onSelect={(q) => { setMobileTab('chat'); handleSend(q, true) }} />
          <button
            type="button"
            className="dark-toggle"
            onClick={() => setDarkMode(d => !d)}
            title="Toggle dark mode"
          >
            {darkMode ? '☀️ Light' : '🌙 Dark'}
          </button>
          <div className={`topbar__status${backendOnline ? '' : ' topbar__status--offline'}`}>
            <span className="topbar__status-dot" />
            {backendOnline ? 'Live' : 'Offline'}
          </div>
        </div>
      </div>

      {/* Graph */}
      <div className="graph-panel">
        {loadingGraph ? (
          <div className="graph-loading">
            <div className="graph-loading__text">Loading graph…</div>
            <div className="graph-loading__shimmer" />
          </div>
        ) : graphError ? (
          <div className="graph-error">
            <div className="graph-error__icon">⬡</div>
            <div className="graph-error__text">
              Unable to connect to the backend. Check that the server is running and try again.
            </div>
            <button className="graph-error__retry" onClick={loadGraph}>
              Retry
            </button>
          </div>
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

        {/* Zoom controls */}
        {!loadingGraph && !graphError && (
          <div className="graph-controls">
            <button className="graph-controls__btn" onClick={handleZoomIn} title="Zoom in" type="button">+</button>
            <button className="graph-controls__btn" onClick={handleZoomOut} title="Zoom out" type="button">−</button>
          </div>
        )}

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
            <div className="chat__header-subtitle">Ask anything about your O2C data</div>
          </div>
        </div>

        {/* T18: Compact stat strip — no icons, single row */}
        {dashboardCards.length > 0 && (
          <div className="stat-strip">
            {dashboardCards.map(card => (
              <div
                key={card.id}
                className={`stat-strip__item${card.severity === 'warning' ? ' stat-strip__item--warning' : card.severity === 'critical' ? ' stat-strip__item--critical' : ''}`}
              >
                <span className="stat-strip__value">{card.value}</span>
                <span className="stat-strip__label">{card.label}</span>
              </div>
            ))}
          </div>
        )}

        <div className="chat__messages">
          {messages.length === 0 ? (
            <div className="chat__welcome">
              <div className="chat__welcome-icon">⬡</div>
              <div className="chat__welcome-title">What would you like to know?</div>
              <div className="chat__welcome-desc">
                Ask about sales orders, deliveries, billing, payments, and more. Every answer is grounded in your data.
              </div>
              <div className="chat__examples">
                {EXAMPLE_QUERIES.map((q, i) => (
                  <button type="button" key={i} className="chat__example" onClick={() => handleSend(q.text)}>
                    {q.text}
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
                <div className="thinking-indicator">
                  <span className="thinking-indicator__text">Thinking</span>
                  <span className="thinking-indicator__dots"><span /><span /><span /></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat__input-area">
          <form className="chat__input-form" onSubmit={e => { e.preventDefault(); handleSend() }}>
            <textarea
              ref={inputRef}
              className="chat__input"
              placeholder="Ask about your O2C data…"
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              disabled={isQuerying}
              rows={1}
            />
            <button className="chat__send-btn" type="submit" disabled={isQuerying || !input.trim()} title="Send">
              ↑
            </button>
          </form>
        </div>
      </div>

      {/* ── Mobile tab bar — hidden on desktop via CSS ── */}
      <div className="ws-tab-bar" role="tablist" aria-label="Workspace sections">
        <button
          type="button"
          role="tab"
          aria-selected={mobileTab === 'graph'}
          className={`ws-tab${mobileTab === 'graph' ? ' ws-tab--active' : ''}`}
          onClick={() => setMobileTab('graph')}
        >
          <span className="ws-tab__icon">🕸️</span>
          Graph
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mobileTab === 'chat'}
          className={`ws-tab${mobileTab === 'chat' ? ' ws-tab--active' : ''}`}
          onClick={() => { setMobileTab('chat'); setTimeout(() => inputRef.current?.focus(), 100) }}
        >
          <span className="ws-tab__icon">💬</span>
          Ask
        </button>
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
