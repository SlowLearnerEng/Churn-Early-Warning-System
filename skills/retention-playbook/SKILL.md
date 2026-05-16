---
name: retention-playbook
description: Map B2B marketplace seller churn signals to specific retention interventions, sales talk tracks, and escalation rules. Use when an agent needs to decide which action to take for an at-risk seller, write a personalised outreach script, assign owner priority, sequence a multi-step retention campaign, or calculate intervention ROI for a B2B marketplace.
compatibility: No runtime dependencies. Instructions and reference materials only.
metadata:
  author: IndiaMART
  version: "1.0"
---

# Retention Playbook

Translate churn risk scores and reason codes into the right retention action, owner, timeline, and messaging.

## Action Code → Intervention Mapping

| Reason Code | Action Code | Owner | SLA |
| --- | --- | --- | --- |
| `service_deactivation` | `urgent_manager_escalation` | Senior Manager | 4 hours |
| `high_negative_intent` + high/critical band | `sales_call_with_roi_summary` | Account Manager | 24 hours |
| `low_call_pickup` | `response_time_coaching` | Success Coach | 48 hours |
| `high_cancellation_rate` | `service_value_review` | Account Manager | 48 hours |
| `unresponsive_to_reviews` | `review_response_training` | Success Coach | 72 hours |
| `untouched_leads` | `lead_handling_workshop` | Success Coach | 72 hours |
| `declining_buyleads` | `catalogue_refresh_session` | Catalogue Specialist | 5 days |
| `renewal_approaching` | `renewal_conversation` | Account Manager | 72 hours |
| `subscription_expired` | `win_back_offer` | Senior Account Manager | 24 hours |
| `low_rating` | `quality_improvement_call` | Success Coach | 48 hours |
| Default (no critical code) | `automated_health_nudge` | System | — |

## Escalation Rules

1. Any `critical` risk band → escalate to Senior Manager regardless of reason code.
2. `service_deactivation` ticket present → freeze all upsell conversations; solve the operational issue first.
3. Subscription expired > 90 days → win-back offer only; do not invoice for full renewal until trust is restored.
4. `buyer_conflicts` ticket open → do not send automated nudges; route to human review.
5. Conflicting signals (high engagement + high cancellation rate) → hold automation; AM reviews manually.

## ROI Justification Framework

When running a `sales_call_with_roi_summary`, build the value case using these metrics:

1. **Lead volume**: enquiries and BuyLeads received in last 30 days vs. zero without subscription.
2. **Buyer diversity**: count of unique buyers who contacted the seller in the period.
3. **Conversion proxy**: `call_pickup_pct × total_enquiries` = estimated buyer contacts made.
4. **Peer benchmark**: seller's category average (if cohort data is available).
5. **Cost per lead**: `package_value / total_enquiries_30d` — frame renewal as cost per qualified buyer.

Never invent metrics. If a field is missing, say the evidence is unavailable and recommend a diagnostic step instead.

## Retention Summary Template

Generate AI-backed retention summaries only from supplied evidence. Use this structure:

1. **Risk sentence** — one sentence naming the risk band and primary reason code with metric evidence.
2. **Three reasons to stay** — evidence-backed; use actual numbers from the account (enquiries, pickup rate, rating).
3. **Next best action** — one specific step with owner, timeline, and expected outcome.
4. **Sales opening line** — personalised with company name, product category, and a specific metric.
5. **JSON action summary** — CRM-safe structured record of the recommendation.

### Example output shape

```json
{
  "risk_sentence": "Crown Solutions is at HIGH risk due to 42% cancellation rate and 3 open service tickets.",
  "reasons_to_stay": [
    "Received 187 enquiries in the last 30 days — equivalent to ₹1.1L in lead value at market rate.",
    "Call pickup rate improved from 48% to 61% month-over-month, showing buyer demand is rising.",
    "Catalogue score of 78 places them in the top 30% of their category."
  ],
  "next_best_action": "Account Manager to call within 24 hours with ROI summary and service resolution update.",
  "sales_opening_line": "Hi, I'm calling about the 187 enquiries Crown Solutions received last month — I want to make sure you're converting those into orders.",
  "action_summary": {
    "action_code": "sales_call_with_roi_summary",
    "owner": "account_manager",
    "due_hours": 24,
    "seller_id": "10211"
  }
}
```

## Priority Scoring

When ranking which sellers to action first:

```
priority = 0.50 × risk_score
         + 0.25 × min(revenue_at_risk / 5000, 100)
         + 0.25 × (100 - min(days_to_renewal_clamped_0_to_100, 100))
```

Sort descending. Action top priority sellers first within each SLA window.

## Intervention ROI Benchmarks

| Action Type | Estimated ROI Multiple | Typical Success Rate |
| --- | --- | --- |
| Urgent manager escalation | 3.2× | 55% |
| Renewal conversation | 3.0× | 50% |
| Sales call with ROI summary | 2.8× | 45% |
| Response time coaching | 2.6× | 40% |
| Catalogue refresh session | 2.1× | 35% |
| Review response training | 1.8× | 30% |
| Lead handling workshop | 1.5× | 28% |
| Automated health nudge | 1.3× | 15% |

## Measurement

Track retention lift per cohort weekly:

- **30-day callback rate** after intervention (did the seller respond?)
- **60-day renewal conversion rate** (did they renew?)
- **Revenue recovered** vs. cost of outreach (ROI realised)
- **Intervention completion rate** per owner (operational health)
