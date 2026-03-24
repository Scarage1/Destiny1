import { describe, expect, it, vi, afterEach } from 'vitest'
import { askQuery, fetchGraphOverview, fetchGraphSubgraph, fetchMetrics, fetchNodeDetails, fetchNodeNeighbors, fetchTrace } from '../api'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('frontend api client', () => {
  it('fetchGraphOverview returns parsed payload', async () => {
    const payload = { nodes: [], edges: [], stats: {} }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => payload }),
    )

    const result = await fetchGraphOverview()
    expect(result).toEqual(payload)
  })

  it('fetchNodeDetails throws for 404', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => ({}) }),
    )

    await expect(fetchNodeDetails('SalesOrder:1')).rejects.toThrow('Node not found')
  })

  it('fetchNodeNeighbors returns neighbors payload', async () => {
    const payload = { nodes: [{ id: 'SalesOrder:1' }], edges: [] }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => payload }),
    )

    const result = await fetchNodeNeighbors('SalesOrder:1')
    expect(result.nodes).toHaveLength(1)
  })

  it('fetchGraphSubgraph posts payload and returns subgraph', async () => {
    const payload = { nodes: [{ id: 'BillingDocument:1' }], edges: [], stats: { seed_count: 1 } }
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => payload })
    vi.stubGlobal('fetch', fetchMock)

    const result = await fetchGraphSubgraph(['BillingDocument:1'], 1, 100)
    expect(fetchMock).toHaveBeenCalledOnce()
    expect(fetchMock.mock.calls[0][0]).toContain('/api/graph/subgraph')
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
    expect(result.stats.seed_count).toBe(1)
  })

  it('askQuery posts query and returns payload', async () => {
    const payload = {
      answer: 'ok',
      status: 'success',
      trace_id: 'trace-1',
      query: 'SELECT 1',
      result_columns: [],
      total_results: 0,
      referenced_nodes: [],
      results: [],
    }

    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => payload })
    vi.stubGlobal('fetch', fetchMock)

    const result = await askQuery('hello', 'conv-1')

    expect(fetchMock).toHaveBeenCalledOnce()
    expect(fetchMock.mock.calls[0][0]).toContain('/api/query/ask')
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
    expect(fetchMock.mock.calls[0][1].body).toContain('"conversation_id":"conv-1"')
    expect(result.status).toBe('success')
  })

  it('fetchTrace returns trace payload', async () => {
    const payload = { trace_id: 't-1', events: [{ stage: 'planner' }] }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => payload }),
    )

    const result = await fetchTrace('t-1')
    expect(result.trace_id).toBe('t-1')
    expect(result.events).toHaveLength(1)
  })

  it('fetchMetrics returns runtime metrics payload', async () => {
    const payload = { success_rate: 0.9, p95_latency_ms: 40 }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => payload }),
    )

    const result = await fetchMetrics()
    expect(result.success_rate).toBe(0.9)
    expect(result.p95_latency_ms).toBe(40)
  })
})
