# Synthetic Dataset Design

## Goal

Generate a realistic, interconnected B2B marketplace dataset ecosystem that supports ML training, churn scoring, dashboards, cohort analysis, retrieval-augmented agent workflows, and business impact storytelling.

The supplied workbook is treated as schema inspiration, not as sufficient training data. The generated data normalizes workbook patterns into clean demo-ready tables.

## Datasets

| Dataset | Target Hackathon Scale | Entity Grain | Key Relationships |
| --- | ---: | --- | --- |
| `sellers` | 10,000+ | one row per seller | joins to subscriptions, inquiries, messages, contactbook |
| `buyers` | 50,000+ | one row per buyer | joins to inquiries, messages, contactbook |
| `inquiries` | 1,000,000+ | one row per inquiry/transaction | buyer_id, seller_id |
| `messages` | millions | one row per message | transaction_id, sender_id, receiver_id |
| `subscriptions` | 10,000+ | one row per subscription period | seller_id |
| `contactbook` | 100,000+ | one seller-buyer relationship | seller_id, buyer_id |
| `interventions` | configurable | one retention action | seller_id, alert_id |
| `daily_features` | configurable | seller_id by date | feature snapshots |

## Entity Relationship Description

```text
sellers 1--N subscriptions
sellers 1--N inquiries N--1 buyers
inquiries 1--N messages
sellers 1--N contactbook N--1 buyers
sellers 1--N daily_features
sellers 1--N interventions
daily_features 1--N churn_scores
```

## Seller Dataset

| Field | Type | Sample | Meaning |
| --- | --- | --- | --- |
| seller_id | string | S000042 | Primary key. |
| business_category | string | Industrial Pumps | Seller category. |
| city | string | Pune | Operating city. |
| state | string | Maharashtra | Operating state. |
| subscription_tier | string | premium_plus | active plan tier. |
| onboarding_date | date | 2023-08-12 | first platform date. |
| response_rate | float | 0.74 | recent response rate. |
| avg_response_minutes | float | 82.4 | recent average response latency. |
| product_count | int | 36 | listed product count. |
| catalog_quality_score | float | 78.0 | quality of catalog content. |
| lead_utilization_score | float | 64.0 | share/quality of handled leads. |
| gst_verified | bool | true | trust verification flag. |
| trust_score | float | 84.0 | aggregate trust indicator. |
| churn_label | int | 0 | synthetic ground truth. |
| churn_risk_score | float | 37.2 | generated latent risk. |

## Buyer Dataset

| Field | Type | Sample | Meaning |
| --- | --- | --- | --- |
| buyer_id | string | B00000121 | Primary key. |
| industry | string | Construction | buyer industry. |
| inquiry_frequency | float | 4.8 | avg monthly inquiries. |
| average_order_value | float | 72000 | estimated order value. |
| engagement_score | float | 63.2 | buyer activity score. |
| repeat_interaction_score | float | 44.7 | strength of repeated seller relationships. |
| region | string | West | operating region. |
| activity_level | string | active | active/seasonal/declining/dormant. |
| churn_label | int | 0 | synthetic buyer churn. |

## Inquiries / Transactions

| Field | Type | Sample | Meaning |
| --- | --- | --- | --- |
| transaction_id | string | T000000042 | Primary key. |
| buyer_id | string | B00000121 | inquiry initiator. |
| seller_id | string | S000042 | seller receiving lead. |
| transaction_type | string | ENQ | enquiry/buylead/C2C/PNS. |
| inquiry_timestamp | datetime | 2026-02-10 12:35:00 | inquiry time. |
| response_timestamp | datetime/null | 2026-02-10 13:14:00 | first seller response. |
| response_sla | string | within_2h | SLA bucket. |
| conversion_status | string | converted | converted/abandoned/pending/spam. |
| order_value | float | 118000 | estimated or actual value. |
| payment_status | string | paid | paid/pending/failed/not_applicable. |
| communication_count | int | 7 | message count. |
| negotiation_duration_hours | float | 26.5 | first to final message. |
| lead_source | string | search | source channel. |

## Messages

