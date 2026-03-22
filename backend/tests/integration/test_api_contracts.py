from __future__ import annotations

from fastapi.testclient import TestClient

from backend.ingest import run_ingestion
from backend.main import app


client = TestClient(app)


def setup_module() -> None:
    run_ingestion()


def test_health_endpoint() -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "healthy"
    assert isinstance(payload["database"], bool)


def test_graph_overview_endpoint_contract() -> None:
    resp = client.get("/api/graph/overview")
    assert resp.status_code == 200

    payload = resp.json()
    assert "nodes" in payload and isinstance(payload["nodes"], list)
    assert "edges" in payload and isinstance(payload["edges"], list)
    assert "stats" in payload and isinstance(payload["stats"], dict)
    assert payload["stats"]["total_nodes"] >= 1


def test_graph_node_endpoints_with_existing_node() -> None:
    overview = client.get("/api/graph/overview").json()
    node_id = overview["nodes"][0]["id"]

    details_resp = client.get(f"/api/graph/node/{node_id}")
    assert details_resp.status_code == 200
    details = details_resp.json()
    assert details["id"] == node_id
    assert "properties" in details
    assert "neighbors" in details

    neighbors_resp = client.get(f"/api/graph/node/{node_id}/neighbors")
    assert neighbors_resp.status_code == 200
    neighbors = neighbors_resp.json()
    assert "nodes" in neighbors and isinstance(neighbors["nodes"], list)
    assert "edges" in neighbors and isinstance(neighbors["edges"], list)


def test_query_endpoint_rejected_contract() -> None:
    resp = client.post("/api/query/ask", json={"query": "write a poem about planets"})
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["status"] == "rejected"
    assert payload["query"] is None
    assert payload["results"] is None
    assert payload["result_columns"] is None
    assert payload["total_results"] is None
    assert isinstance(payload["trace_id"], str)


def test_query_endpoint_empty_query_is_400() -> None:
    resp = client.post("/api/query/ask", json={"query": "   "})
    assert resp.status_code == 400
