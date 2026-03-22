# Demo Script (5-7 minutes)

## 1) Intro (30 sec)
- Explain objective: graph-based O2C tracing with NL querying and guardrails.

## 2) Graph Exploration (60 sec)
- Open graph overview.
- Click node, show inspector metadata.
- Expand neighbors.

## 3) Required Query A (60 sec)
- Ask: top products by billing-document associations.
- Show answer + referenced node highlights.

## 4) Required Query B (75 sec)
- Ask: trace full flow for a billing document.
- Show order -> delivery -> billing -> journal/payment path.

## 5) Required Query C (75 sec)
- Ask: show broken/incomplete flows.
- Show delivered-not-billed and billed-without-delivery anomalies.

## 6) Guardrail Demo (45 sec)
- Ask unrelated prompt (e.g., write a poem).
- Show policy rejection response.

## 7) Closing (30 sec)
- Mention architecture, test coverage, and AI log bundle location.
