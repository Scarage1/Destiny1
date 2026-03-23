# Assignment Requirements Mapping

This document maps the delivered implementation to the original assignment criteria.

## 1) Graph Construction
**Status:** Implemented

**Evidence:**
- Ingestion pipeline and SQLite load: [backend/ingest.py](backend/ingest.py)
- Graph build from business entities/relations: [backend/graph_builder.py](backend/graph_builder.py)
- Domain schema contracts: [backend/app/models/graph_schema.py](backend/app/models/graph_schema.py)
- Data profiling + dictionary: [docs/data-dictionary.md](docs/data-dictionary.md)

## 2) Graph Visualization
**Status:** Implemented

**Evidence:**
- Interactive graph UI with expansion and node click handling: [frontend/src/App.jsx](frontend/src/App.jsx)
- Graph component support files: [frontend/src/components/GraphCanvas.jsx](frontend/src/components/GraphCanvas.jsx)
- Graph APIs for overview/node/neighbors: [backend/main.py](backend/main.py)

## 3) Conversational Query Interface
**Status:** Implemented

**Evidence:**
- NL query endpoint: [backend/main.py](backend/main.py)
- NL to SQL + execution + grounded synthesis: [backend/llm_service.py](backend/llm_service.py)
- Frontend chat query flow: [frontend/src/App.jsx](frontend/src/App.jsx)

## 4) Required Example Query Classes
**Status:** Implemented and tested

**Evidence:**
- Integration tests for required query classes (a/b/c): [backend/tests/integration/test_required_queries.py](backend/tests/integration/test_required_queries.py)
- Test case documentation: [docs/test-cases.md](docs/test-cases.md)

## 5) Guardrails
**Status:** Implemented and tested

**Evidence:**
- Domain rejection + SQL safety checks: [backend/guardrails.py](backend/guardrails.py)
- Guardrail unit tests: [backend/tests/unit/test_guardrails.py](backend/tests/unit/test_guardrails.py)
- Guardrail integration rejection tests: [backend/tests/integration/test_guardrail_rejections.py](backend/tests/integration/test_guardrail_rejections.py)

## 6) Code Quality and Architecture
**Status:** Implemented

**Evidence:**
- Architecture write-up: [docs/architecture.md](docs/architecture.md)
- Runbook and operational docs: [docs/runbook.md](docs/runbook.md)
- CI workflow: [.github/workflows/ci.yml](.github/workflows/ci.yml)
- Tests: backend and frontend suites

## 7) Submission Artifacts
**Status:** Partially complete (manual finalization pending)

**Completed evidence:**
- Public repository configured: [README.md](README.md)
- Architecture/guardrails/prompting docs:
  - [docs/architecture.md](docs/architecture.md)
  - [docs/guardrails.md](docs/guardrails.md)
  - [docs/prompting-strategy.md](docs/prompting-strategy.md)
- AI logs folder scaffold: [docs/ai-session-logs/README.md](docs/ai-session-logs/README.md)

**Manual steps pending before final submission:**
1. Replace local demo URL with public hosted demo link in [README.md](README.md).
2. Add exported AI transcript files under [docs/ai-session-logs](docs/ai-session-logs).
3. Tag release `v1.0-submission` and submit form.
