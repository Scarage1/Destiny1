"""
FastAPI application: serves graph exploration and NL query APIs.

In production (Docker/Azure), the built frontend is served as static files
from /frontend/dist, meaning a single container handles both API and UI.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("o2c")

try:
    from .agents.observability import get_metrics_summary, get_trace
    from .agents.orchestrator import process_query
    from .db_adapter import get_db_adapter
    from .graph_builder import (
        build_graph,
        get_graph_overview,
        get_node_details,
        get_node_neighbors,
        get_subgraph,
    )
except ImportError:
    from agents.observability import get_metrics_summary, get_trace
    from agents.orchestrator import process_query
    from db_adapter import get_db_adapter
    from graph_builder import (
        build_graph,
        get_graph_overview,
        get_node_details,
        get_node_neighbors,
        get_subgraph,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run on startup: auto-ingest if needed, build graph, start serving."""
    import threading

    adapter = get_db_adapter()

    if not adapter.db_exists():
        # DB missing — run ingestion in a background thread so uvicorn starts
        # immediately and Azure health checks pass. Data becomes available ~30s later.
        logger.info("[startup] Database not found — starting background ingestion...")

        def _run_ingest() -> None:
            try:
                try:
                    from .ingest import run_ingestion  # type: ignore[attr-defined]
                except ImportError:
                    from ingest import run_ingestion  # type: ignore[attr-defined]
                run_ingestion()
                logger.info("[startup] Background ingestion complete — rebuilding graph.")
                build_graph()
                logger.info("[startup] Graph ready.")
            except Exception:
                logger.exception("[startup] Background ingestion failed.")

        t = threading.Thread(target=_run_ingest, daemon=True, name="bg-ingest")
        t.start()
    elif adapter.name != "sqlite":
        logger.info("Graph build skipped for backend '%s' (SQLite expected).", adapter.name)
    else:
        logger.info("Building graph from database...")
        g = build_graph()
        logger.info(
            "Graph built: %d nodes, %d edges",
            g.number_of_nodes(),
            g.number_of_edges(),
        )

    yield


app = FastAPI(
    title="O2C Graph Intelligence API",
    description="Deterministic graph exploration and agentic query orchestration for SAP Order-to-Cash data",
    version="1.0.0",
    lifespan=lifespan,
)

