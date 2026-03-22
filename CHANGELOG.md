# Changelog

## [Unreleased]
### Added
- [T2] Graph schema v1 Pydantic models matching Domain Schema contracts.
### Changed
### Fixed
- [T2] Resolved flake8 linting violations (F401, W291, E302, E501) across `test_graph_schema.py`.
### Docs
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
