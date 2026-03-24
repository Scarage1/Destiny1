import React from 'react'

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
  const stageMap = {
    planner: { label: 'Planner', status: 'passed' },
    guard_pass: { label: 'Guard', status: 'passed' },
    guard_reject: { label: 'Guard', status: 'blocked' },
    query_agent: { label: 'Query', status: 'passed' },
    execution: { label: 'Execution', status: 'passed' },
    verification: { label: 'Verify', status: 'passed' },
    response: { label: 'Response', status: 'passed' },
  }

  const rows = []
  const seen = new Set()

  for (const ev of traceEvents) {
    if (!stageMap[ev.stage]) continue
    if (seen.has(ev.stage)) continue
    rows.push({ ...ev, config: stageMap[ev.stage] })
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

  return {
    totalMs,
    stageCount: collectStageEvents(traceEvents).length,
  }
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

export default function AgentTracePanel({ intent, plan, verification, traceEvents, sql, totalResults }) {
  const eventsByStage = collectStageEvents(traceEvents)
  const executionSummary = extractExecutionSummary(traceEvents, totalResults)
  const metrics = computeTraceMetrics(traceEvents)
  const intentJson = {
    intent: plan?.intent || intent || 'analyze',
    entity_type: plan?.entity_type || null,
    entity_id: plan?.entity_id || null,
    metric: plan?.metric || null,
    group_by: plan?.group_by || null,
    verification: plan?.verification || 'required',
  }

  return (
    <div className="trace-panel">
      <div className="trace-header">Agent Pipeline</div>
      <div className="trace-meta">
        intent: <strong>{intent || 'analyze'}</strong>
        {' · '}results: <strong>{totalResults ?? 0}</strong>
        {' · '}stages: <strong>{metrics.stageCount}</strong>
        {' · '}latency: <strong>{metrics.totalMs != null ? `${metrics.totalMs}ms` : 'n/a'}</strong>
      </div>

      <div className="trace-step">
        <span className="trace-badge trace-badge--passed">✓</span>
        <div className="trace-step__body">
          <div className="trace-step__title">Intent JSON</div>
          <div className="trace-step__payload">{JSON.stringify(intentJson)}</div>
        </div>
      </div>

      {eventsByStage.map((ev, idx) => {
        const config = ev.config || { label: ev.stage, status: 'passed' }
        const status = ev.stage === 'verification' && verification?.status === 'warning'
          ? 'warning'
          : config.status

        return (
          <div className="trace-step" key={`${ev.stage}-${idx}`}>
            <span className={getBadgeClass(status)}>{getBadgeSymbol(status)}</span>
            <div className="trace-step__body">
              <div className="trace-step__title">{config.label}{ev.ts ? ` · ${new Date(ev.ts).toLocaleTimeString()}` : ''}</div>
              <div className="trace-step__payload">{JSON.stringify(ev.payload || {})}</div>
            </div>
          </div>
        )
      })}

      <div className="trace-step">
        <span className="trace-badge trace-badge--passed">✓</span>
        <div className="trace-step__body">
          <div className="trace-step__title">Execution Summary</div>
          <div className="trace-step__payload">
            {JSON.stringify({
              rows_returned: executionSummary.rowsReturned,
              verification_status: executionSummary.verificationStatus,
              warnings_count: executionSummary.warnings.length,
            })}
          </div>
        </div>
      </div>

      {sql && <pre className="trace-sql">{sql}</pre>}
      {verification?.warnings?.length > 0 && (
        <ul className="trace-warnings">
          {verification.warnings.map((w, i) => <li key={i}>{w}</li>)}
        </ul>
      )}
    </div>
  )
}
