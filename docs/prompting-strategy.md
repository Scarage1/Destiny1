# Prompting Strategy

## NL to SQL Generation Prompt
The generator prompt includes:
- Full schema description from SQLite metadata
- Explicit business relationship hints for O2C lineage
- Strict SQL-only constraints
- Output restriction: raw SQL text only

## Retry Strategy
If execution fails:
1. Capture database error
2. Re-prompt model with original question + failed SQL + error
3. Re-run safety validation before retry execution

## Answer Synthesis Prompt
The synthesis prompt enforces:
- Result-grounded answer construction
- Explicit no-fabrication rule
- Concise presentation with IDs/values

## Deterministic Overrides
To reduce model variance:
- Off-domain prompt bypasses LLM and returns policy response
- Empty query-result bypasses LLM and returns deterministic no-data message

## Limitations
- SQL quality depends on model performance for complex joins
- No static parser yet for deep SQL semantic validation beyond current safety checks
