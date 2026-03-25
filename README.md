# O2C Graph Intelligence

**Understand your Order-to-Cash system in seconds — natural language queries grounded in your data.**

> **Live Demo:** https://entitled-subsidiaries-foo-chrome.trycloudflare.com
> **Repository:** https://github.com/Scarage1/Destiny1

---

## What This Is

A context graph system with an LLM-powered query interface over a SAP Order-to-Cash dataset.

- Orders, deliveries, invoices, and payments are unified into an **interactive knowledge graph**
- A **ForceGraph2D canvas** lets users expand nodes and inspect relationships
- A **conversational chat interface** accepts natural language questions
- The system translates queries into **SQL dynamically**, executes them, and returns **data-backed answers**
- **Guardrails** reject off-domain prompts before any LLM call is made

---

## Architecture Decisions

### Why SQLite as the storage layer?

The dataset is a single flat-file export (~10k rows) with no concurrent write requirements. SQLite provides:

- **Zero-setup** — no server process, embeds directly into the Python process
- **Full SQL expressiveness** — complex joins across 10+ normalized tables with window functions
- **Deterministic execution** — the same query always returns the same rows, which is critical for grounded answers
- **Portability** — one `.db` file, trivial to checkpoint and reproduce

A graph database (Neo4j, etc.) was considered but rejected: the O2C domain's relationships are already fully expressible as foreign-key joins, and adding a Cypher layer would introduce translation overhead with no query capability benefit for this dataset size.

### Why NetworkX for the graph layer?

SQLite holds the source-of-truth data. NetworkX provides the **exploration and traversal** layer:

- Nodes are typed entities (Customer, SalesOrder, Delivery, etc.)
- Edges are typed relationships (PLACED → FULFILLED → BILLED → BOOKED)
- Subgraph traversal (BFS, hop-limited expansion) is built-in and fast for in-memory graphs at this scale
- No serialization round-trip — the graph is built once on startup and queried in-memory

### Why a multi-agent pipeline instead of direct NL→SQL?

Direct NL→SQL is unreliable: the model may hallucinate column names, generate UPDATE/DELETE statements, or miss JOIN conditions. The pipeline decomposes the problem:

```
User query
    → Guard Agent      [domain check — reject if off-topic]
    → Planner Agent    [extract structured intent: entity, metric, group_by, filter]
    → Query Agent      [match intent to deterministic SQL template; LLM only for novel queries]
    → Executor Agent   [circuit-breaker-protected SQL execution with retry]
    → Verifier Agent   [result sanity check]
    → Response Agent   [grounded NL answer from result rows]
```

**Deterministic templates handle ~80% of queries.** The LLM is only called for intent planning and for queries that don't match a template — reducing latency, cost, and hallucination risk.

---

## Graph Model

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
                    JournalEntry
                         │
                      SETTLED_BY
                         │
                         ▼
                       Payment
```

Nodes: `Customer`, `SalesOrder`, `SalesOrderItem`, `Delivery`, `DeliveryItem`, `BillingDocument`, `BillingDocumentItem`, `JournalEntry`, `Payment`, `Product`, `Plant`

---

## LLM Integration & Prompting Strategy

### Provider hierarchy
1. **Google Gemini** (`gemini-2.0-flash`) — primary, fastest
2. **Groq** (`llama-3.1-8b-instant`) — automatic fallback on timeout/rate-limit

### Intent planning prompt
The Planner receives:
- The user's raw query
- A schema summary (table names + key columns, no raw data)
- A structured output contract (JSON with `intent`, `entity`, `metric`, `group_by`, `filter`, `context_ids`)

Output is validated against a strict Pydantic schema before proceeding — malformed LLM output is rejected, not passed downstream.

### SQL generation prompt (fallback path only)
When no deterministic template matches:
- Full DDL schema is injected
- Business relationship hints are provided (`billing_document_headers.billingDocument = accounting_documents.billingDocument`)
- Hard constraint: output must be a single `SELECT` statement
- Retry with error feedback: on SQL execution failure, the error message and failed SQL are re-sent to the model for a corrected attempt

### Answer synthesis prompt
The Response Agent receives only the query result rows (not raw SQL). Rules:
- Answer must reference specific IDs/values from the result
- No fabrication if result is empty — returns a deterministic "No matching records found" message
- Business language enforced: translate column names to human-readable terms

---

## Guardrails

### Domain guard (Guard Agent)
- **Keyword allowlist**: queries must reference O2C concepts (customer, order, delivery, invoice, billing, payment, product, sales, journal, etc.)
- **Semantic reject patterns**: general knowledge, creative writing, math, off-topic requests trigger immediate rejection
- Response: *"This system is designed to answer questions related to the provided dataset only."*
- **Implemented and tested**: `backend/tests/unit/test_guardrails.py`, `backend/tests/integration/test_guardrail_rejections.py`

### SQL safety guard (Validator Agent)
- Mutation keyword blocking: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`
- Multi-statement injection blocking
- Automatic `LIMIT 100` injection when missing
- Query class enforcement: only `SELECT` / `WITH` queries execute

