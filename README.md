# O2C Graph Intelligence

**Explore your Order-to-Cash data through natural language — no SQL required.**

[![CI](https://github.com/Scarage1/Destiny1/actions/workflows/ci.yml/badge.svg)](https://github.com/Scarage1/Destiny1/actions/workflows/ci.yml)

---

## What This Is

A production-grade context graph system with an LLM-powered query interface over a SAP Order-to-Cash dataset.

- Orders, deliveries, invoices, and payments unified into an **interactive knowledge graph**
- A **ForceGraph2D canvas** for visual node exploration
- A **conversational chat interface** that understands natural language — including typos and shorthand
- Queries translate to **deterministic SQL templates** (~80%); LLM only called for novel queries
- **Multi-agent pipeline** with Guard → Planner → Query → Execute → Verify → Respond
- Automatic **Groq fallback** if Gemini times out

---

## Architecture

```
User query
  → Guard Agent      [domain check — reject if off-topic]
  → Planner Agent    [extract structured intent; typo-tolerant]
  → Query Agent      [match intent to deterministic SQL template]
  → Executor Agent   [circuit-breaker-protected SQL execution]
  → Verifier Agent   [result sanity check]
  → Response Agent   [grounded NL answer]
```

### Stack

| Layer | Technology | Reason |
|-------|-----------|--------|
| Storage | SQLite (dev) / PostgreSQL (prod) | Zero-setup, full SQL expressiveness |
| Graph | NetworkX | In-memory traversal, BFS expansion |
| API | FastAPI + uvicorn | Async, auto-docs, Pydantic validation |
| LLM | Gemini 2.0 Flash + Groq fallback | Speed + cost |
| Frontend | React + Vite | Fast HMR, lightweight bundle |
| Deployment | Docker → Azure App Service | Single container, PORT env injection |

### Graph Model

```
Customer ──PLACED──► SalesOrder ──HAS──► SalesOrderItem ──REFERS_TO──► Product
                         │
                    FULFILLED_BY
                         │
                         ▼
                      Delivery ──HAS──► DeliveryItem ──DELIVERED_TO──► Plant
                         │
                      BILLED_BY
                         │
                         ▼
                   BillingDocument ──HAS──► BillingDocumentItem
                         │
                      BOOKED_AS
                         │
                         ▼
                    JournalEntry ──SETTLED_BY──► Payment
```

---

## Quick Start

```bash
# 1. Clone and create virtual environment
git clone https://github.com/Scarage1/Destiny1
cd Destiny1
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements-dev.txt

# 2. Configure
cp .env.example .env
# Edit .env — set GEMINI_API_KEY

# 3. Ingest data
make ingest

# 4. Start services
make dev        # backend :8000  |  frontend :3000
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | **Yes** | — | Google Gemini API key |
| `GROQ_API_KEY` | No | — | Groq fallback key |
| `PORT` | No | `8000` | Listen port (injected by Azure) |
| `CORS_ALLOWED_ORIGINS` | No | `localhost:3000` | Comma-separated allowed origins |
| `DB_BACKEND` | No | `sqlite` | `sqlite` or `postgres` |
| `POSTGRES_DSN` | No | — | Full DSN when `DB_BACKEND=postgres` |
| `LLM_TIMEOUT_SECONDS` | No | `20` | LLM call timeout |
| `PIPELINE_TIMEOUT_MS` | No | `30000` | Total pipeline wall-clock limit |

---

## Testing

```bash
make test       # 156 backend + 20 frontend
make lint       # ruff (zero issues expected)
make coverage   # backend coverage report
make gate       # full quality gate
```

---

## Docker

```bash
make docker-build   # builds multi-stage image (frontend + backend)
make docker-run     # runs on :8000 with .env
```

The container serves the built React app as static files from `/` — no separate web server needed.

---

## Deploy to Azure

### App Service (recommended for demo/evaluation)

```bash
# Build and push to Azure Container Registry
az acr build --registry <your-registry> --image o2c-intelligence:latest .

# Create App Service
az webapp create \
  --name o2c-intelligence \
  --resource-group <rg> \
  --plan <plan> \
  --deployment-container-image-name <your-registry>.azurecr.io/o2c-intelligence:latest

# Set required environment variables
az webapp config appsettings set \
  --name o2c-intelligence \
  --resource-group <rg> \
  --settings GEMINI_API_KEY=<key> WEBSITES_PORT=8000

# Health check endpoint
curl https://o2c-intelligence.azurewebsites.net/api/health
```

### Notes
- Azure injects `PORT` automatically — the app reads it
- Mount an Azure Files share to `/app/data` if you need persistent SQLite across restarts
- For production scale: set `DB_BACKEND=postgres` and point `POSTGRES_DSN` to Azure Database for PostgreSQL

---

## Project Structure

```
backend/
  agents/           8 specialist agents + orchestrator
  app/models/       Pydantic graph schema contracts
  ingestion/        Normalizer with Pydantic validation
  tests/            156 tests (unit + integration)
  main.py           FastAPI application
  ingest.py         One-shot data ingestion
  graph_builder.py  NetworkX graph construction
  guardrails.py     Domain rejection policy
  requirements.txt        Production dependencies
  requirements-dev.txt    Dev-only (pytest, ruff)
frontend/
  src/pages/        Landing + Workspace
  src/components/   Message, AgentTracePanel
  src/tests/        20 vitest tests
docs/
  architecture.md
  data-dictionary.md
  guardrails.md
  prompting-strategy.md
scripts/            dev_up.sh, dev_down.sh, quality_gate.sh
Dockerfile          Multi-stage production build
docker-compose.yml  Local container validation
pyproject.toml      ruff lint configuration
```

---

## Guardrails

- **Domain guard** — keyword allowlist rejects off-topic queries before any LLM call
- **SQL safety** — mutation keywords (`INSERT`, `UPDATE`, `DELETE`, etc.) are blocked; only `SELECT`/`WITH` execute
- **Injection prevention** — table names validated against regex allowlist; string literals stripped of control characters
- **Grounding guard** — empty results return a deterministic "no data" response; no hallucination
- **Circuit breaker** — opens after 3 consecutive DB failures, closes after 60s recovery

---

## Example Queries

| Query | Intent | Method |
|-------|--------|--------|
| *Top 5 customers by net amount* | `analyze` | Deterministic template |
| *Trace invoice 90000322* | `trace_flow` | Deterministic template |
| *Show orders delivered but not billed* | `detect_anomaly` | Deterministic template |
| *Most sold product* | `analyze` | Deterministic template |
| *trc inv 90000322* (shorthand) | `trace_flow` | Typo correction → template |
| *custmer with highest pymnt amout* | `analyze` | Typo correction → template |
