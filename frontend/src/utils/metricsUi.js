export function formatRate(value) {
  if (typeof value !== 'number') return '--'
  return `${Math.round(value * 100)}%`
}

export function formatLatencyMs(value) {
  if (typeof value !== 'number') return '--'
  return `${value}ms`
}

function formatCount(value) {
  return typeof value === 'number' ? `${value}` : '--'
}

export function getMetricsDetailRows(runtimeMetrics) {
  return [
    { label: 'Requests', value: formatCount(runtimeMetrics?.request_count) },
    { label: 'Success Rate', value: formatRate(runtimeMetrics?.success_rate) },
    { label: 'Guard Rejections', value: formatRate(runtimeMetrics?.guard_rejection_rate) },
    { label: 'Clarifications', value: formatRate(runtimeMetrics?.clarification_rate) },
    { label: 'Deterministic Hit', value: formatRate(runtimeMetrics?.deterministic_hit_rate) },
    { label: 'Fallback Rate', value: formatRate(runtimeMetrics?.llm_fallback_rate) },
    { label: 'P95 Latency', value: formatLatencyMs(runtimeMetrics?.p95_latency_ms) },
  ]
}
