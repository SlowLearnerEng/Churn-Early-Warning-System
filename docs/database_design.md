# Database And Warehouse Design

## Modeling Approach

Use OLTP tables for workflow state and warehouse tables for analytics. Daily feature and score tables are append-only by `as_of_date` to support audits, drift checks, and point-in-time model training.

## Core Tables

### sellers

| Column | Type | Meaning | Sample |
| --- | --- | --- | --- |
| seller_id | varchar(32) pk | seller id | S000042 |
| business_category | varchar(128) | primary category | Industrial Pumps |
| city | varchar(64) | city | Pune |
| state | varchar(64) | state | Maharashtra |
| subscription_tier | varchar(32) | plan tier | premium_plus |
| onboarding_date | date | first active date | 2023-08-12 |
| gst_verified | boolean | trust flag | true |
| created_at | timestamptz | load timestamp | 2026-05-15T07:00:00Z |

### buyers

| Column | Type | Meaning | Sample |
| --- | --- | --- | --- |
| buyer_id | varchar(32) pk | buyer id | B000121 |
| industry | varchar(128) | buyer industry | Construction |
| region | varchar(32) | region bucket | West |
| activity_level | varchar(32) | active/seasonal/declining/dormant | active |
| created_at | timestamptz | load timestamp | 2026-05-15T07:00:00Z |

### inquiries

| Column | Type | Meaning |
| --- | --- | --- |
| transaction_id | varchar(32) pk | inquiry/transaction id |
| seller_id | varchar(32) | seller receiving inquiry |
| buyer_id | varchar(32) | buyer initiating inquiry |
| transaction_type | varchar(16) | ENQ, BL, C2C, PNS |
| inquiry_timestamp | timestamptz | inquiry time |
| response_timestamp | timestamptz null | first response time |
| response_sla | varchar(32) | within_2h, same_day, delayed, no_response |
| conversion_status | varchar(32) | converted, abandoned, pending, spam |
| order_value | numeric(14,2) | order value |
| payment_status | varchar(32) | paid, pending, failed, not_applicable |
| communication_count | int | message count |
| negotiation_duration_hours | numeric(10,2) | negotiation length |
| lead_source | varchar(64) | search, category, paid_lead, repeat_buyer |

### messages

| Column | Type | Meaning |
| --- | --- | --- |
| message_id | varchar(32) pk | message id |
| txn_id | varchar(32) | inquiry id |
| sender_id | varchar(32) | sender id |
| receiver_id | varchar(32) | receiver id |
| message_type | varchar(32) | inquiry, reply, quote, system, followup |
| timestamp | timestamptz | message time |
| read_status | varchar(16) | read/unread |
| response_latency_minutes | numeric(10,2) null | response latency |
| sentiment | numeric(4,3) | -1 to 1 |
| escalation_flag | boolean | escalation marker |

### subscriptions

| Column | Type | Meaning |
| --- | --- | --- |
| subscription_id | varchar(32) pk | subscription period id |
| seller_id | varchar(32) | seller id |
| plan_type | varchar(32) | plan |
| renewal_date | date | renewal/expiry date |
| renewal_history | int | count of prior renewals |
| package_value | numeric(14,2) | annual contract value |
| usage_score | numeric(5,2) | usage health |
| feature_adoption_score | numeric(5,2) | premium feature use |
| login_frequency | numeric(8,2) | weekly login frequency |
| churn_outcome | int | 1 if not renewed/downgraded |

### contactbook

| Column | Type | Meaning |
| --- | --- | --- |
| contactbook_id | varchar(32) pk | relationship id |
| seller_id | varchar(32) | seller id |
| buyer_id | varchar(32) | buyer id |
| interaction_frequency | numeric(8,2) | monthly contact frequency |
| last_contacted_at | timestamptz | latest contact |
| relationship_strength | numeric(5,2) | relationship score |
| repeat_business_score | numeric(5,2) | repeat business score |
| saved_contact_flag | boolean | saved relationship flag |

## Feature Tables

### seller_health_daily

| Column | Type | Meaning |
| --- | --- | --- |
| seller_id | varchar(32) | seller id |
| as_of_date | date | snapshot date |
| active_days_30d | int | active days in last 30 days |
| inquiries_received_30d | int | recent leads |
| handled_leads_30d | int | responded leads |
| response_rate_30d | numeric(5,4) | handled / received |
| avg_response_minutes_30d | numeric(10,2) | latency |
| conversion_rate_90d | numeric(5,4) | converted / inquiries |
| lead_utilization_score | numeric(5,2) | composite |
| catalog_quality_score | numeric(5,2) | product/catalog quality |
| catalog_staleness_days | int | days since catalog update |
| buyer_repeat_count_90d | int | repeat buyer count |
| sentiment_avg_30d | numeric(4,3) | avg sentiment |
| graph_degree_90d | int | unique buyer relationships |
| created_at | timestamptz | pipeline timestamp |

Primary key: `(seller_id, as_of_date)`.

### buyer_health_daily

