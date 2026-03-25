/**
 * T10: Query History Panel
 *
 * Persists the last 20 queries in localStorage and renders them
 * as a collapsible slide-in panel on the right side of the chat panel.
 */
import React, { useState, useEffect } from 'react'

const HISTORY_KEY = 'o2c_query_history'
const MAX_HISTORY = 20

export interface HistoryEntry {
  id: string
  query: string
  intent: string
  status: string
  ts: number
}

/** Read from localStorage */
function readHistory(): HistoryEntry[] {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]')
  } catch {
    return []
  }
}

/** Persist to localStorage */
function writeHistory(entries: HistoryEntry[]): void {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(entries.slice(0, MAX_HISTORY)))
  } catch { /* storage full — ignore */ }
}

/** Add a new query to history — deduplicates consecutive identical queries */
export function addToHistory(entry: Omit<HistoryEntry, 'id' | 'ts'>): void {
  const existing = readHistory()
  if (existing[0]?.query === entry.query) return // no consecutive dupe
  const next: HistoryEntry = { ...entry, id: `h-${Date.now()}`, ts: Date.now() }
  writeHistory([next, ...existing])
}

/** Clear all history */
export function clearHistory(): void {
  try { localStorage.removeItem(HISTORY_KEY) } catch { /* ignore */ }
}

// ── Intent → label helper ──────────────────────────────────────────────────

function intentBadge(intent: string) {
  const map: Record<string, { label: string; cls: string }> = {
    trace_flow:        { label: 'Trace',   cls: 'hpanel__badge--trace'   },
    detect_anomaly:    { label: 'Anomaly', cls: 'hpanel__badge--anomaly' },
    status_lookup:     { label: 'Status',  cls: 'hpanel__badge--status'  },
    analyze:           { label: 'Analyze', cls: 'hpanel__badge--analyze' },
    compare_analytics: { label: 'Compare', cls: 'hpanel__badge--compare' },
  }
  const { label, cls } = map[intent] ?? { label: intent, cls: '' }
  return <span className={`hpanel__badge ${cls}`}>{label}</span>
}

function relativeTime(ts: number): string {
  const diff = Date.now() - ts
  if (diff < 60_000)  return 'just now'
  if (diff < 3_600_000) return `${Math.round(diff / 60_000)}m ago`
  if (diff < 86_400_000) return `${Math.round(diff / 3_600_000)}h ago`
  return new Date(ts).toLocaleDateString()
}

// ── Component ──────────────────────────────────────────────────────────────

interface HistoryPanelProps {
  onSelect: (query: string) => void
}

export default function QueryHistoryPanel({ onSelect }: HistoryPanelProps) {
  const [open, setOpen] = useState(false)
  const [entries, setEntries] = useState<HistoryEntry[]>([])

  // Refresh from localStorage whenever panel opens
  useEffect(() => {
    if (open) setEntries(readHistory())
  }, [open])

  // Also refresh when a new message is added (storage event from same tab)
  useEffect(() => {
    const handleStorage = () => setEntries(readHistory())
    window.addEventListener('o2c_history_update', handleStorage)
    return () => window.removeEventListener('o2c_history_update', handleStorage)
  }, [])

  const handleClear = () => {
    clearHistory()
    setEntries([])
  }

  return (
    <>
      {/* Trigger button — always visible */}
      <button
        type="button"
        className="hpanel__trigger"
        onClick={() => setOpen(o => !o)}
        title="Query history"
        aria-label="Toggle query history"
      >
        🕐
        {entries.length > 0 && !open && (
          <span className="hpanel__trigger-count">{entries.length}</span>
        )}
      </button>

      {/* Slide-in panel */}
      <div className={`hpanel${open ? ' hpanel--open' : ''}`} aria-hidden={!open}>
        <div className="hpanel__header">
          <span className="hpanel__title">History</span>
          <div className="hpanel__header-actions">
            {entries.length > 0 && (
              <button type="button" className="hpanel__clear" onClick={handleClear}>
                Clear
              </button>
            )}
            <button type="button" className="hpanel__close" onClick={() => setOpen(false)}>
              ✕
            </button>
          </div>
        </div>

        <div className="hpanel__list">
          {entries.length === 0 ? (
            <div className="hpanel__empty">No queries yet</div>
          ) : (
            entries.map(e => (
              <button
                key={e.id}
                type="button"
                className={`hpanel__item${e.status === 'error' ? ' hpanel__item--error' : ''}`}
                onClick={() => { onSelect(e.query); setOpen(false) }}
              >
                <div className="hpanel__item-top">
                  {intentBadge(e.intent)}
                  <span className="hpanel__item-time">{relativeTime(e.ts)}</span>
                </div>
                <div className="hpanel__item-query">{e.query}</div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Backdrop on mobile */}
      {open && (
        <div className="hpanel__backdrop" onClick={() => setOpen(false)} />
      )}
    </>
  )
}
