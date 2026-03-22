# 02 - System Design

## High-level flow
1. User asks a natural-language question.
2. Backend checks domain relevance.
3. LLM generates schema-constrained Cypher.
4. Safety validator blocks unsafe patterns.
5. Query executes via read-only Neo4j credentials.
6. Results are normalized to a stable contract.
7. LLM synthesizes grounded answer from results only.
8. UI renders answer and highlights referenced graph nodes/edges.

## Backend modules
- domain: typed models and contracts
- ingestion: profile, normalize, validate
- graph: schema setup, load, traversal
- llm: prompts, generator, parser, guardrails, answer synthesis
- query: execution and normalization
- api: route orchestration and error mapping

## Frontend modules
- chat: user question and response history
- graph: visualization and expansion
- inspector: node metadata panel
- api: typed client contracts
- state: session and UI states

## Required API behavior
- query endpoint returns:
  - answer
  - generated query (for traceability)
  - normalized rows/columns summary
  - referenced entities for highlight
  - trace id
- graph endpoints support:
  - node details
  - neighbors/expansion

## Error semantics
- Off-domain: deterministic policy response
- Unsafe query: blocked response
- Empty result: no-data grounded fallback
- Execution timeout: explicit timeout error
- Internal error: trace id included
