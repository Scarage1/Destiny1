# Graph Load Runbook

## Purpose
Operational runbook for SQLite ingestion + in-memory graph build with idempotency checks.

## Steps
1. Run ingestion:
   - `python backend/ingest.py`
2. Build graph (startup or explicit):
   - `python backend/main.py` (startup builds graph)

## Idempotency verification
Run integration test:
- `python -m pytest backend/tests/integration/test_graph_loader_idempotency.py -q`

The test verifies:
- repeated ingestion runs produce the same graph fingerprint
- no duplicate node/edge inflation across reruns
- relationship diagnostics report remains structurally valid

## Orphan diagnostics
Use `get_relationship_diagnostics()` from [backend/graph_builder.py](backend/graph_builder.py) to inspect missing source/target links for critical flow joins.

Output includes:
- per-relationship orphan counts
- aggregate orphan link total

## Troubleshooting
- If ingestion fails, ensure raw dataset exists under `data/raw/sap-o2c-data`.
- If graph count changes unexpectedly across reruns, inspect source table row counts and join-key quality from [docs/data-quality-report.md](docs/data-quality-report.md).
