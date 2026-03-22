# Agent Docs - Graph-Based Data Modeling and Query System

This folder is the single execution source for AI agents and human operators.

## How to use
1. Read [00-project-charter.md](00-project-charter.md).
2. Read [01-architecture-decisions.md](01-architecture-decisions.md).
3. Execute work using [04-agent-operating-model.md](04-agent-operating-model.md).
4. Pick next ticket from [05-ticket-backlog.md](05-ticket-backlog.md).
5. Run prompts from [06-subagent-prompt-pack.md](06-subagent-prompt-pack.md).
6. Enforce standards in [07-git-and-branching-standards.md](07-git-and-branching-standards.md) and [08-quality-gates-and-testing.md](08-quality-gates-and-testing.md).
7. Follow time-boxes in [09-day-by-day-command-center.md](09-day-by-day-command-center.md).
8. Complete delivery using [10-submission-checklist.md](10-submission-checklist.md).

## Project constraints
- Deadline: 26 March 2026, 11:59 PM IST.
- Priority order: correctness > guardrails > traceability > UI polish.
- Free-tier tooling only.
- No authentication required for demo.

## Locked stack
- Frontend: React + TypeScript
- Backend: FastAPI
- Graph DB: Neo4j (Aura primary, local fallback)
- LLM: Gemini primary, Groq fallback

## Non-negotiables
- No data-backed result, no claim.
- Off-domain prompts must be rejected.
- Read-only query execution path.
- One ticket per branch, one PR per ticket.
