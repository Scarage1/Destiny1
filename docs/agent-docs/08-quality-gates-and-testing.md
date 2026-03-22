# 08 - Quality Gates and Testing

## Mandatory gates per ticket
- Lint passes
- Type-check passes
- Relevant unit tests pass
- Relevant integration tests pass

## Assignment-critical integration tests
1. Products associated with highest number of billing documents
2. Full billing flow trace
3. Broken/incomplete flow detection

## Guardrail tests
- Off-domain prompt rejection
- Unsafe/mutation query rejection
- No-data-no-claim fallback behavior

## Reliability checks
- Query timeout enforcement
- Row limit enforcement
- Stable response contract shape
- Trace id propagation

## Production-readiness checks
- No secrets committed
- No broken links in docs
- Public demo route accessible
- README setup instructions verified from clean environment
