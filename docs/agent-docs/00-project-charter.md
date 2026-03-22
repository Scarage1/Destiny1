# 00 - Project Charter

## Objective
Build a context graph system that unifies fragmented business entities (orders, deliveries, invoices, payments, customers, products, address) and answers natural-language questions with dataset-grounded responses.

## Assignment outcomes
- Graph construction from dataset
- Graph visualization UI (expand, inspect metadata, view relationships)
- Conversational query interface
- Dynamic NL to structured query generation
- Guardrails for out-of-domain prompts
- Public demo + public repository + professional README + AI logs

## Success criteria
1. Required query classes work:
   - Top products by billing-document count
   - Full flow trace for billing document
   - Broken/incomplete flow detection
2. Answers are traceable to query results.
3. Off-topic prompts rejected with policy response.
4. Clean and maintainable codebase with tests and docs.

## In-scope for v1
- End-to-end NL query pipeline
- Core graph model and traversal
- UI with chat + graph explorer + inspector + answer-path highlight
- Guardrails and safety validation

## Out-of-scope for v1
- Authentication/authorization UX
- Complex role-based access control
- Advanced graph clustering analytics
- Multi-tenant architecture

## Decision priorities
1. Query correctness
2. Guardrail reliability
3. Traceability/observability
4. Code quality and professional docs
5. UI enhancements
