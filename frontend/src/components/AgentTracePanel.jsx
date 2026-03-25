import React, { useState } from 'react'

// ─── Stage config ───────────────────────────────────────────────────────────
const STAGE_CONFIG = {
  planner:      { label: 'Planner',    icon: '◈', description: 'Parsed intent and built query plan' },
  guard_pass:   { label: 'Guard',      icon: '◉', description: 'Query allowed — within permitted scope' },
  guard_reject: { label: 'Guard',      icon: '◉', description: 'Query blocked — outside permitted scope', alwaysBlocked: true },
  query_agent:  { label: 'Query',      icon: '◎', description: 'Selected deterministic SQL template' },
  execution:    { label: 'Execution',  icon: '▶', description: 'Ran query against database' },
  verification: { label: 'Verify',     icon: '◇', description: 'Verified result quality and grounding' },
  response:     { label: 'Response',   icon: '◆', description: 'Synthesised natural language answer' },
}

// ─── Pure helper exports (used by tests) ───────────────────────────────────
export function getBadgeClass(status) {
  if (status === 'blocked') return 'trace-badge trace-badge--blocked'
  if (status === 'warning') return 'trace-badge trace-badge--warning'
  return 'trace-badge trace-badge--passed'
}

export function getBadgeSymbol(status) {
  if (status === 'blocked') return '✗'
  if (status === 'warning') return '⚠'
  return '✓'
}

export function collectStageEvents(traceEvents = []) {
  const rows = []
  const seen = new Set()
  for (const ev of traceEvents) {
    if (!STAGE_CONFIG[ev.stage]) continue
    if (seen.has(ev.stage)) continue
    rows.push({ ...ev, config: STAGE_CONFIG[ev.stage] })
    seen.add(ev.stage)
  }
  return rows
}

function parseTimestampMs(value) {
  if (!value) return null
  const t = Date.parse(value)
  return Number.isFinite(t) ? t : null
}

export function computeTraceMetrics(traceEvents = []) {
  if (!Array.isArray(traceEvents) || traceEvents.length === 0) {
    return { totalMs: null, stageCount: 0 }
  }
  const firstTs = parseTimestampMs(traceEvents[0]?.ts)
  const lastTs = parseTimestampMs(traceEvents[traceEvents.length - 1]?.ts)
  const totalMs = firstTs != null && lastTs != null && lastTs >= firstTs
    ? lastTs - firstTs
    : null
  return { totalMs, stageCount: collectStageEvents(traceEvents).length }
}

function extractExecutionSummary(traceEvents = [], totalResults) {
  const execution = traceEvents.find(e => e.stage === 'execution')
  const verification = traceEvents.find(e => e.stage === 'verification')
  return {
    rowsReturned: execution?.payload?.row_count ?? totalResults ?? 0,
    verificationStatus: verification?.payload?.status || 'ok',
    warnings: verification?.payload?.warnings || [],
  }
}

// ─── Smart payload renderer — human-readable, no raw JSON ──────────────────
function renderPayload(stage, payload) {
  if (!payload || Object.keys(payload).length === 0) return null
  const p = payload

  if (stage === 'planner') {
    const parts = []
    if (p.intent) parts.push(`Intent: ${p.intent}`)
    if (p.entity_type) parts.push(`Entity: ${p.entity_type}${p.entity_id ? ` (${p.entity_id})` : ''}`)
    if (p.metric) parts.push(`Metric: ${p.metric}`)
    if (p.group_by) parts.push(`Group by: ${p.group_by}`)
    return parts.length ? parts.join(' · ') : null
  }

  if (stage === 'guard_pass' || stage === 'guard_reject') {
    const parts = []
    if (p.intent) parts.push(p.intent)
    if (p.reason) parts.push(p.reason)
    return parts.join(' — ') || null
  }

  if (stage === 'execution') {
    const parts = []
    if (p.row_count != null) parts.push(`${p.row_count} row${p.row_count !== 1 ? 's' : ''} returned`)
    if (p.duration_ms != null) parts.push(`${p.duration_ms}ms`)
    if (p.cached) parts.push('cached')
    return parts.join(' · ') || null
  }

  if (stage === 'verification') {
    const parts = []
    if (p.status) parts.push(`Status: ${p.status}`)
    if (Array.isArray(p.warnings) && p.warnings.length > 0) {
      parts.push(`${p.warnings.length} warning${p.warnings.length > 1 ? 's' : ''}`)
    }
    return parts.join(' · ') || null
  }

  if (stage === 'response') {
    if (p.method) return `Method: ${p.method}`
    return null
  }

  // Fallback: pick first 2 string/number values
  const readable = Object.entries(p)
    .filter(([, v]) => v != null && typeof v !== 'object')
    .slice(0, 2)
    .map(([k, v]) => `${k}: ${v}`)
    .join(' · ')
  return readable || null
}

