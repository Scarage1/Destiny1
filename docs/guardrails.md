# Guardrails and Safety Policy

## Scope Guardrail
Primary policy response:

> This system is designed to answer questions related to the SAP Order-to-Cash dataset only.

Off-domain prompts are rejected before query generation.

## SQL Safety Guardrail
The query validator enforces:
- Read-only query class (`SELECT` / `WITH`)
- Mutation keyword blocking (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, etc.)
- Dangerous pattern blocking (multi-statement injection patterns)
- Limit enforcement through sanitization (`LIMIT 100` when missing)

## Grounding Guardrail
- If query returns no rows, response is deterministic:
  - `No matching records found in the dataset.`
- Answers must be grounded in query result rows.

## Verification Coverage
Implemented tests:
- [backend/tests/unit/test_guardrails.py](backend/tests/unit/test_guardrails.py)
- [backend/tests/integration/test_guardrail_rejections.py](backend/tests/integration/test_guardrail_rejections.py)
- [backend/tests/unit/test_query_pipeline_contract.py](backend/tests/unit/test_query_pipeline_contract.py)
