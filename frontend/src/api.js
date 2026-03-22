const API_BASE = '/api';

export async function fetchGraphOverview() {
    const res = await fetch(`${API_BASE}/graph/overview`);
    if (!res.ok) throw new Error('Failed to fetch graph');
    return res.json();
}

export async function fetchNodeDetails(nodeId) {
    const res = await fetch(`${API_BASE}/graph/node/${encodeURIComponent(nodeId)}`);
    if (!res.ok) throw new Error('Node not found');
    return res.json();
}

export async function fetchNodeNeighbors(nodeId) {
    const res = await fetch(`${API_BASE}/graph/node/${encodeURIComponent(nodeId)}/neighbors`);
    if (!res.ok) throw new Error('Failed to fetch neighbors');
    return res.json();
}

export async function askQuery(query) {
    const res = await fetch(`${API_BASE}/query/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
    });
    if (!res.ok) throw new Error('Query failed');
    return res.json();
}
