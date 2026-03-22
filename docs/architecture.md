# Architecture Overview

## Goal
Unify fragmented Order-to-Cash entities into a graph representation and provide a data-grounded natural-language query interface.

## Runtime Components
- Backend API: FastAPI
- Query Engine: SQLite read-only SQL execution
- Graph Engine: NetworkX in-memory directed graph built from SQLite tables
- LLM Service: Gemini for NL -> SQL and answer synthesis
- Frontend: React + Vite with ForceGraph2D

## Data Plane
1. Raw JSONL files are ingested into SQLite tables.
2. Ingestion performs optional schema-backed normalization for core entities.
3. Rejection and summary artifacts are written to `data/processed`.
4. Graph is constructed from SQLite joins into typed node/edge identifiers.

## Query Plane
1. User question is sent to `/api/query/ask`.
2. Domain relevance guardrail checks in-scope intent.
3. LLM generates SQL with schema context.
4. SQL safety validator blocks writes/injection-like patterns.
5. Query executes via read-only path.
6. Answer is synthesized from result rows only.
7. API returns `answer`, `query`, `results`, `result_columns`, `total_results`, `referenced_nodes`, `trace_id`, `status`.

## Graph APIs
- `GET /api/graph/overview`
- `GET /api/graph/node/{node_id}`
- `GET /api/graph/node/{node_id}/neighbors`

## Reliability and Testing
- Unit tests for schema/normalization/guardrails/query contracts
- Integration tests for required assignment query classes
- Integration tests for API contracts and ingestion idempotency

## Tradeoffs
- SQLite+NetworkX chosen for delivery speed and deterministic local execution.
- Neo4j/Cypher path is deferred; SQL path is explicitly documented for v1.
