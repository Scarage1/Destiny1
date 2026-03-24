export function buildSessionSnapshot({
  conversationId,
  messages,
  queryHistory,
  uiMode,
  runtimeMetrics,
}) {
  return {
    version: '1.0',
    exported_at: new Date().toISOString(),
    conversation_id: conversationId || null,
    ui_mode: uiMode || 'standard',
    runtime_metrics: runtimeMetrics || null,
    query_history: Array.isArray(queryHistory) ? queryHistory : [],
    messages: Array.isArray(messages)
      ? messages.map(m => ({
          role: m.role,
          text: m.text,
          status: m.status || null,
          intent: m.intent || null,
          total_results: m.totalResults ?? null,
          trace_id: m.traceId || null,
          plan: m.plan || null,
          verification: m.verification || null,
          referenced_nodes: m.referencedNodes || [],
          sql: m.sql || null,
          trace_events: m.traceEvents || [],
        }))
      : [],
  }
}

/** Maps persisted snapshot messages back to Workspace message objects. */
export function reviveMessagesFromSnapshot(storedMessages) {
  if (!Array.isArray(storedMessages)) return []
  return storedMessages.map(m => ({
    role: m.role,
    text: m.text,
    status: m.status,
    intent: m.intent,
    totalResults: m.total_results,
    traceId: m.trace_id,
    plan: m.plan,
    verification: m.verification,
    referencedNodes: m.referenced_nodes || [],
    sql: m.sql,
    traceEvents: m.trace_events || [],
  }))
}

export function makeSnapshotFilename(conversationId) {
  const suffix = conversationId || 'session'
  const safeSuffix = String(suffix).replace(/[^a-zA-Z0-9-_]/g, '')
  return `o2c-session-${safeSuffix}.json`
}
