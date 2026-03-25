import React, { useState } from 'react'
import AgentTracePanel from './AgentTracePanel'
import { exportResults } from '../utils/export'

function formatIntentLayer(plan, intent) {
  const p = plan || {}
  return {
    intent: p.intent || intent || 'analyze',
    entityType: p.entity_type || '—',
    entityId: p.entity_id || '—',
    metric: p.metric || '—',
    groupBy: p.group_by || '—',
  }
}

function getClarificationSuggestions(plan) {
  const intent = plan?.intent
  if (intent === 'status_lookup') return ['Check status for invoice 90504204', 'Check status for sales order 740509']
  if (intent === 'trace_flow')   return ['Trace invoice 90504204', 'Trace sales order 740509']
  return ['Top 5 customers by net amount', 'Show incomplete orders', 'Which deliveries were never billed?']
}

function getResultTitle(intent) {
  if (intent === 'trace_flow')     return 'Flow Trace'
  if (intent === 'detect_anomaly') return 'Process Issues'
  if (intent === 'status_lookup') return 'Document Status'
  return 'Top Results'
}

/* ── Sortable results table (T11) ── */
function ResultsTable({ results, columns }) {
  const [sortKey, setSortKey]   = useState(null)
  const [sortDir, setSortDir]   = useState('asc')
  if (!results || results.length === 0) return null

  const cols = columns || Object.keys(results[0])

  const sorted = sortKey
    ? [...results].sort((a, b) => {
        const av = a[sortKey], bv = b[sortKey]
        const n = (v) => (typeof v === 'number' ? v : parseFloat(v) || 0)
        const cmp = typeof av === 'number' || typeof bv === 'number'
          ? n(av) - n(bv)
          : String(av ?? '').localeCompare(String(bv ?? ''))
        return sortDir === 'asc' ? cmp : -cmp
      })
    : results

  const handleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('asc') }
  }

  return (
    <div className="results-table-wrap">
      <table className="results-table">
        <thead>
          <tr>
            {cols.map(col => (
              <th key={col} onClick={() => handleSort(col)} className="results-table__th">
                {col}
                {sortKey === col ? (sortDir === 'asc' ? ' ↑' : ' ↓') : ''}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => (
            <tr key={i} className="results-table__row">
              {cols.map(col => (
                <td key={col} className="results-table__td">
                  {row[col] == null ? '—' : String(row[col])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ── Suggestion pills (T7) ── */
function SuggestionPills({ suggestions, onSend }) {
  if (!suggestions || suggestions.length === 0) return null
  return (
    <div className="suggestions-row">
      <span className="suggestions-label">Try next:</span>
      {suggestions.map((s, i) => (
        <button key={i} type="button" className="suggestion-pill" onClick={() => onSend?.(s)}>
          {s}
        </button>
      ))}
    </div>
  )
}


/* ── SQL Explain Toggle (T20) ── */
const EXPLAIN_TEMPLATES = {
  trace_flow:     (plan) => `This query traces the end-to-end O2C journey for ${plan?.entity_type || "the document"} ${plan?.entity_id || ""}, joining sales orders → deliveries → billing documents → payments to show the full lifecycle status.`,
  detect_anomaly: (plan) => `This query detects process anomalies${plan?.anomaly_sub_type ? ` (${plan.anomaly_sub_type.replaceAll("_", " ")})` : ""} by looking for records where expected downstream steps are missing — using LEFT JOIN to surface NULL gaps.`,
  status_lookup:  (plan) => `This query looks up the current status of ${plan?.entity_type || "the document"} ${plan?.entity_id || ""} and checks if it has a linked payment or clearing entry.`,
  analyze:        (plan) => `This query aggregates ${plan?.metric || "records"} by ${plan?.group_by || "category"}, ${plan?.operation === "max" ? "ranking highest first" : "ordered by volume"}, limited to the top results.`,
  list:           (_)    => "This query lists records matching the requested filter criteria, ordered by the most relevant column.",
}

function SqlExplainer({ plan, sql }) {
  const [show, setShow] = useState(false)
  if (!plan || !sql) return null
  const intent = plan.intent || "analyze"
  const explainFn = EXPLAIN_TEMPLATES[intent] || EXPLAIN_TEMPLATES.analyze
  return (
    <div className="sql-explain-wrap">
      <button
        type="button"
        className="message__toggle"
        onClick={() => setShow(!show)}
        aria-expanded={show}
      >
        {show ? "▾ Hide Explain" : "▸ Explain SQL"}
      </button>
      {show && (
        <div className="sql-explain-text">
          <span className="sql-explain-icon">🔍</span>
          {explainFn(plan)}
        </div>
      )}
    </div>
  )
}

const Message = React.memo(function Message({ msg, onSend, advancedMode = false, onCopy }) {
  const [showSql, setShowSql]       = useState(false)
  const [copied, setCopied]         = useState(false)
  const [showDetails, setShowDetails] = useState(false)
  const shouldAutoOpenTrace = ['blocked', 'rejected', 'error'].includes(msg.status)
  const [showTrace, setShowTrace]   = useState(shouldAutoOpenTrace)
  const isClarification = msg.status === 'clarification'

  const roleClass   = msg.role === 'user' ? 'message--user' : 'message--system'

  // W1-4: Loading skeleton — shown while API call is in-flight
  if (msg._loading) {
    return (
      <div className="message message--system">
        <div className="message__loading">
          <span /><span /><span />
        </div>
      </div>
    )
  }

  const statusClass = msg.status === 'rejected'     ? ' message--rejected'
    : msg.status === 'error'         ? ' message--error'
    : msg.status === 'clarification' ? ' message--clarification'
    : ''

  const intentLayer = formatIntentLayer(msg.plan, msg.intent)
  const clarificationSuggestions = isClarification ? getClarificationSuggestions(msg.plan) : []
  const traceLabel  = advancedMode ? 'Trace' : 'Explain'
  const resultTitle = getResultTitle(intentLayer.intent)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(msg.text || '')
      setCopied(true)
      onCopy?.('Copied answer')
      setTimeout(() => setCopied(false), 1200)
    } catch { setCopied(false) }
  }

  const hasResults = msg.results && msg.results.length > 0

  return (
    <div className={`message ${roleClass}${statusClass}`}>
      <div className="message__bubble">
        <div className="message__text">{msg.text}</div>

        {/* Result info strip — system messages only, not clarifications */}
        {msg.role !== 'user' && !isClarification && (
          <div className="message__trust-strip">
            {msg.totalResults != null && (
              <span className="message__results-badge">
                {msg.totalResults} result{msg.totalResults !== 1 ? 's' : ''}
              </span>
            )}
            <button type="button"
              className={`message__copy-btn${copied ? ' message__copy-btn--copied' : ''}`}
              onClick={handleCopy}>
              {copied ? '✓ Copied' : '⎘ Copy'}
            </button>

            {/* T9: Export buttons */}
            {hasResults && (
              <>
                <button type="button" className="message__copy-btn"
                  title="Download as CSV"
                  onClick={() => exportResults(msg.results, msg.result_columns, 'csv')}>
                  ↓ CSV
                </button>
                <button type="button" className="message__copy-btn"
                  title="Download as JSON"
                  onClick={() => exportResults(msg.results, msg.result_columns, 'json')}>
                  ↓ JSON
                </button>
              </>
            )}
          </div>
        )}

        {/* T11: Structured results table */}
        {hasResults && (
          <details className="results-section" open>
            <summary className="results-section__title">
              {resultTitle} <span className="results-count">({msg.results.length})</span>
            </summary>
            <ResultsTable results={msg.results} columns={msg.result_columns} />
          </details>
        )}

        {/* Collapsible SQL + Trace — skip for clarification messages */}
        {(msg.sql || msg.traceId) && !isClarification && (
          <>
            <button className="message__toggle" type="button"
              onClick={() => setShowDetails(!showDetails)} aria-expanded={showDetails}>
              {showDetails ? '▾ Hide Details' : '▸ Show Details'}
            </button>
            {showDetails && (
              <div className="message__detail-actions">
                {msg.sql && (
                  <button className="message__toggle" type="button"
                    onClick={() => setShowSql(!showSql)} aria-expanded={showSql}>
                    {showSql ? '▾ Hide SQL' : '▸ Show SQL'}
                  </button>
                )}
                {msg.traceId && (
                  <button className="message__toggle" type="button"
                    onClick={() => setShowTrace(!showTrace)} aria-expanded={showTrace}>
                    {showTrace ? `▾ Hide ${traceLabel}` : `▸ Show ${traceLabel}`}
                  </button>
                )}
              </div>
            )}
          </>
        )}

        {showSql && msg.sql && (
          <div className="message__sql">
            {/* W3-2: Plain-language summary for business users */}
            <div className="message__sql-summary">
              {(() => {
                const { intent, entity_type, entity_id } = msg.plan || {}
                if (intent === 'trace_flow')
                  return `Traced full O2C lifecycle for ${entity_type || 'document'} ${entity_id || ''}`
                if (intent === 'detect_anomaly')
                  return `Scanned for anomalies in ${entity_type || 'O2C'} records`
                if (intent === 'compare_analytics')
                  return `Compared performance across ${entity_type || 'groups'}`
                if (intent === 'status_lookup')
                  return `Looked up current status of ${entity_type || 'document'} ${entity_id || ''}`
                return `Analyzed ${entity_type || 'O2C'} data across ${msg.totalResults ?? 0} record(s)`
              })()}
            </div>
            {/* Developer SQL — collapsed by default */}
            <details className="message__sql-details">
              <summary className="message__sql-dev-toggle">Developer SQL</summary>
              <pre className="message__sql-code">{msg.sql}</pre>
            </details>
          </div>
        )}

        {/* T20: SQL explain toggle */}
        {showSql && msg.sql && (
          <SqlExplainer plan={msg.plan} sql={msg.sql} />
        )}

        {/* T7: AI-suggested follow-up queries */}
        {msg.role !== 'user' && !isClarification && (
          <SuggestionPills suggestions={msg.suggestions} onSend={onSend} />
        )}

        {/* Clarification suggestions */}
        {clarificationSuggestions.length > 0 && (
          <div className="clarification-suggestions">
            {clarificationSuggestions.map((q, idx) => (
              <button key={`${idx}-${q}`} className="clarification-suggestion-btn"
                type="button" onClick={() => onSend?.(q)}>{q}</button>
            ))}
          </div>
        )}

        {/* W1-2: Hide agent trace on guard rejections — content already in bubble */}
        {showTrace && msg.traceId && msg.status !== 'rejected' && (
          <AgentTracePanel
            intent={msg.intent}
            plan={msg.plan}
            verification={msg.verification}
            traceEvents={msg.traceEvents || []}
            sql={msg.sql}
            totalResults={msg.totalResults}
          />
        )}
      </div>
    </div>
  )
})

export default Message
