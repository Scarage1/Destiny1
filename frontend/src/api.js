const API_BASE = '/api';
const REQUEST_TIMEOUT_MS = 60000;

async function fetchWithTimeout(url, options = {}) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
        const res = await fetch(url, { ...options, signal: controller.signal });
        return res;
    } catch (err) {
        if (err?.name === 'AbortError') {
            throw new Error('Request timed out. Please try again.');
        }
        throw err;
    } finally {
        clearTimeout(timeoutId);
    }
}

export async function fetchGraphOverview() {
    const res = await fetchWithTimeout(`${API_BASE}/graph/overview`);
    if (!res.ok) throw new Error('Failed to fetch graph');
    return res.json();
}

export async function fetchNodeDetails(nodeId) {
    const res = await fetchWithTimeout(`${API_BASE}/graph/node/${encodeURIComponent(nodeId)}`);
    if (!res.ok) throw new Error('Node not found');
    return res.json();
}

export async function fetchNodeNeighbors(nodeId) {
    const res = await fetchWithTimeout(`${API_BASE}/graph/node/${encodeURIComponent(nodeId)}/neighbors`);
    if (!res.ok) throw new Error('Failed to fetch neighbors');
    return res.json();
}

export async function fetchGraphSubgraph(seedNodeIds, hops = 1, maxNodes = 200) {
    const res = await fetchWithTimeout(`${API_BASE}/graph/subgraph`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            seed_node_ids: seedNodeIds,
            hops,
            max_nodes: maxNodes,
        }),
    });
    if (!res.ok) throw new Error('Failed to fetch focused subgraph');
    return res.json();
}

export async function askQuery(query, conversationId = null) {
    const res = await fetchWithTimeout(`${API_BASE}/query/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, conversation_id: conversationId }),
    });
    if (!res.ok) throw new Error('Query failed');
    return res.json();
}

export async function fetchTrace(traceId) {
    const res = await fetchWithTimeout(`${API_BASE}/query/trace/${encodeURIComponent(traceId)}`);
    if (!res.ok) throw new Error('Failed to fetch trace');
    return res.json();
}

export async function fetchMetrics() {
    const res = await fetchWithTimeout(`${API_BASE}/metrics`);
    if (!res.ok) throw new Error('Failed to fetch metrics');
    return res.json();
}
