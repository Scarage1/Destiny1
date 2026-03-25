// @vitest-environment jsdom

import React from 'react'
import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Landing from '../pages/Landing'
import Workspace from '../pages/Workspace'

const WORKSPACE_SESSION_KEY = 'o2c_workspace_v1'

vi.mock('react-force-graph-2d', () => {
  const MockGraph = React.forwardRef(function MockGraph(_props, _ref) {
    return React.createElement('div', { 'data-testid': 'mock-graph' })
  })
  return { default: MockGraph }
})

const fetchGraphOverview = vi.fn()
const fetchNodeDetails = vi.fn()
const fetchNodeNeighbors = vi.fn()
const askQuery = vi.fn()
const fetchTrace = vi.fn()

vi.mock('../api', () => ({
  fetchGraphOverview: (...args) => fetchGraphOverview(...args),
  fetchNodeDetails: (...args) => fetchNodeDetails(...args),
  fetchNodeNeighbors: (...args) => fetchNodeNeighbors(...args),
  askQuery: (...args) => askQuery(...args),
  fetchTrace: (...args) => fetchTrace(...args),
}))

describe('route surfaces', () => {
  afterEach(() => {
    cleanup()
  })

  beforeEach(() => {
    sessionStorage.removeItem(WORKSPACE_SESSION_KEY)
    if (!Element.prototype.scrollIntoView) {
      Element.prototype.scrollIntoView = () => {}
    }

    fetchGraphOverview.mockReset()
    fetchNodeDetails.mockReset()
    fetchNodeNeighbors.mockReset()
    askQuery.mockReset()
    fetchTrace.mockReset()

    fetchGraphOverview.mockResolvedValue({
      nodes: [{ id: 'SalesOrder:1', type: 'SalesOrder' }],
      edges: [],
    })
    fetchNodeDetails.mockResolvedValue({ properties: {}, neighbors: {} })
    fetchNodeNeighbors.mockResolvedValue({ nodes: [], edges: [] })
    askQuery.mockResolvedValue({
      answer: 'Found 1 broken flow.',
      status: 'success',
      query: 'SELECT 1',
      total_results: 1,
      conversation_id: 'conv-1',
      intent: 'detect_anomaly',
      plan: { intent: 'detect_anomaly' },
      trace_id: 'trace-1',
      verification: { status: 'ok', warnings: [] },
      agent_trace: { trace_id: 'trace-1', events: [] },
      referenced_nodes: ['SalesOrder:1'],
    })
    fetchTrace.mockResolvedValue({ trace_id: 'trace-1', events: [] })
  })

  it('renders landing CTA to workspace', () => {
    render(React.createElement(MemoryRouter, null, React.createElement(Landing)))

    expect(screen.getByText('See how your business flows.')).toBeTruthy()
    const cta = screen.getAllByRole('link', { name: /Open (Demo|Workspace)/i })[0]
    expect(cta.getAttribute('href')).toBe('/workspace')
  })

  it('supports workspace query send lifecycle', async () => {
    render(React.createElement(MemoryRouter, null, React.createElement(Workspace)))

    const input = await screen.findByPlaceholderText('Ask about your O2C data…')
    fireEvent.change(input, { target: { value: 'Find broken flows' } })
    fireEvent.click(screen.getByTitle('Send'))

    await waitFor(() => {
      expect(screen.getByText('Find broken flows')).toBeTruthy()
      expect(screen.getByText('Found 1 broken flow.')).toBeTruthy()
    })
  })

  it('reuses conversation id for follow-up queries', async () => {
    askQuery
      .mockResolvedValueOnce({
        answer: 'Please specify a metric.',
        status: 'clarification',
        query: null,
        total_results: null,
        conversation_id: 'conv-followup',
        intent: 'analyze',
        plan: { intent: 'analyze' },
        trace_id: 'trace-a',
        verification: { status: 'skipped', warnings: ['Clarification required'] },
        agent_trace: { trace_id: 'trace-a', events: [] },
        referenced_nodes: [],
      })
      .mockResolvedValueOnce({
        answer: 'Using net amount now.',
        status: 'success',
        query: 'SELECT 1',
        total_results: 1,
        conversation_id: 'conv-followup',
        intent: 'analyze',
        plan: { intent: 'analyze' },
        trace_id: 'trace-b',
        verification: { status: 'ok', warnings: [] },
        agent_trace: { trace_id: 'trace-b', events: [] },
        referenced_nodes: [],
      })

    render(React.createElement(MemoryRouter, null, React.createElement(Workspace)))

    const input = await screen.findByPlaceholderText('Ask about your O2C data…')
    fireEvent.change(input, { target: { value: 'highest order' } })
    fireEvent.click(screen.getByTitle('Send'))

    await waitFor(() => {
      expect(screen.getByText('Please specify a metric.')).toBeTruthy()
    })

    fireEvent.change(input, { target: { value: 'net amount' } })
    fireEvent.click(screen.getByTitle('Send'))

    await waitFor(() => {
      expect(askQuery).toHaveBeenNthCalledWith(1, 'highest order', null)
      expect(askQuery).toHaveBeenNthCalledWith(2, 'net amount', 'conv-followup')
      expect(screen.getByText('Using net amount now.')).toBeTruthy()
    })
  })

  it('focuses input when slash shortcut is pressed', async () => {
    render(React.createElement(MemoryRouter, null, React.createElement(Workspace)))

    const input = await screen.findByPlaceholderText('Ask about your O2C data…')
    fireEvent.keyDown(window, { key: '/' })
    expect(document.activeElement).toBe(input)
  })
})
