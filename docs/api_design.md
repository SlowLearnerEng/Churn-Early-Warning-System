# API Design

## Assumptions

| Topic | Decision |
| --- | --- |
| Protocol | HTTPS JSON APIs. |
| Auth | OAuth2/JWT with role claims for sales, manager, analyst, admin. |
| Pagination | Cursor-based for alert queues and history endpoints. |
| Latency | Single-entity scoring p95 under 200 ms; AI summaries p95 under 5 seconds. |
| Versioning | Prefix with `/v1`. |
| Idempotency | Mutating intervention endpoints accept `Idempotency-Key`. |

## POST /v1/churn/predict

Scores one or more entities.

### Request

```json
{
  "horizon_days": 90,
  "entities": [
    {
      "entity_type": "seller",
      "entity_id": "S000042",
      "as_of_date": "2026-05-15"
    }
  ],
  "include_explanations": true
}
```

### Response

```json
{
  "results": [
    {
      "entity_type": "seller",
      "entity_id": "S000042",
      "as_of_date": "2026-05-15",
      "risk_score": 78.4,
      "risk_band": "high",
      "confidence": 0.86,
      "revenue_at_risk": 65000,
      "top_reasons": [
        {
          "code": "response_rate_drop",
          "severity": "high",
          "evidence": "response_rate_30d dropped from 0.78 to 0.46"
        },
        {
          "code": "lead_utilization_decline",
          "severity": "medium",
          "evidence": "handled leads declined for 3 consecutive weeks"
        }
      ],
      "recommended_action": "sales_call_with_roi_summary"
    }
  ]
}
```

## GET /v1/sellers/{seller_id}/health

Returns seller health, feature trends, subscription risk, and explainability cards.

### Response

```json
{
  "seller_id": "S000042",
  "profile": {
    "business_category": "Industrial Pumps",
    "city": "Pune",
    "subscription_tier": "premium_plus",
    "package_value": 65000
  },
  "health": {
    "risk_score": 78.4,
    "risk_band": "high",
    "confidence": 0.86,
    "days_to_renewal": 41
  },
  "trend_cards": [
    {
      "metric": "response_rate",
      "current": 0.46,
      "baseline": 0.78,
      "delta": -0.32,
      "direction": "down"
    }
  ],
  "alerts": [
    {
      "alert_id": "ALT000123",
      "severity": "high",
      "status": "open",
      "title": "Premium renewal risk within 90 days"
    }
  ]
}
```

## GET /v1/buyers/{buyer_id}/health

Returns buyer activity risk and demand pattern.

```json
{
  "buyer_id": "B00000121",
  "risk_score": 61.8,
  "risk_band": "medium",
  "activity_level": "declining",
  "top_reasons": [
    "inquiry_count_30d is 65% below historical baseline",
    "repeat seller interactions down from 5 to 1"
  ]
}
```

## GET /v1/alerts

Paginated alert work queue for sales/retention teams.

### Query Parameters

| Name | Example | Meaning |
| --- | --- | --- |
| `risk_band` | high,critical | filter by risk band |
| `owner_id` | E12345 | sales owner |
| `entity_type` | seller | seller/buyer/subscription |
| `status` | open | open/in_progress/resolved/suppressed |
| `cursor` | opaque token | next page cursor |
| `limit` | 50 | max rows |

### Response

```json
{
  "items": [
    {
      "alert_id": "ALT000123",
      "entity_type": "seller",
      "entity_id": "S000042",
      "severity": "high",
      "risk_score": 78.4,
      "priority_score": 82.1,
      "owner_id": "E12345",
      "title": "Response rate and lead utilization decline",
      "created_at": "2026-05-15T07:00:00+05:30"
    }
  ],
  "next_cursor": "eyJwYWdlIjoyfQ"
}
```

## POST /v1/recommendations/next-best-action

Generates or retrieves intervention recommendation.

### Request

```json
{
  "entity_type": "seller",
  "entity_id": "S000042",
  "risk_score": 78.4,
  "reason_codes": ["response_rate_drop", "lead_utilization_decline"],
  "constraints": {
    "max_discount_percent": 10,
    "sales_capacity": "normal"
  }
}
```

### Response

```json
{
  "action_code": "sales_call_with_roi_summary",
  "priority": "high",
  "owner_role": "account_manager",
  "due_in_hours": 72,
  "rationale": "High revenue at risk, clear recoverable usage decline, renewal in 41 days.",
  "playbook_steps": [
    "Open with historical qualified leads and repeat buyer evidence.",
    "Review response time and missed-lead pattern.",
    "Offer catalog optimization before discounting."
  ]
}
```

## POST /v1/ai/retention-summary

Generates a grounded AI summary for a seller/buyer/subscriber.

### Request

```json
{
  "entity_type": "seller",
  "entity_id": "S000042",
  "purpose": "sales_call_script",
  "language": "en",
  "max_words": 180
}
```

### Response

```json
{
  "summary": "Risk is high because response rate dropped from 78% to 46%, lead utilization has declined for three weeks, and renewal is 41 days away.",
  "reasons_to_stay": [
    "You generated 420 qualified leads in the last 6 months.",
    "67 leads came from repeat buyers, showing relationship value.",
    "Demand in Industrial Pumps is up 18% in Pune this quarter."
  ],
  "sales_opening_line": "I am calling because your account has produced strong buyer interest, but recent lead handling has dropped and we can recover that before renewal.",
  "evidence_ids": ["seller_health_daily:S000042:2026-05-15", "subscription_risk:SUB000042"]
}
```

## POST /v1/interventions

Creates an intervention record.

```json
{
  "alert_id": "ALT000123",
  "entity_type": "seller",
  "entity_id": "S000042",
  "action_code": "sales_call_with_roi_summary",
  "owner_id": "E12345",
  "scheduled_at": "2026-05-16T10:30:00+05:30"
}
```

## PATCH /v1/interventions/{intervention_id}

Updates action status and outcome.

```json
{
  "status": "completed",
  "outcome": "seller_committed_catalog_refresh",
  "notes": "Seller agreed to update top 15 products and enable quick replies."
}
```

## Error Model

```json
{
  "error": {
    "code": "ENTITY_NOT_FOUND",
    "message": "Seller S000042 was not found.",
    "request_id": "req_abc123"
  }
}
```

