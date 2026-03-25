from __future__ import annotations

from fastapi.testclient import TestClient

from backend.database import execute_readonly_query
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


def test_graph_subgraph_endpoint_contract() -> None:
    overview = client.get("/api/graph/overview").json()
    seed = overview["nodes"][0]["id"]

    resp = client.post(
        "/api/graph/subgraph",
        json={"seed_node_ids": [seed], "hops": 1, "max_nodes": 50},
    )
    assert resp.status_code == 200
    payload = resp.json()

    assert "nodes" in payload and isinstance(payload["nodes"], list)
    assert "edges" in payload and isinstance(payload["edges"], list)
    assert "stats" in payload and isinstance(payload["stats"], dict)
    assert payload["stats"]["seed_count"] == 1
    assert payload["stats"]["resolved_seed_count"] >= 1


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


def test_agents_status_endpoint() -> None:
    resp = client.get("/api/agents/status")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "healthy"
    agents = payload["agents"]
    assert "orchestrator" in agents
    assert "executor_agent" in agents
    assert "validator_agent" in agents


def test_query_trace_endpoint_contract() -> None:
    ask = client.post("/api/query/ask", json={"query": "Tell me a joke about football"})
    assert ask.status_code == 200
    trace_id = ask.json()["trace_id"]

    trace_resp = client.get(f"/api/query/trace/{trace_id}")
    assert trace_resp.status_code == 200
    payload = trace_resp.json()
    assert payload["trace_id"] == trace_id
    assert isinstance(payload["events"], list)


def test_query_endpoint_success_includes_plan_contract() -> None:
    resp = client.post(
        "/api/query/ask",
        json={"query": "Which products are associated with the highest number of billing documents?"},
    )
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["status"] == "success"
    assert payload["intent"] == "analyze"
    assert isinstance(payload["plan"], dict)
    assert "intent" in payload["plan"]
    assert "metric" in payload["plan"]
    assert "group_by" in payload["plan"]
    assert isinstance(payload["agent_trace"], dict)
    assert payload["agent_trace"]["trace_id"] == payload["trace_id"]
    assert "summary" in payload["agent_trace"]


def test_query_endpoint_generic_trace_flow_contract() -> None:
    resp = client.post(
        "/api/query/ask",
        json={"query": "Trace the full flow of a billing document"},
    )
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["status"] == "success"
    assert payload["intent"] == "trace_flow"
    assert payload["total_results"] is not None
    assert isinstance(payload["result_columns"], list)
    assert "billingDocument" in payload["result_columns"]


def test_query_endpoint_journal_entry_lookup_contract() -> None:
    rows = execute_readonly_query(
        "SELECT billingDocument FROM billing_document_headers ORDER BY billingDocument LIMIT 1"
    )
    billing_doc = rows[0]["billingDocument"]

    resp = client.post(
        "/api/query/ask",
        json={"query": f"{billing_doc} - Find the journal entry number linked to this?"},
    )
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["status"] == "success"
    assert isinstance(payload["result_columns"], list)
    assert "journalEntry" in payload["result_columns"]


def test_metrics_endpoint_contract() -> None:
    resp = client.get("/api/metrics")
    assert resp.status_code == 200
    payload = resp.json()
    assert "request_count" in payload
    assert "success_rate" in payload
    assert "guard_rejection_rate" in payload
    assert "clarification_rate" in payload
    assert "deterministic_hit_rate" in payload
    assert "llm_fallback_rate" in payload
    assert "p95_latency_ms" in payload
