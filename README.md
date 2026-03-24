# O2C Graph Intelligence

**Promise:** Understand your order-to-cash system in seconds.

## Agentic Business Intelligence System for Order-to-Cash Graphs

This project delivers a production-style BI assistant over SAP Order-to-Cash entities using deterministic execution with constrained LLM assistance.

We intentionally avoid direct blind NL→SQL execution to reduce hallucination risk and increase reliability.

## Demo and Repository
- Demo: https://decent-prix-laid-customize.trycloudflare.com
- Repository: `https://github.com/Scarage1/Destiny1`

> Note: Current public demo is tunnel-based (temporary). Replace with a stable hosted URL for final submission.

## Architecture

Detailed architecture write-up: [docs/architecture.md](docs/architecture.md)

Architecture diagrams and pipeline sequence are documented in [docs/architecture.md](docs/architecture.md).

### Stack
- Backend: FastAPI + Python
- Storage: SQLite (raw source of truth) + in-memory NetworkX graph for exploration
- LLM: Google Gemini (`gemini-2.0-flash`) with Groq fallback for NL -> SQL and answer synthesis
- Frontend: React + Vite + ForceGraph2D

## Product Surfaces
- `/` → Landing page (hero, features, trust)
- `/workspace` → Operational workspace (graph + chat + trace)

Design intent: clarity over effects, one primary action, deterministic behavior first.

### End-to-end flow
1. User asks question in chat UI.
2. Planner Agent extracts structured intent (goal, entity, context).
3. Guard Agent validates domain scope and safety policy.
4. Query Agent executes deterministic templates first, then constrained SQL generation if needed.
5. Verifier checks result consistency/emptiness for intent-specific conditions.
6. Response Agent generates grounded business explanation from returned rows.
7. Memory stores minimal conversation context for follow-up questions.
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
- [backend/agents](backend/agents): planner/guard/query/verifier/response agents + orchestrator
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

Browser verification:
- `http://localhost:3000/` loads landing page
- `http://localhost:3000/workspace` loads workspace
- `http://localhost:8000/api/health` returns healthy

## Gemini API setup
1. Copy [.env.example](.env.example) to `.env`
2. Set `GEMINI_API_KEY` in `.env`
3. Start services with [scripts/dev_up.sh](scripts/dev_up.sh) (loads `.env` automatically)

To verify Gemini path, run [scripts/quality_gate.sh](scripts/quality_gate.sh). It performs an extra LLM smoke check when `GEMINI_API_KEY` is set.

## Groq fallback setup (optional)
1. Set `GROQ_API_KEY` in `.env`
2. (Optional) set `GROQ_MODEL` (default: `llama-3.1-8b-instant`)
3. If Gemini is unavailable or rate-limited, the orchestrator automatically falls back to Groq for non-deterministic query generation and SQL repair retries.

## Testing
- Backend: `python -m pytest backend/tests -q`
- Frontend: `cd frontend && npm test`
- Full quality gate: `bash scripts/quality_gate.sh` (tests + build + API smoke; starts backend temporarily if needed)

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
