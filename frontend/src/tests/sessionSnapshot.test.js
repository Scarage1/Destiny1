import { describe, expect, it } from 'vitest'
import { buildSessionSnapshot, makeSnapshotFilename, reviveMessagesFromSnapshot } from '../utils/sessionSnapshot'

describe('session snapshot utilities', () => {
  it('builds a normalized snapshot payload', () => {
    const snapshot = buildSessionSnapshot({
      conversationId: 'conv-123',
      uiMode: 'advanced',
      runtimeMetrics: { success_rate: 0.91 },
      queryHistory: [{ id: 'q1', text: 'Top customers' }],
      messages: [
        {
          role: 'system',
          text: 'Done',
          status: 'success',
          intent: 'aggregate',
          totalResults: 5,
          traceId: 'trace-1',
          plan: { intent: 'aggregate' },
          referencedNodes: ['Customer:C100'],
        },
      ],
    })

    expect(snapshot.version).toBe('1.0')
    expect(snapshot.conversation_id).toBe('conv-123')
    expect(snapshot.ui_mode).toBe('advanced')
    expect(snapshot.messages).toHaveLength(1)
    expect(snapshot.messages[0].total_results).toBe(5)
    expect(snapshot.messages[0].referenced_nodes).toEqual(['Customer:C100'])
  })

  it('creates a safe filename', () => {
    expect(makeSnapshotFilename('conv-1')).toBe('o2c-session-conv-1.json')
    expect(makeSnapshotFilename('conv:1/unsafe')).toBe('o2c-session-conv1unsafe.json')
  })

  it('revives messages from persisted snapshot shape', () => {
    const revived = reviveMessagesFromSnapshot([
      {
        role: 'system',
        text: 'ok',
        total_results: 2,
        trace_id: 't1',
        sql: 'SELECT 1',
        trace_events: [{ stage: 'planner', payload: {} }],
      },
    ])
    expect(revived).toHaveLength(1)
    expect(revived[0].totalResults).toBe(2)
    expect(revived[0].traceId).toBe('t1')
    expect(revived[0].sql).toBe('SELECT 1')
    expect(revived[0].traceEvents).toHaveLength(1)
  })
})