### Grounding guard (Verifier Agent)
- Empty result → deterministic "no data" response (no LLM hallucination)
- Result row count validated against intent (e.g. `trace_flow` expects at least one linked entity)

---

## Example Queries Supported

| Query | Intent | Method |
|-------|--------|--------|
| *Which products are associated with the highest number of billing documents?* | `analyze` | Deterministic template |
| *Trace the full flow of billing document 90000322* | `trace_flow` | Deterministic template |
| *Identify sales orders delivered but not billed* | `broken_flow` | Deterministic template |
| *Show customers with the most payments* | `analyze` | Deterministic template |
| *Find journal entry for invoice X* | `lookup` | Deterministic template |

---

## Bonus Features Implemented

- ✅ **NL → SQL translation** via constrained LLM prompt
- ✅ **Node highlighting** — query results highlight referenced graph nodes
- ✅ **Conversation memory** — follow-up questions use prior context
- ✅ **Groq fallback** — automatic provider failover
- ✅ **Deterministic SQL templates** — 80%+ of queries never call the LLM for SQL
- ✅ **Circuit breaker** on SQL executor (opens after 3 consecutive failures)
- ✅ **Agent trace UI** — per-query trace visible in chat panel

---

## Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/Scarage1/Destiny1
cd Destiny1
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

# 2. Configure API key
cp .env.example .env
# Edit .env: set GEMINI_API_KEY=your_key_here

# 3. Ingest data
python backend/ingest.py

# 4. Start services (separate terminals)
python backend/main.py          # API on :8000
cd frontend && npm install && npm run dev   # UI on :3000
```

Or use the convenience script: `bash scripts/dev_up.sh`

---

## Testing

```bash
# Backend (156 tests, 88% coverage)
python -m pytest -q

# Frontend (20 tests)
cd frontend && npm test

# Full quality gate
bash scripts/quality_gate.sh
```

---

## Project Structure

```
backend/
  agents/          # 8 specialist agents + orchestrator
  app/models/      # Pydantic graph schema contracts
  ingestion/       # Normalizer with Pydantic validation
  tests/           # 156 tests (unit + integration)
  main.py          # FastAPI app
  ingest.py        # One-shot data ingestion
  graph_builder.py # NetworkX graph construction
  guardrails.py    # Domain rejection policy
frontend/
  src/pages/       # Landing + Workspace
  src/components/  # Message, AgentTracePanel
  src/tests/       # 20 vitest tests
docs/
  architecture.md
  guardrails.md
  prompting-strategy.md
scripts/           # dev_up.sh, dev_down.sh, quality_gate.sh
```

---

## AI Coding Sessions

Session logs are in [`docs/ai-session-logs/`](docs/ai-session-logs/) — see the index for transcript locations.

This project was built using AI-assisted development (Antigravity / Gemini). The session transcripts cover planning, implementation, review, and production hardening phases.
