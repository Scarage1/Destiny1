# 04 - Agent Operating Model

## Role model
- Principal-Planner: creates ticket scope and acceptance criteria
- Builder: implements scoped ticket only
- Reviewer: validates scope, quality, and test coverage
- Integrator: merge decision based on gates
- DocOps: updates docs, ADRs, and logs

## Execution cycle (must follow)
1. Planner creates ticket spec
2. Builder implements within scope
3. Reviewer audits pass/fail
4. Run gates (lint, type-check, tests)
5. Integrator decides merge/no-merge
6. DocOps records decision and documentation delta

## Anti-drift policy
- One ticket per branch
- Max 5 target files per ticket where practical
- No opportunistic refactors
- No cross-module scope creep
- If assumptions required, write them explicitly before coding

## Output contract for agents
Every agent response should include:
- What changed
- Why changed
- Validation completed
- Known risks

## Prompt discipline
Use deterministic prompts with:
- Scope boundaries
- Acceptance criteria
- Validation steps
- Explicit return format

## Escalation
If a ticket fails review twice:
- Stop and log blockers
- Split ticket into smaller scope
- Re-run Planner and continue
