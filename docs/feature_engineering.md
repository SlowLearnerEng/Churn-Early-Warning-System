# Feature Engineering Plan

## Principles

| Principle | Application |
| --- | --- |
| Point-in-time correctness | Build features as of a scoring date and avoid future leakage. |
| Rolling windows | Compute 7, 30, 60, 90, and 180 day windows for behavior. |
| Trend over snapshot | Use deltas and slopes to catch early decline. |
| Entity-specific baselines | Compare each seller/buyer against their own history and cohort. |
| Explainability | Every high-weight feature maps to a human-readable reason code. |

## Seller Features

| Feature | Formula | Reason Hypothesis |
| --- | --- | --- |
| `response_rate_30d` | responded non-spam inquiries / total non-spam inquiries in last 30 days | Lower response predicts seller disengagement and lower ROI. |
| `response_rate_delta_90d` | response_rate_30d - response_rate_prev_90d | Sharp decline is stronger than low absolute rate alone. |
| `avg_response_minutes_30d` | avg(first_response_ts - inquiry_ts) | Slow responses reduce buyer satisfaction and conversion. |
| `sla_breach_rate_30d` | responses beyond SLA / responded inquiries | Operational friction signal. |
| `lead_utilization_score` | 100 * (0.4*response + 0.25*SLA + 0.2*followup + 0.15*conversion) | Measures whether seller extracts value from leads. |
| `catalog_staleness_days` | as_of_date - last_catalog_update_date | Stale catalog reduces discovery and shows disengagement. |
| `catalog_quality_score` | weighted product images, descriptions, category tags, price completeness | Low quality weakens conversion and perceived ROI. |
| `buyer_repeat_count_90d` | count distinct buyers with 2+ interactions | Repeat buyers create retention stickiness. |
| `sentiment_avg_30d` | avg message sentiment | Negative interactions can precede churn. |
| `graph_degree_90d` | distinct buyers interacting with seller | Isolated sellers are fragile. |

## Buyer Features

| Feature | Formula | Reason Hypothesis |
| --- | --- | --- |
| `inquiries_30d` | count inquiries in last 30 days | Demand-side activity. |
| `inquiry_decline_pct` | max(0, baseline_90d - inquiries_30d) / baseline_90d | Drop in inquiry generation predicts buyer churn. |
| `avg_order_value_delta_90d` | avg_order_value_30d - avg_order_value_prev_90d | Lower purchase intent. |
| `repeat_seller_count_90d` | sellers with repeated buyer interactions | Network stickiness. |
| `message_read_rate_30d` | read messages / received messages | Buyer responsiveness. |
| `seasonal_adjusted_activity` | activity_30d / same-season historical activity | Reduces false positives for seasonal buyers. |

## Subscription Features

| Feature | Formula | Reason Hypothesis |
| --- | --- | --- |
| `days_to_renewal` | renewal_date - as_of_date | Urgency amplifier. |
| `usage_decline_pct_90d` | max(0, usage_baseline_90d - usage_30d) / usage_baseline_90d | Early warning signal. |
| `feature_adoption_score` | weighted use of paid features | Low adoption means weak plan value. |
| `estimated_roi_score` | normalized qualified lead value / package value | Low ROI perception predicts non-renewal. |
| `prior_grace_period_count` | grace periods across renewals | Payment/renewal friction. |
| `upgrade_downgrade_signal` | +1 upgrade, 0 stable, -1 downgrade | Downgrade can be partial churn. |

## Temporal Features

| Feature | Formula |
| --- | --- |
| `weekly_lead_slope_8w` | linear regression slope of weekly leads received over 8 weeks |
| `weekly_response_slope_8w` | linear regression slope of weekly response rate |
| `consecutive_decline_weeks` | count consecutive weeks where key metric decreased |
| `activity_momentum` | 0.5*metric_7d + 0.3*metric_30d + 0.2*metric_90d |
| `recency_days` | as_of_date - latest meaningful event |

## RFM Features

| Feature | Formula |
| --- | --- |
| `recency_score` | percentile rank of inverse days since last activity |
| `frequency_score` | percentile rank of inquiries/messages/orders |
| `monetary_score` | percentile rank of order/package value |
| `rfm_health_score` | 0.35*recency + 0.35*frequency + 0.30*monetary |

## Graph Features

| Feature | Formula | Interpretation |
| --- | --- | --- |
| `seller_degree_90d` | unique buyers connected to seller | Network breadth. |
| `repeat_edge_ratio` | repeat buyer-seller edges / all edges | Relationship depth. |
| `power_buyer_dependency` | value from top 3 buyers / total value | Concentration risk. |
| `relationship_decay` | 1 - recent edge weight / historical edge weight | Weakening relationships. |
| `category_cluster_risk` | avg risk of similar sellers in city/category | Local market signal. |

## Sample Calculations

### Response Rate Drop

```text
response_rate_baseline_90d = 0.78
response_rate_30d = 0.46
response_rate_delta_90d = 0.46 - 0.78 = -0.32
```

Reason code: `response_rate_drop`.

### Lead Utilization Score

```text
response_component = 0.46
sla_component = 0.38
followup_component = 0.52
conversion_component = 0.11

lead_utilization_score =
100 * (0.4*0.46 + 0.25*0.38 + 0.2*0.52 + 0.15*0.11)
= 39.95
```

Reason code: `lead_utilization_decline`.

### Priority Score

```text
churn_risk = 78
value_percentile = 82
recoverability = 70
urgency = 59
strategic_weight = 75

priority =
0.40*78 + 0.25*82 + 0.15*70 + 0.10*59 + 0.10*75
= 75.6
```

## Feature Importance Hypotheses

| Rank | Feature | Expected Direction |
| --- | --- | --- |
| 1 | `usage_decline_pct_90d` | higher decline increases premium churn risk |
| 2 | `response_rate_delta_90d` | larger negative delta increases risk |
| 3 | `lead_utilization_score` | lower score increases risk |
| 4 | `days_to_renewal` | near renewal amplifies risk |
| 5 | `feature_adoption_score` | lower adoption increases premium churn risk |
| 6 | `catalog_staleness_days` | older catalog increases risk |
| 7 | `repeat_edge_ratio` | lower ratio increases risk |
| 8 | `sentiment_avg_30d` | negative sentiment increases risk |

## Leakage Controls

| Risk | Guardrail |
| --- | --- |
| Using renewal outcome in features | Exclude post-renewal status from pre-renewal training rows. |
| Future messages included in scoring | Enforce `event_timestamp <= as_of_date`. |
| Intervention effect leakage | Mark intervention windows and use pre-action features for prediction. |
| Synthetic labels too deterministic | Add calibrated noise and probabilistic label sampling. |

