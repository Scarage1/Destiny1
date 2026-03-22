# 12 - Master Tracker

| ID | Title | Priority | Status | Owner | Depends On | Gate |
|---|---|---|---|---|---|---|
| T1 | Data profiling and dictionary | P0 | Done | Planner/Builder | - | Data map complete |
| T2 | Graph schema v1 | P0 | Done | Planner | T1 | Contract frozen |
| T3 | Normalization pipeline | P0 | Done | Builder | T1,T2 | Deterministic output |
| T4 | Idempotent graph loader | P0 | Done | Builder | T3 | Rerun-safe verified |
| T5 | Flow integrity tests | P0 | Done | Reviewer | T4 | Required tests pass |
| T6 | Guardrails and safety | P0 | Done | Builder/Reviewer | T5 | Rejection rules pass |
| T7 | NL to SQL | P0 | Done | Builder | T6 | Contract + safety pass |
| T8 | Query execution normalization | P0 | Done | Builder | T7 | Stable payload |
| T9 | Grounded answer synthesis | P0 | Done | Builder | T8 | Grounding policy pass |
| T10 | API endpoints | P0 | Done | API Builder | T9 | API contracts pass |
| T11 | Frontend core UX | P0 | Done | Frontend Builder | T10 | End-to-end UI pass |
| T12 | Docs/demo/submission | P0 | Review | Integrator/DocOps | T11 | Submission-ready |

## Status values
- Not Started
- In Progress
- Review
- Blocked
- Done

## Current audit reference
- See [13-current-state-audit-2026-03-23.md](13-current-state-audit-2026-03-23.md)

## Daily standup format
1. Completed yesterday
2. Planned today
3. Blockers
4. Decisions needed
5. ETA to next gate
