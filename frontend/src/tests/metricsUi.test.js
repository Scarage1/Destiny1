import { describe, expect, it } from 'vitest'
import { formatLatencyMs, formatRate, getMetricsDetailRows } from '../utils/metricsUi'

describe('metrics ui helpers', () => {
  it('formats rates and latency with placeholders', () => {
    expect(formatRate(0.934)).toBe('93%')
    expect(formatRate(undefined)).toBe('--')
    expect(formatLatencyMs(42)).toBe('42ms')
    expect(formatLatencyMs(null)).toBe('--')
  })

  it('builds runtime detail rows', () => {
    const rows = getMetricsDetailRows({
      request_count: 9,
      success_rate: 0.77,
      guard_rejection_rate: 0.11,
      clarification_rate: 0.05,
      deterministic_hit_rate: 0.64,
      llm_fallback_rate: 0.08,
      p95_latency_ms: 137,
    })

    expect(rows).toHaveLength(7)
    expect(rows[0]).toEqual({ label: 'Requests', value: '9' })
    expect(rows[1]).toEqual({ label: 'Success Rate', value: '77%' })
    expect(rows[6]).toEqual({ label: 'P95 Latency', value: '137ms' })
  })
})
