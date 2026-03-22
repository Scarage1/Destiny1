# 13 - Current State Audit (2026-03-23)

## Purpose
Provide a truthful snapshot of codebase + docs alignment against tickets T1-T12, and define the immediate one-by-one execution order.

## Completion Matrix

| Ticket | Status | Evidence |
|---|---|---|
| T1 Data profiling and dictionary | Done | [backend/ingestion/profile_dataset.py](backend/ingestion/profile_dataset.py), [docs/data-dictionary.md](docs/data-dictionary.md), [docs/data-quality-report.md](docs/data-quality-report.md), [data/processed/profile_summary.json](data/processed/profile_summary.json), [backend/tests/unit/test_profile_dataset.py](backend/tests/unit/test_profile_dataset.py) |
| T2 Graph schema v1 and contracts | In Progress | [backend/app/models/graph_schema.py](backend/app/models/graph_schema.py) exists but no dedicated tests and not fully integrated into runtime graph builder |
| T3 Normalization pipeline | Done | normalizer integrated into [backend/ingest.py](backend/ingest.py), with integration tests in [backend/tests/integration/test_normalization_pipeline.py](backend/tests/integration/test_normalization_pipeline.py) |
| T4 Idempotent graph loader | Done | integration suite added in [backend/tests/integration/test_graph_loader_idempotency.py](backend/tests/integration/test_graph_loader_idempotency.py), diagnostics added in [backend/graph_builder.py](backend/graph_builder.py) |
| T5 Flow integrity tests | Done | required query suite in [backend/tests/integration/test_required_queries.py](backend/tests/integration/test_required_queries.py) |
| T6 Guardrails and safety | Done | guardrail suites in [backend/tests/unit/test_guardrails.py](backend/tests/unit/test_guardrails.py) and [backend/tests/integration/test_guardrail_rejections.py](backend/tests/integration/test_guardrail_rejections.py) |
| T7 NL to SQL generation | Done | deterministic contract tests added in [backend/tests/unit/test_query_pipeline_contract.py](backend/tests/unit/test_query_pipeline_contract.py) |
| T8 Query execution normalization | Done | trace_id/result_columns contract enforced in [backend/llm_service.py](backend/llm_service.py) and verified by tests |
| T9 Grounded answer synthesis | Done | deterministic no-data grounding enforced in [backend/llm_service.py](backend/llm_service.py) with unit tests |
| T10 API endpoints | Done | API contract suite in [backend/tests/integration/test_api_contracts.py](backend/tests/integration/test_api_contracts.py), route conflict fixed in [backend/main.py](backend/main.py) |
| T11 Frontend core UX | Done | graph/chat/highlight in [frontend/src/App.jsx](frontend/src/App.jsx), tests in [frontend/src/tests/api.test.js](frontend/src/tests/api.test.js) |
| T12 Docs/demo/submission | Review | root [README.md](README.md), CI [/.github/workflows/ci.yml](.github/workflows/ci.yml), issue templates, and delivery docs are complete; demo/repo link fill and transcript artifact upload pending |

## Critical Misalignments

Update: T3, T4, T5, T6, T7, T8, T9, T10, and T11 have been completed after this audit was first drafted.

1. **Architecture consistency check**
   - Planned docs are now aligned to the implemented SQLite + SQL + NetworkX path for v1 delivery.

2. **Testing gap against quality gates**
   - Required integration and guardrail tests are now present, but API contract tests and frontend tests are still missing.

3. **Project structure drift**
   - Planned modular boundaries in [docs/agent-docs/02-system-design.md](docs/agent-docs/02-system-design.md) are only partially reflected in backend/frontend layout.

## Decision Applied

The project is now explicitly baselined on **SQLite + SQL** for v1 to reduce delivery risk and stay aligned with current implementation.

## Next 5 Tasks (strict order)

### Task 1: T12 submission package finalization
- Fill demo/repo links, finalize evaluator narrative, and attach AI transcripts.

### Task 2: CI pipeline verification
- Validate workflow execution on first push/PR cycle.

### Task 3: Governance templates completion
- Add issue templates and ensure PR template references are consistent.

### Task 4: Demo/documentation polish
- Finalize architecture narrative and runbook for evaluator walkthrough.

### Task 5: Submission handoff bundle
- Final checklist validation and AI logs packaging notes.

## Execution Rule
Proceed one task at a time: Planner -> Builder -> Reviewer -> Integrator -> DocOps, with quality gates on each ticket.
