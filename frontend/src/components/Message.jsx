import React, { useEffect, useState } from 'react'
import AgentTracePanel from './AgentTracePanel'

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
  if (intent === 'status_lookup') {
    return [
      'Check status for invoice 90504204',
      'Check status for sales order 740509',
      'Check payment status for invoice 90504204',
    ]
  }
  if (intent === 'trace_flow') {
    return [
      'Trace invoice 90504204',
      'Trace invoice 91150187',
      'Trace sales order 740509',
    ]
  }
  return [
    'Top 5 customers by net amount',
    'Show incomplete orders',
    'Trace the full flow of a billing document',
  ]
}

function buildMarkdownPayload(msg, intentLayer) {
  const lines = []
  lines.push('## O2C Query Result')
  lines.push('')
  lines.push(`**Status:** ${msg.status || 'success'}`)
  lines.push(`**Intent:** ${intentLayer.intent}`)
  if (msg.totalResults != null) {
    lines.push(`**Results:** ${msg.totalResults}`)
  }
  if (msg.traceId) {
    lines.push(`**Trace ID:** ${msg.traceId}`)
  }
  lines.push('')
  lines.push('### Answer')
  lines.push(msg.text || '')

  if (msg.sql) {
    lines.push('')
    lines.push('### SQL')
    lines.push('```sql')
    lines.push(msg.sql)
    lines.push('```')
  }

  return lines.join('\n')
}

function getResultTitle(intent) {
  if (intent === 'trace_flow') return 'Flow Trace'
  if (intent === 'detect_anomaly') return 'Process Issues'
  if (intent === 'status_lookup') return 'Document Status'
  return 'Top Results'
}

export default function Message({ msg, onSend, advancedMode = false, onCopy }) {
  const [showSql, setShowSql] = useState(false)
  const [copied, setCopied] = useState(false)
  const [copiedMd, setCopiedMd] = useState(false)
  const [showDetails, setShowDetails] = useState(false)
  const shouldAutoOpenTrace = ['blocked', 'rejected', 'error'].includes(msg.status)
  const [showTrace, setShowTrace] = useState(shouldAutoOpenTrace)
  // Don't show details/trace controls for clarification messages — they have no SQL/trace
  const isClarification = msg.status === 'clarification'

  useEffect(() => {
    if (shouldAutoOpenTrace) {
      setShowTrace(true)
    }
  }, [shouldAutoOpenTrace])

  const roleClass = msg.role === 'user' ? 'message--user' : 'message--system'
  const statusClass = msg.status === 'rejected'
    ? ' message--rejected'
    : msg.status === 'error'
      ? ' message--error'
      : msg.status === 'clarification'
        ? ' message--clarification'
        : ''
  const intentLayer = formatIntentLayer(msg.plan, msg.intent)
  const clarificationSuggestions = msg.status === 'clarification'
    ? getClarificationSuggestions(msg.plan)
    : []
  const traceLabel = advancedMode ? 'Trace' : 'Explain'
  const resultTitle = getResultTitle(intentLayer.intent)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(msg.text || '')
      setCopied(true)
      onCopy?.('Copied answer')
      setTimeout(() => setCopied(false), 1200)
    } catch {
      setCopied(false)
    }
  }

  const handleCopyMarkdown = async () => {
    try {
      const payload = buildMarkdownPayload(msg, intentLayer)
      await navigator.clipboard.writeText(payload)
      setCopiedMd(true)
      onCopy?.('Copied markdown')
      setTimeout(() => setCopiedMd(false), 1200)
    } catch {
      setCopiedMd(false)
    }
  }

  return (
    <div className={`message ${roleClass}${statusClass}`}>
      <div className="message__bubble">
        <div className="message__text">{msg.text}</div>

        {/* Result info strip — system messages only, not clarifications */}
        {msg.role !== 'user' && msg.status !== 'clarification' && (
          <div className="message__trust-strip">
            {msg.totalResults != null && (
              <span className="message__results-badge">
                {msg.totalResults} result{msg.totalResults !== 1 ? 's' : ''}
              </span>
            )}
            <button
              type="button"
              className={`message__copy-btn${copied ? ' message__copy-btn--copied' : ''}`}
              onClick={handleCopy}
            >
              {copied ? '✓ Copied' : '⎘ Copy'}
            </button>
            {advancedMode && (
              <button
                type="button"
                className={`message__copy-btn${copiedMd ? ' message__copy-btn--copied' : ''}`}
                onClick={handleCopyMarkdown}
              >
                {copiedMd ? '✓ MD' : '⎘ MD'}
              </button>
            )}
          </div>
        )}

        {/* Intent layer — hidden by default, only shown in advanced mode */}
        {msg.role !== 'user' && (
          <div className={`message__intent-layer ${advancedMode ? 'message__intent-layer--visible' : ''}`}>
            <strong>Intent Layer:</strong> {intentLayer.intent} · entity: {intentLayer.entityType} ({intentLayer.entityId}) · metric: {intentLayer.metric} · group by: {intentLayer.groupBy}
          </div>
        )}

        {/* Collapsible details — skip for clarification messages */}
        {(msg.sql || msg.traceId) && !isClarification && (
          <>
            <button
              className="message__toggle"
              type="button"
              onClick={() => setShowDetails(!showDetails)}
              aria-expanded={showDetails}
            >
              {showDetails ? '▾ Hide Details' : '▸ Show Details'}
            </button>
            {showDetails && (
              <div className="message__detail-actions">
                {msg.sql && (
                  <button
                    className="message__toggle"
                    type="button"
                    onClick={() => setShowSql(!showSql)}
                    aria-expanded={showSql}
                  >
                    {showSql ? '▾ Hide SQL' : '▸ Show SQL'}
                  </button>
                )}
                {msg.traceId && (
                  <button
                    className="message__toggle"
                    type="button"
                    onClick={() => setShowTrace(!showTrace)}
                    aria-expanded={showTrace}
                  >
                    {showTrace ? `▾ Hide ${traceLabel}` : `▸ Show ${traceLabel}`}
                    {shouldAutoOpenTrace && <span className="trace-auto-pill">auto-opened</span>}
                  </button>
                )}
              </div>
            )}
          </>
        )}

        {/* SQL block */}
        {showSql && msg.sql && (
          <div className="message__sql">
            <div className="message__sql-label">SQL</div>
            {msg.sql}
          </div>
        )}

        {/* Clarification suggestions as pill buttons */}
        {clarificationSuggestions.length > 0 && (
          <div className="clarification-suggestions">
            {clarificationSuggestions.map((q, idx) => (
              <button
                key={`${idx}-${q}`}
                className="clarification-suggestion-btn"
                type="button"
                onClick={() => onSend?.(q)}
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {/* Agent trace panel */}
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
