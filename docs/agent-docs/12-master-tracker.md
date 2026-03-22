# 12 - Master Tracker

| ID | Title | Priority | Status | Owner | Depends On | Gate |
|---|---|---|---|---|---|---|
| T1 | Data profiling and dictionary | P0 | Not Started | Planner/Builder | - | Data map complete |
| T2 | Graph schema v1 | P0 | Not Started | Planner | T1 | Contract frozen |
| T3 | Normalization pipeline | P0 | Not Started | Builder | T1,T2 | Deterministic output |
| T4 | Idempotent graph loader | P0 | Not Started | Builder | T3 | Rerun-safe verified |
| T5 | Flow integrity tests | P0 | Not Started | Reviewer | T4 | Required tests pass |
| T6 | Guardrails and safety | P0 | Not Started | Builder/Reviewer | T5 | Rejection rules pass |
| T7 | NL to Cypher | P0 | Not Started | Builder | T6 | Contract + safety pass |
| T8 | Query execution normalization | P0 | Not Started | Builder | T7 | Stable payload |
| T9 | Grounded answer synthesis | P0 | Not Started | Builder | T8 | Grounding policy pass |
| T10 | API endpoints | P0 | Not Started | API Builder | T9 | API contracts pass |
| T11 | Frontend core UX | P0 | Not Started | Frontend Builder | T10 | End-to-end UI pass |
| T12 | Docs/demo/submission | P0 | Not Started | Integrator/DocOps | T11 | Submission-ready |

## Status values
- Not Started
- In Progress
- Review
- Blocked
- Done

## Daily standup format
1. Completed yesterday
2. Planned today
3. Blockers
4. Decisions needed
5. ETA to next gate