// ─── Component ──────────────────────────────────────────────────────────────
export default function AgentTracePanel({ intent, plan, verification, traceEvents, sql, totalResults }) {
  const [sqlCopied, setSqlCopied] = useState(false)
  const eventsByStage = collectStageEvents(traceEvents)
  const executionSummary = extractExecutionSummary(traceEvents, totalResults)
  const metrics = computeTraceMetrics(traceEvents)
  const hasFallback = eventsByStage.length === 0

  const intentLabel = plan?.intent || intent || 'analyze'
  const latencyLabel = metrics.totalMs != null ? `${metrics.totalMs}ms` : null

  const handleCopySql = async () => {
    if (!sql) return
    try {
      await navigator.clipboard.writeText(sql)
      setSqlCopied(true)
      setTimeout(() => setSqlCopied(false), 1400)
    } catch {
      setSqlCopied(false)
    }
  }

  // Build steps: either real events or a minimal skeleton
  const steps = hasFallback
    ? [
        { stage: 'planner', label: 'Plan', symbol: '✓', badgeClass: 'trace-badge trace-badge--passed', description: `Intent: ${intentLabel}`, payload: null },
        { stage: 'execution', label: 'Execute', symbol: '✓', badgeClass: 'trace-badge trace-badge--passed', description: `${totalResults ?? 0} results`, payload: null },
      ]
    : eventsByStage.map(ev => {
        const config = ev.config || { label: ev.stage, description: '' }
        const isGuardReject = ev.stage === 'guard_reject'
        const isVerifyWarn = ev.stage === 'verification' && verification?.status === 'warning'
        const status = isGuardReject ? 'blocked' : isVerifyWarn ? 'warning' : 'passed'
        const payloadText = renderPayload(ev.stage, ev.payload)
        return {
          stage: ev.stage,
          label: config.label,
          symbol: getBadgeSymbol(status),
          badgeClass: getBadgeClass(status),
          description: config.description,
          payload: payloadText,
          ts: ev.ts,
        }
      })

  return (
    <div className="trace-panel">
      <div className="trace-header">Agent Pipeline</div>

      {/* Summary meta strip */}
      <div className="trace-meta">
        <strong>{intentLabel}</strong>
        {' · '}
        {totalResults != null && <><strong>{totalResults}</strong> result{totalResults !== 1 ? 's' : ''}{' · '}</>}
        {latencyLabel && <><strong>{latencyLabel}</strong>{' · '}</>}
        <span>{hasFallback ? 2 : metrics.stageCount} stages</span>
      </div>

      {/* Stepper */}
      {steps.map((step, idx) => (
        <div className="trace-step" key={`${step.stage}-${idx}`}>
          <span className={step.badgeClass}>{step.symbol}</span>
          <div className="trace-step__body">
            <div className="trace-step__title">
              {step.label}
              {step.ts && (
                <span style={{ fontWeight: 400, marginLeft: 4, color: '#94a3b8', fontSize: '10px' }}>
                  {new Date(step.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
              )}
            </div>
            {step.payload && (
              <div className="trace-step__payload">{step.payload}</div>
            )}
          </div>
        </div>
      ))}

      {/* SQL block with copy */}
      {sql && (
        <div style={{ marginTop: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
            <div className="trace-header" style={{ marginBottom: 0 }}>SQL</div>
            <button
              type="button"
              className={`message__copy-btn${sqlCopied ? ' message__copy-btn--copied' : ''}`}
              onClick={handleCopySql}
            >
              {sqlCopied ? '✓ Copied' : '⎘ Copy'}
            </button>
          </div>
          <pre className="trace-sql">{sql}</pre>
        </div>
      )}

      {/* Verification warnings */}
      {(executionSummary.warnings.length > 0 || (verification?.warnings?.length > 0)) && (
        <ul className="trace-warnings">
          {(verification?.warnings || executionSummary.warnings).map((w, i) => (
            <li key={i}>{w}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
