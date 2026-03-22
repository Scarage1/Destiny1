# Changelog

## [Unreleased]
### Added
- [T3] Normalization-integrated ingestion with summary and reject-report artifacts.
- [T4] Graph idempotency diagnostics and integration validation.
- [T5] Required assignment query integration tests.
- [T6] Guardrail unit and integration test coverage.
- [T7/T8/T9] Deterministic query pipeline contract tests with trace metadata and no-data grounding behavior.
- [T10] API contract integration tests.
- [T11] Frontend Vitest setup with API client tests.
- [T12] Submission documentation pack (architecture, guardrails, prompting, runbook, demo script, final signoff).
### Changed
- README now includes repository and demo references plus architecture/runbook links.
### Fixed
- [T2] Resolved flake8 linting violations (F401, W291, E302, E501) across `test_graph_schema.py`.
### Docs
- Added agent audit/status updates and submission readiness tracker improvements.
### Tests
- [T2] Enforced strict tests restricting invalid relationship edge creation.

## [v0.1-data-foundation] - 2026-03-23
### Added
- Dataset profiling: 20 entity types, 1634 records across 17 SQLite tables
- Graph schema v1: 11 node types, 12 relationship types
- JSONL ingestion pipeline (idempotent)
- NetworkX graph construction from SQLite
- SQLite database with indexed joins and read-only execution

## [v0.2-query-core] - 2026-03-23
### Added
- Domain guardrails with off-topic rejection and SQL safety validation
- Schema-constrained NL→SQL generator using Gemini
- Grounded answer synthesis with no-data-no-claim policy
- Query execution service with timeout and row limits
- FastAPI endpoints: /api/query/ask, /api/graph/overview, /api/graph/node/{id}