# Response compression — reduces payload size significantly for large graph responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS — configurable via CORS_ALLOWED_ORIGINS env var (comma-separated)
_CORS_ORIGINS_DEFAULT = "http://localhost:3000,http://127.0.0.1:3000"
_cors_origins = [
    o.strip()
    for o in os.environ.get("CORS_ALLOWED_ORIGINS", _CORS_ORIGINS_DEFAULT).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NOTE: Static files are mounted AFTER all API routes at module level (see bottom of file).
# This ensures /api/* routes take precedence. Guarded by SERVE_STATIC=true.


# --- Request/Response Models ---


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
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
    seed_node_ids: list[str] = Field(..., min_length=1, max_length=50)
    hops: int = Field(default=1, ge=0, le=3)
    max_nodes: int = Field(default=200, ge=1, le=500)


class SubgraphResponse(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    stats: dict[str, Any]


# Only expose the JSON root metadata when NOT serving the React SPA.
# When SERVE_STATIC=true the index.html from the static mount handles GET /.
_SERVE_STATIC = os.environ.get("SERVE_STATIC", "").lower() == "true"


if not _SERVE_STATIC:
    @app.get("/")
    def root(request: Request):
        base = str(request.base_url).rstrip("/")
        return {
            "message": "O2C Graph Intelligence backend is running.",
            "health": f"{base}/api/health",
            "graph_overview": f"{base}/api/graph/overview",
            "query_endpoint": f"{base}/api/query/ask",
            "frontend": "http://localhost:3000 (dev)",
        }


@app.get("/api/health")
def health_check():
    """Azure App Service health probe endpoint."""
    from .graph_builder import get_graph_overview  # noqa: PLC0415 — lazy import to avoid circular
    adapter = get_db_adapter()
    try:
        overview = get_graph_overview()
        node_count = overview.get("stats", {}).get("node_count", 0)
    except Exception:
        node_count = 0
    return {
        "status": "healthy",
        "database": adapter.db_exists(),
        "db_backend": adapter.name,
        "graph_nodes": node_count,
        "version": "1.0.0",
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
    return get_subgraph(
        seed_node_ids=request.seed_node_ids,
        hops=request.hops,
        max_nodes=request.max_nodes,
    )


# --- Query Endpoint ---


@app.post("/api/query/ask", response_model=QueryResponse)
def ask_query(request: QueryRequest):
    """Process a natural language query against the O2C dataset."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    try:
        result = process_query(request.query, conversation_id=request.conversation_id)
    except Exception as exc:
        result = {
            "answer": "An internal error occurred while processing your query. Please try again.",
            "query": None,
            "results": None,
            "result_columns": None,
            "total_results": None,
            "referenced_nodes": [],
            "status": "error",
            "trace_id": "",
            "conversation_id": request.conversation_id,
            "intent": None,
            "plan": None,
            "verification": {"status": "failed", "warnings": [str(exc)]},
            "agent_trace": None,
        }
    return QueryResponse(**result)


@app.get("/api/query/trace/{trace_id}")
def query_trace(trace_id: str):
    return {"trace_id": trace_id, "events": get_trace(trace_id)}


# ─── Dashboard KPI Endpoint (T18) ─────────────────────────────────────────────
@app.get("/api/dashboard")
def get_dashboard():
    """Return 5 aggregated KPI cards for the workspace landing state."""
    adapter = get_db_adapter()

    def _run(sql: str) -> list[dict]:
        try:
            return adapter.execute_query(sql)
        except Exception:
            return []

    total_orders_rows = _run("SELECT COUNT(DISTINCT salesOrder) AS total FROM sales_order_headers")
    total_orders = total_orders_rows[0]["total"] if total_orders_rows else 0

    # Complete O2C cycle: salesOrder → delivery → billing → payment
    complete_rows = _run("""
        SELECT COUNT(DISTINCT soh.salesOrder) AS cnt
        FROM sales_order_headers soh
        JOIN outbound_delivery_items odi ON odi.referenceSdDocument = soh.salesOrder
        JOIN billing_document_items bdi ON bdi.referenceSdDocument = odi.deliveryDocument
        JOIN billing_document_headers bdh ON bdh.billingDocument = bdi.billingDocument
        JOIN payments p ON p.accountingDocument = bdh.accountingDocument
    """)
    complete_cycles = complete_rows[0]["cnt"] if complete_rows else 0

    # Deliveries with no matching billing document
    unbilled_rows = _run("""
        SELECT COUNT(DISTINCT odi.deliveryDocument) AS cnt
        FROM outbound_delivery_items odi
        LEFT JOIN billing_document_items bdi ON bdi.referenceSdDocument = odi.deliveryDocument
        WHERE odi.deliveryDocument IS NOT NULL AND bdi.billingDocument IS NULL
    """)
    never_billed = unbilled_rows[0]["cnt"] if unbilled_rows else 0

    # Billing docs with no payment settled
    uncleared_rows = _run("""
        SELECT COUNT(DISTINCT bdh.billingDocument) AS cnt
        FROM billing_document_headers bdh
        LEFT JOIN payments p ON p.accountingDocument = bdh.accountingDocument
        WHERE bdh.accountingDocument IS NOT NULL AND p.accountingDocument IS NULL
    """)
    uncleared = uncleared_rows[0]["cnt"] if uncleared_rows else 0

    # Top customer by total net amount
    top_cust_rows = _run("""
        SELECT COALESCE(bp.businessPartnerName, soh.soldToParty) AS name,
               ROUND(SUM(soh.totalNetAmount), 2) AS total_amount
        FROM sales_order_headers soh
        LEFT JOIN business_partners bp ON bp.customer = soh.soldToParty
        GROUP BY soh.soldToParty
        ORDER BY total_amount DESC
        LIMIT 1
    """)
    top_customer = top_cust_rows[0] if top_cust_rows else {"name": "—", "total_amount": 0}

    completion_pct = round((complete_cycles / total_orders * 100), 1) if total_orders > 0 else 0

    return {
        "cards": [
            {"id": "total_orders",    "label": "Orders",       "value": total_orders},
            {"id": "completion_rate", "label": "Complete",     "value": f"{completion_pct}%"},
            {"id": "never_billed",    "label": "Never Billed", "value": never_billed, "severity": "warning"},
            {"id": "uncleared",       "label": "Uncleared",    "value": uncleared, "severity": "critical"},
            {"id": "top_customer",    "label": "Top Customer", "value": top_customer["name"]},
        ]
    }




# ─── Static file serving (SPA catch-all) ──────────────────────────────────────
# Pattern for React Router (history mode) in FastAPI:
#  1. Mount /assets/ for hashed CSS/JS bundles (exact file matches)
#  2. Catch-all route returns index.html for every other non-API path
# Enabled only when SERVE_STATIC=true (Docker / Azure). Never in dev or tests.
_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _SERVE_STATIC and _frontend_dist.is_dir():
    # Serve hashed JS/CSS assets directly
    _assets_dir = _frontend_dist / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

    # SPA catch-all: serve index.html for any non-API, non-asset path
    _index_html = _frontend_dist / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):  # noqa: ARG001
        from fastapi.responses import FileResponse  # noqa: PLC0415
        return FileResponse(str(_index_html))

    logger.info("Serving frontend SPA from %s", _frontend_dist)
elif _SERVE_STATIC:
    logger.warning(
        "SERVE_STATIC=true but frontend/dist not found at %s — "
        "ensure the Docker image was built with the frontend stage.",
        _frontend_dist,
    )


if __name__ == "__main__":
    import uvicorn
    # PORT is injected by Azure App Service; fall back to 8000 locally
    port = int(os.environ.get("PORT", os.environ.get("API_PORT", 8000)))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)