| Field | Type | Sample | Meaning |
| --- | --- | --- | --- |
| message_id | string | M00000001 | Primary key. |
| sender_id | string | B00000121 | sender. |
| receiver_id | string | S000042 | receiver. |
| txn_id | string | T000000042 | transaction link. |
| message_type | string | inquiry | inquiry/reply/system/followup/quote. |
| timestamp | datetime | 2026-02-10 12:36:00 | message time. |
| read_status | string | read | read/unread. |
| response_latency_minutes | float/null | 39.0 | response latency when applicable. |
| sentiment | float | 0.34 | -1 to 1 sentiment. |
| escalation_flag | bool | false | dispute or escalation indicator. |

## Subscription Dataset

| Field | Type | Sample | Meaning |
| --- | --- | --- | --- |
| subscription_id | string | SUB000042 | Primary key. |
| seller_id | string | S000042 | seller. |
| plan_type | string | premium_plus | plan. |
| renewal_date | date | 2026-07-20 | expiry/renewal date. |
| renewal_history | int | 3 | prior renewals. |
| package_value | float | 65000 | annual value. |
| usage_score | float | 58.0 | current usage health. |
| feature_adoption_score | float | 45.0 | adoption of premium features. |
| login_frequency | float | 5.2 | weekly logins. |
| churn_outcome | int | 0 | final renewal/churn label. |

## Contactbook

| Field | Type | Sample | Meaning |
| --- | --- | --- | --- |
| contactbook_id | string | CB0000001 | Primary key. |
| seller_id | string | S000042 | seller. |
| buyer_id | string | B00000121 | buyer. |
| interaction_frequency | float | 3.1 | monthly interactions. |
| last_contacted_at | datetime | 2026-03-01 09:10:00 | latest contact. |
| relationship_strength | float | 72.0 | graph edge weight. |
| repeat_business_score | float | 60.0 | repeat purchase likelihood. |
| saved_contact_flag | bool | true | explicit saved relationship. |

## Realistic Distribution Logic

| Behavior | Generation Strategy |
| --- | --- |
| Marketplace long tail | Pareto distribution for seller lead volume and buyer order value. |
| Category seasonality | Festival spikes, quarter-end procurement, monsoon/construction cycles. |
| Response behavior | Premium/high-performing sellers respond faster; at-risk sellers degrade over time. |
| Fraud/spam | Small percentage of inquiries marked spam with low conversion and abnormal messaging. |
| Renewal risk | 90-day pre-renewal decline in usage, leads handled, feature adoption, and response rate. |
| Recovery | Some high-risk sellers improve after intervention, creating measurable uplift. |
| Cold start | Newly onboarded sellers have sparse history and lower confidence. |

## Ground Truth Labels

Synthetic churn labels are not random. A latent risk score is generated from:

```text
seller_churn_latent =
  0.22 * inactivity_score
+ 0.18 * response_degradation
+ 0.16 * lead_utilization_decline
+ 0.14 * low_feature_adoption
+ 0.12 * catalog_staleness
+ 0.10 * poor_conversion
+ 0.08 * negative_sentiment
+ noise
```

Premium churn outcome adds renewal proximity and package value sensitivity:

```text
premium_churn_latent =
  0.35 * usage_decline_90d
+ 0.20 * days_to_renewal_urgency
+ 0.15 * low_roi_realization
+ 0.15 * feature_adoption_gap
+ 0.10 * prior_grace_periods
+ 0.05 * sentiment_risk
```

Risk scores are calibrated to 0-100 and converted into labels through probabilistic sampling. This preserves uncertainty and prevents labels from becoming a trivial formula.

## Edge Cases

| Scenario | Representation |
| --- | --- |
| High-value but inactive premium seller | High package value, low recent activity, high risk. |
| Seasonal buyer | Cyclical activity with lower off-season false-positive risk. |
| Bot/spam buyer | High inquiry volume, low response/conversion, spam flag. |
| Isolated seller | Low graph degree and relationship strength. |
| Sudden engagement crash | Sharp rolling-window decline after stable baseline. |
| Recovery after intervention | Risk decline after action date and usage rebound. |
| Missing data | Null response timestamps, unknown payment status, cold-start confidence. |

