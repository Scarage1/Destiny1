# Contributing

## Branching
- One ticket per branch.
- Naming:
  - feat/T#-short-name
  - fix/T#-short-name
  - test/T#-short-name
  - docs/T#-short-name
- No direct commits to main.

## Commits
Use Conventional Commits:
- feat(scope): ...
- fix(scope): ...
- test(scope): ...
- docs(scope): ...
- chore(scope): ...

## Pull Requests
PR must include:
1. Ticket ID
2. Acceptance criteria mapping
3. Validation evidence
4. Risk and rollback
5. AI log reference

## Merge Rules
Required checks:
- lint
- type-check
- unit tests
- integration tests
- secret scan

## Coding Standards
- Keep changes scoped.
- Preserve contracts unless explicitly changed.
- Add tests for every functional change.
