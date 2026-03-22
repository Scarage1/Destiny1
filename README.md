# Graph-Based Data Modeling and Query System

This project builds a context graph over SAP Order-to-Cash style entities and provides a natural-language query assistant with dataset-grounded answers.

## Demo and Repository
- Demo: `http://localhost:3000` (local run)
- Repository: `https://github.com/Scarage1/Destiny1`

> Note: Add your final public deployment URL before submission if hosting externally.

## Architecture

Detailed architecture write-up: [docs/architecture.md](docs/architecture.md)

### Stack
- Backend: FastAPI + Python
- Storage: SQLite (raw source of truth) + in-memory NetworkX graph for exploration
- LLM: Google Gemini (`gemini-2.0-flash`) for NL -> SQL and answer synthesis
- Frontend: React + Vite + ForceGraph2D

### End-to-end flow
1. User asks question in chat UI.
2. Domain guardrail validates relevance.
3. LLM generates SQL query constrained by schema prompt.
4. SQL safety validator blocks write/injection patterns.
5. Read-only SQL executes against SQLite.
6. Results are normalized and returned with trace metadata.
7. Grounded answer is synthesized from result rows.
8. Referenced graph nodes are highlighted in UI.

## Graph Model
Primary nodes and relations include:
- `Customer -> SalesOrder -> Delivery -> BillingDocument -> JournalEntry -> Payment`
- `SalesOrderItem -> Product`
- `DeliveryItem -> Plant`

See [docs/agent-docs/03-domain-schema.md](docs/agent-docs/03-domain-schema.md) for details.

## Guardrails
Implemented in [backend/guardrails.py](backend/guardrails.py):
- Off-domain rejection policy
- SQL read-only safety checks
- Injection-like pattern blocking
- Standard rejection response

Additional guardrail documentation: [docs/guardrails.md](docs/guardrails.md)

## Prompting Strategy
- [docs/prompting-strategy.md](docs/prompting-strategy.md)

## Project Structure
- [backend](backend): ingestion, graph build, LLM service, FastAPI
- [frontend](frontend): graph explorer and chat UI
- [docs/agent-docs](docs/agent-docs): execution plan, tracker, architecture decisions
- [docs/ai-session-logs](docs/ai-session-logs): transcript index for submission evidence

## Local Setup

Operational runbook: [docs/runbook.md](docs/runbook.md)

### Backend
1. `python -m venv .venv`
2. `source .venv/bin/activate`
3. `pip install -r backend/requirements.txt`
4. `python backend/ingest.py`
5. `python backend/main.py`

### Frontend
1. `cd frontend`
2. `npm install`
3. `npm run dev`

Backend API runs on `:8000`, frontend on `:3000`.

## Testing
- Backend: `python -m pytest backend/tests -q`
- Frontend: `cd frontend && npm test`

## What is complete
- Data profiling and dictionary outputs
- Graph build and exploration APIs
- Required integration query tests (a/b/c)
- Guardrail unit/integration tests
- API contract tests
- Frontend API tests and graph/chat UX

## Known limitations
- SQL-based pipeline used for v1 delivery (no Neo4j/Cypher path in current implementation).
- LLM answer quality depends on model response quality for non-empty results.
- Frontend remains JavaScript in v1; TS migration can be future enhancement.

## Submission checklist pointers
- [docs/agent-docs/10-submission-checklist.md](docs/agent-docs/10-submission-checklist.md)
- [docs/ai-session-logs/README.md](docs/ai-session-logs/README.md)
- [docs/demo-script.md](docs/demo-script.md)
- [docs/final-signoff.md](docs/final-signoff.md)
