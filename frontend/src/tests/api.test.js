import { describe, expect, it, vi, afterEach } from 'vitest'
import { askQuery, fetchGraphOverview, fetchNodeDetails, fetchNodeNeighbors } from '../api'

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

    const result = await askQuery('hello')

    expect(fetchMock).toHaveBeenCalledOnce()
    expect(fetchMock.mock.calls[0][0]).toContain('/api/query/ask')
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
    expect(result.status).toBe('success')
  })
})
