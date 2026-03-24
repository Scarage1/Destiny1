"""
FastAPI application: serves graph exploration and NL query APIs.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any

try:
    from .db_adapter import get_db_adapter
    from .agents.orchestrator import process_query
    from .agents.observability import get_metrics_summary, get_trace
    from .graph_builder import (
        get_graph_overview,
        get_subgraph,
        get_node_details,
        get_node_neighbors,
        build_graph,
    )
except ImportError:
    from db_adapter import get_db_adapter
    from agents.orchestrator import process_query
    from agents.observability import get_metrics_summary, get_trace
    from graph_builder import (
        get_graph_overview,
        get_subgraph,
        get_node_details,
        get_node_neighbors,
        build_graph,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run on startup: ensure DB exists, build graph."""
    adapter = get_db_adapter()

    if not adapter.db_exists():
        print("⚠ Database source not found. Run ingestion/setup first.")
    elif adapter.name != "sqlite":
        print(f"ℹ Graph build skipped for backend '{adapter.name}' (current graph engine expects SQLite).")
    else:
        print("Building graph from database...")
        g = build_graph()
        print(
            f"✓ Graph built: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges"
        )
    yield


app = FastAPI(
    title="O2C Graph Intelligence API",
    description="Deterministic graph exploration and agentic query orchestration for SAP Order-to-Cash data",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request/Response Models ---


class QueryRequest(BaseModel):
    query: str
    conversation_id: str | None = None


class QueryResponse(BaseModel):
    answer: str
    query: str | None = None
    results: list[dict[str, Any]] | None = None
    result_columns: list[str] | None = None
    total_results: int | None = None
    referenced_nodes: list[str] = []
    status: str
    trace_id: str
    conversation_id: str | None = None
    intent: str | None = None
    plan: dict[str, Any] | None = None
    verification: dict[str, Any] | None = None
    agent_trace: dict[str, Any] | None = None


class GraphOverview(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    stats: dict[str, Any]


class NodeDetails(BaseModel):
    id: str
    properties: dict[str, Any]
    neighbors: dict[str, list[dict[str, Any]]]


class NodeNeighbors(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class SubgraphRequest(BaseModel):
    seed_node_ids: list[str]
    hops: int = 1
    max_nodes: int = 200


class SubgraphResponse(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    stats: dict[str, Any]


# --- Health ---


@app.get("/")
def root():
    return {
        "message": "O2C Graph Intelligence backend is running.",
        "health": "/api/health",
        "graph_overview": "/api/graph/overview",
        "query_endpoint": "/api/query/ask",
        "frontend": "http://127.0.0.1:3000",
    }


@app.get("/api/health")
def health_check():
    adapter = get_db_adapter()
    return {
        "status": "healthy",
        "database": adapter.db_exists(),
        "db_backend": adapter.name,
    }


@app.get("/api/agents/status")
def agents_status():
    return {
        "status": "healthy",
        "agents": [
            "planner_agent",
            "guard_agent",
            "validator_agent",
            "query_agent",
            "executor_agent",
            "verifier_agent",
            "response_agent",
            "memory",
            "observability",
            "orchestrator",
        ],
    }


@app.get("/api/metrics")
def metrics_summary():
    return get_metrics_summary()


# --- Graph Endpoints ---


@app.get("/api/graph/overview", response_model=GraphOverview)
def graph_overview():
    """Get full graph for initial rendering."""
    return get_graph_overview()


@app.get("/api/graph/node/{node_id}", response_model=NodeDetails)
def node_details(node_id: str):
    """Get full metadata for a specific node."""
    details = get_node_details(node_id)
    if details is None:
        raise HTTPException(
            status_code=404, detail=f"Node not found: {node_id}"
        )
    return details


@app.get(
    "/api/graph/node/{node_id}/neighbors", response_model=NodeNeighbors
)
def node_neighbors(node_id: str):
    """Get neighbors for node expansion."""
    neighbors = get_node_neighbors(node_id)
    if neighbors is None:
        raise HTTPException(
            status_code=404, detail=f"Node not found: {node_id}"
        )
    return neighbors


@app.post("/api/graph/subgraph", response_model=SubgraphResponse)
def graph_subgraph(request: SubgraphRequest):
    hops = max(0, min(request.hops, 3))
    max_nodes = max(1, min(request.max_nodes, 500))
    return get_subgraph(
        seed_node_ids=request.seed_node_ids,
        hops=hops,
        max_nodes=max_nodes,
    )


# --- Query Endpoint ---


@app.post("/api/query/ask", response_model=QueryResponse)
def ask_query(request: QueryRequest):
    """Process a natural language query against the O2C dataset."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    result = process_query(request.query, conversation_id=request.conversation_id)
    return QueryResponse(**result)


@app.get("/api/query/trace/{trace_id}")
def query_trace(trace_id: str):
    return {"trace_id": trace_id, "events": get_trace(trace_id)}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("API_PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
