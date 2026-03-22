# Operations Runbook

## Local Startup
1. Create and activate venv
2. Install backend dependencies from `backend/requirements.txt`
3. Run ingestion: `python backend/ingest.py`
4. Start API: `python backend/main.py`
5. In `frontend`, run `npm install` and `npm run dev`

## Validation Commands
- Backend tests: `python -m pytest backend/tests -q`
- Frontend tests: `cd frontend && npm test`

## Data Artifacts
Generated under `data/processed`:
- `profile_summary.json`
- `ingestion_summary.json`
- `normalization_rejects.json`

## Troubleshooting
- Missing DB: run ingestion first.
- Query blocked: inspect guardrail and SQL safety checks.
- Empty graph: verify dataset exists under `data/raw/sap-o2c-data`.

## Release Hygiene
- One ticket per branch
- Conventional commits
- PR template must be fully completed
- CI must pass before merge
