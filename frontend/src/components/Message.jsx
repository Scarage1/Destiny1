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

export default function Message({ msg, onSend, advancedMode = false, onCopy }) {
  const [showSql, setShowSql]       = useState(false)
  const [copied, setCopied]         = useState(false)
  const [showDetails, setShowDetails] = useState(false)
  const shouldAutoOpenTrace = ['blocked', 'rejected', 'error'].includes(msg.status)
  const [showTrace, setShowTrace]   = useState(shouldAutoOpenTrace)
  const isClarification = msg.status === 'clarification'

  const roleClass   = msg.role === 'user' ? 'message--user' : 'message--system'
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
            <div className="message__sql-label">SQL</div>
            {msg.sql}
          </div>
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

        {showTrace && msg.traceId && (
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
}
