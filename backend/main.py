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
    from .database import DB_PATH
    from .graph_builder import (
        get_graph_overview,
        get_node_details,
        get_node_neighbors,
        build_graph,
    )
    from .llm_service import process_query
except ImportError:
    from database import DB_PATH
    from graph_builder import (
        get_graph_overview,
        get_node_details,
        get_node_neighbors,
        build_graph,
    )
    from llm_service import process_query


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run on startup: ensure DB exists, build graph."""
    if not DB_PATH.exists():
        print("⚠ Database not found. Run 'python ingest.py' first.")
    else:
        print("Building graph from database...")
        g = build_graph()
        print(
            f"✓ Graph built: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges"
        )
    yield


app = FastAPI(
    title="SAP O2C Graph Query System",
    description="Graph-based exploration and NL querying of SAP Order-to-Cash data",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request/Response Models ---


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    answer: str
    query: str | None = None
    results: list[dict[str, Any]] | None = None
    result_columns: list[str] | None = None
    total_results: int | None = None
    referenced_nodes: list[str] = []
    status: str
    trace_id: str


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


# --- Health ---


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "database": DB_PATH.exists()}


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


# --- Query Endpoint ---


@app.post("/api/query/ask", response_model=QueryResponse)
def ask_query(request: QueryRequest):
    """Process a natural language query against the O2C dataset."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    result = process_query(request.query)
    return QueryResponse(**result)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("API_PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
