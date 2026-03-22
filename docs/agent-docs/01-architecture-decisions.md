# 01 - Architecture Decisions (Locked)

## ADR-001: System architecture
- Decision: Modular monolith
- Why: Fast delivery under deadline, clean boundaries, easier testing and integration.

## ADR-002: Data storage
- Decision: Neo4j property graph
- Why: Natural fit for lineage and flow traversal, simpler than complex relational joins for this use case.

## ADR-003: Query strategy
- Decision: SQL-only in v1 (SQLite execution)
- Why: Matches current implementation, keeps delivery risk low, and avoids dual SQL/Cypher failure surface before deadline.

## ADR-004: LLM strategy
- Decision: 2-stage approach
  1) NL -> constrained Cypher
  2) Result -> grounded natural-language answer
- Why: Better control, traceability, and failure isolation.

## ADR-005: Guardrail order
1. Domain intent check
2. Schema whitelist validation
3. Query safety validation
4. Read-only execution
5. Grounded synthesis

## ADR-006: Provider choice
- Primary: Gemini
- Fallback: Groq
- Why: Free-tier availability, practical latency and quality.

## ADR-007: Product priority
- Decision: correctness over UI polish
- Why: Matches evaluation rubric and reliability requirements.

## ADR-008: JournalEntry handling
- Decision: Conditional entity in v1
- Why: Include only if present in dataset; avoid fabricated structure.
