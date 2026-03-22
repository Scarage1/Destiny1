# 07 - Git and Branching Standards

## Branching model
- Protected main branch
- One ticket per short-lived branch
- Naming:
  - feat/T#-short-name
  - fix/T#-short-name
  - test/T#-short-name
  - docs/T#-short-name

## Commit policy
Use Conventional Commits:
- feat(scope): ...
- fix(scope): ...
- test(scope): ...
- docs(scope): ...
- chore(scope): ...

Rules:
- Atomic commits
- No mixed intent commits
- No direct commit to main

## PR policy
PR must include:
- Ticket id and scope
- Acceptance mapping checklist
- Validation evidence (lint/type/tests)
- Risk and rollback
- AI logs reference

## Merge policy
Required checks:
- backend lint/type/tests
- frontend lint/type/tests
- integration tests
- guardrail rejection tests
- secret scan

## Release tags
- v0.1-data-foundation
- v0.2-query-core
- v0.3-product-ui
- v1.0-submission