| Column | Type | Meaning |
| --- | --- | --- |
| buyer_id | varchar(32) | buyer id |
| as_of_date | date | snapshot date |
| inquiries_30d | int | recent inquiries |
| inquiries_baseline_90d | numeric(10,2) | prior baseline |
| inquiry_decline_pct | numeric(6,3) | decline |
| avg_order_value_90d | numeric(14,2) | order value |
| repeat_seller_count_90d | int | repeat sellers |
| message_response_rate_30d | numeric(5,4) | communication health |
| created_at | timestamptz | pipeline timestamp |

### engagement_features

Generic feature store table for model training and serving.

| Column | Type | Meaning |
| --- | --- | --- |
| entity_type | varchar(32) | seller/buyer/subscription |
| entity_id | varchar(32) | entity id |
| as_of_date | date | snapshot |
| feature_name | varchar(128) | feature name |
| feature_value | numeric | value |
| window_days | int | window |
| source_table | varchar(128) | lineage |

### subscription_risk

| Column | Type | Meaning |
| --- | --- | --- |
| subscription_id | varchar(32) | subscription id |
| seller_id | varchar(32) | seller |
| as_of_date | date | snapshot |
| days_to_renewal | int | renewal proximity |
| usage_score_30d | numeric(5,2) | current usage |
| usage_score_baseline_90d | numeric(5,2) | baseline |
| usage_decline_pct | numeric(6,3) | decline |
| feature_adoption_score | numeric(5,2) | adoption |
| estimated_roi_score | numeric(5,2) | ROI proxy |
| renewal_risk_score | numeric(5,2) | 0-100 |
| risk_band | varchar(16) | low/medium/high/critical |

## Score And Workflow Tables

### churn_scores

| Column | Type | Meaning |
| --- | --- | --- |
| score_id | varchar(32) pk | score id |
| entity_type | varchar(32) | seller/buyer/subscription |
| entity_id | varchar(32) | entity id |
| as_of_date | date | score date |
| model_name | varchar(64) | rule_engine, gbm_v1 |
| model_version | varchar(32) | version |
| horizon_days | int | prediction horizon |
| risk_score | numeric(5,2) | 0-100 |
| risk_band | varchar(16) | low/medium/high/critical |
| confidence | numeric(5,4) | 0-1 |
| reason_codes | jsonb | explanation reasons |
| revenue_at_risk | numeric(14,2) | value |
| created_at | timestamptz | timestamp |

### alert_events

| Column | Type | Meaning |
| --- | --- | --- |
| alert_id | varchar(32) pk | alert id |
| score_id | varchar(32) | linked score |
| entity_type | varchar(32) | entity |
| entity_id | varchar(32) | entity id |
| severity | varchar(16) | medium/high/critical |
| title | varchar(256) | alert title |
| status | varchar(32) | open/in_progress/resolved/suppressed |
| owner_id | varchar(32) | sales owner |
| priority_score | numeric(5,2) | queue priority |
| created_at | timestamptz | created |
| resolved_at | timestamptz null | resolution |

### retention_actions

| Column | Type | Meaning |
| --- | --- | --- |
| action_id | varchar(32) pk | action id |
| alert_id | varchar(32) | alert |
| entity_type | varchar(32) | entity |
| entity_id | varchar(32) | entity id |
| action_code | varchar(64) | playbook code |
| owner_id | varchar(32) | owner |
| scheduled_at | timestamptz | planned time |
| completed_at | timestamptz null | completion |
| status | varchar(32) | scheduled/completed/cancelled |
| outcome | varchar(128) null | result |
| notes | text | notes |

### intervention_history

| Column | Type | Meaning |
| --- | --- | --- |
| history_id | varchar(32) pk | history id |
| action_id | varchar(32) | action |
| entity_id | varchar(32) | entity |
| pre_risk_score | numeric(5,2) | risk before |
| post_risk_score | numeric(5,2) | risk after |
| renewed_flag | boolean | renewed |
| revenue_saved | numeric(14,2) | attributed value |
| attribution_method | varchar(64) | ab_test, rule, observational |
| measured_at | date | outcome date |

## Warehouse Models

| Model | Grain | Purpose |
| --- | --- | --- |
| `mart_renewal_watchlist` | seller-subscription-day | sales prioritization. |
| `mart_churn_funnel` | cohort-risk-band-week | executive reporting. |
| `mart_intervention_uplift` | action-code-month | playbook effectiveness. |
| `mart_category_health` | category-city-week | supply/demand liquidity monitoring. |
| `mart_account_360` | seller-day | dashboard drilldown. |

## Indexing

| Table | Index |
| --- | --- |
| `churn_scores` | `(entity_type, entity_id, as_of_date desc)`, `(risk_band, as_of_date)` |
| `alert_events` | `(owner_id, status, priority_score desc)`, `(created_at desc)` |
| `seller_health_daily` | `(seller_id, as_of_date desc)` |
| `subscription_risk` | `(days_to_renewal, risk_band)`, `(seller_id, as_of_date desc)` |

