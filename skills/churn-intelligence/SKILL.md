---
name: churn-intelligence
description: Build, score, explain, and operate B2B marketplace churn early-warning workflows for sellers, buyers, and premium subscribers. Use when Codex needs churn definitions, feature engineering, 90-day renewal risk logic, retention playbooks, AI reasons-to-stay prompts, dataset generation support, dashboard/API/database designs, or hackathon-grade churn intelligence artifacts.
---

# Churn Intelligence

Use this skill to turn marketplace behavior data into explainable churn risk, renewal alerts, and retention actions.

## Core Workflow

1. Identify entity type: seller, buyer, or premium subscription.
2. Load the relevant schema reference from `references/schemas.md` only when field details are needed.
3. Compute or request rolling-window features: recency, frequency, monetary value, response quality, lead utilization, catalog health, subscription usage, contactbook strength, and trend deltas.
4. Score risk with a rule engine first. Use ML probabilities when available, but keep reason codes deterministic and auditable.
5. Map reason codes to a retention playbook from `references/playbooks.md`.
6. Generate a grounded retention summary using only provided account evidence.
7. Return structured output that matches `references/output_schemas.json`.

## Environment Variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `CHURN_SCORE_THRESHOLD_MEDIUM` | minimum medium-risk score | `40` |
| `CHURN_SCORE_THRESHOLD_HIGH` | minimum high-risk score | `60` |
| `CHURN_SCORE_THRESHOLD_CRITICAL` | minimum critical-risk score | `80` |
| `CHURN_RENEWAL_WINDOW_DAYS` | renewal warning horizon | `90` |
| `CHURN_MAX_SUMMARY_WORDS` | max AI summary length | `180` |

## Scoring Rules

Prioritize interpretable reasons over opaque scores. A useful risk output contains:

- Risk score from 0 to 100.
- Risk band: low, medium, high, critical.
- Confidence from 0 to 1.
- Top reason codes with metric evidence.
- Recommended next best action.
- Revenue at risk when subscription value is available.

Use `scripts/score_account.py` for deterministic account-level scoring.

## AI Retention Summary Rules

Generate retention copy only from supplied evidence. Do not invent counts, revenue, category demand, or benchmarks. If a metric is missing, say the evidence is unavailable and use a safer operational recommendation.

Good summary shape:

1. One-sentence risk explanation.
2. Three evidence-backed reasons to stay.
3. Next best action.
4. Sales opening line.
5. JSON-safe action summary.

## Examples

### Seller Risk

Input evidence:

```json
{
  "entity_type": "seller",
  "response_rate_30d": 0.46,
  "response_rate_baseline_90d": 0.78,
  "lead_utilization_score": 38,
  "avg_response_minutes_30d": 910,
  "catalog_staleness_days": 145,
  "days_to_renewal": 41,
  "package_value": 65000
}
```

Expected result:

- High or critical risk.
- Reasons include response rate drop, slow response time, lead utilization decline, catalog staleness, renewal in 90 days.
- Action: sales call with ROI summary plus catalog/response coaching.

### Buyer Risk

Use inquiry decline, inactivity, repeat seller count, order value decline, and message engagement. Avoid treating seasonal buyers as churned unless the decline breaks their normal seasonal pattern.

### Premium Renewal Risk

Use renewal proximity only as an amplifier, not a standalone risk reason. A seller near renewal with healthy usage should not be flagged high risk.

## Edge Cases

| Case | Handling |
| --- | --- |
| Cold start | Lower confidence; use onboarding health and early activation indicators. |
| Seasonal buyer | Compare against same-season baseline when possible. |
| Spam/fake leads | Exclude from seller performance penalties. |
| Missing subscription | Score behavioral churn and omit revenue-at-risk. |
| LLM unavailable | Return deterministic reason-code explanation. |
| Conflicting signals | Surface confidence and top positive counter-signal. |

## Evaluation Logic

Use three layers:

| Layer | Metrics |
| --- | --- |
| ML | precision at action capacity, recall in top decile, PR AUC, calibration error. |
| Business | retention lift, revenue saved, intervention success, discount efficiency. |
| Operations | alert volume, duplicate suppression rate, SLA to action, owner completion rate. |

For hackathon demos, always show at least one account-level explanation and one aggregate impact metric.

## Bundled Resources

| Path | When To Use |
| --- | --- |
| `scripts/score_account.py` | Score a single account JSON payload. |
| `references/schemas.md` | Need field definitions, feature names, or entity relationships. |
| `references/playbooks.md` | Need intervention mapping or sales talk tracks. |
| `references/output_schemas.json` | Need strict JSON response contracts. |
| `assets/dashboard_wireframe.md` | Need a quick dashboard/demo layout. |

