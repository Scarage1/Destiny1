import { describe, expect, it } from 'vitest'
import { collectStageEvents, computeTraceMetrics, getBadgeClass, getBadgeSymbol } from '../components/AgentTracePanel'

describe('agent trace panel helpers', () => {
  it('maps status to badge class', () => {
    expect(getBadgeClass('passed')).toContain('trace-badge--passed')
    expect(getBadgeClass('blocked')).toContain('trace-badge--blocked')
    expect(getBadgeClass('warning')).toContain('trace-badge--warning')
  })

  it('maps status to badge symbol', () => {
    expect(getBadgeSymbol('passed')).toBe('✓')
    expect(getBadgeSymbol('blocked')).toBe('✗')
    expect(getBadgeSymbol('warning')).toBe('⚠')
  })

  it('collects only first event per known stage', () => {
    const rows = collectStageEvents([
      { stage: 'planner', payload: { a: 1 } },
      { stage: 'planner', payload: { a: 2 } },
      { stage: 'guard_pass', payload: {} },
      { stage: 'unknown_stage', payload: {} },
      { stage: 'response', payload: {} },
    ])

    expect(rows).toHaveLength(3)
    expect(rows[0].stage).toBe('planner')
    expect(rows[1].stage).toBe('guard_pass')
    expect(rows[2].stage).toBe('response')
  })

  it('computes trace metrics from timestamps', () => {
    const metrics = computeTraceMetrics([
      { stage: 'planner', ts: '2026-03-24T10:00:00.000Z', payload: {} },
      { stage: 'guard_pass', ts: '2026-03-24T10:00:00.050Z', payload: {} },
      { stage: 'response', ts: '2026-03-24T10:00:00.120Z', payload: {} },
    ])

    expect(metrics.stageCount).toBe(3)
    expect(metrics.totalMs).toBe(120)
  })
})
