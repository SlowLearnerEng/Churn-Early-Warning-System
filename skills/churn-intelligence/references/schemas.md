# Churn Intelligence Schemas

## Entity Map

| Entity | Primary Key | Description |
| --- | --- | --- |
| Seller | `seller_id` | Marketplace supplier or premium subscriber. |
| Buyer | `buyer_id` | Demand-side user generating inquiries and orders. |
| Inquiry | `transaction_id` | Buyer-seller lead, enquiry, buylead, C2C, or PNS event. |
| Message | `message_id` | Communication event attached to a transaction. |
| Subscription | `subscription_id` | Seller paid plan period and renewal state. |
| Contactbook | `contactbook_id` | Seller-buyer relationship edge. |
| Churn score | `score_id` | Point-in-time risk prediction. |
| Alert | `alert_id` | Routed work item for a retention owner. |

## Key Relationships

```text
seller 1--N subscription
seller 1--N inquiry N--1 buyer
inquiry 1--N message
seller 1--N contactbook N--1 buyer
seller/buyer/subscription 1--N churn_score
churn_score 1--N alert_event
alert_event 1--N retention_action
```

## Feature Families

| Family | Feature Names |
| --- | --- |
| Engagement | `active_days_30d`, `login_frequency`, `messages_sent_30d`, `inquiries_received_30d` |
| Responsiveness | `response_rate_7d`, `response_rate_30d`, `avg_response_minutes_30d`, `sla_breach_rate_30d` |
| Monetization | `package_value`, `order_value_90d`, `average_order_value`, `revenue_at_risk` |
| Lead quality | `conversion_rate_90d`, `abandoned_inquiry_rate_30d`, `spam_lead_rate_30d` |
| Subscription | `days_to_renewal`, `usage_score`, `feature_adoption_score`, `renewal_history` |
| Catalog | `product_count`, `catalog_quality_score`, `catalog_staleness_days` |
| Contactbook | `relationship_strength`, `repeat_business_score`, `saved_contact_flag` |
| Graph | `graph_degree_90d`, `repeat_edge_ratio`, `power_buyer_dependency`, `relationship_decay` |
| Decline | `response_rate_delta_90d`, `usage_decline_pct`, `lead_utilization_drop_30d` |

## Recommended Feature Formulas

| Feature | Formula |
| --- | --- |
| `response_rate_30d` | responded inquiries in 30 days / total non-spam inquiries in 30 days |
| `lead_utilization_score` | 100 * weighted average of response, SLA, follow-up, and conversion behavior |
| `usage_decline_pct` | max(0, baseline_usage_90d - usage_30d) / baseline_usage_90d |
| `catalog_staleness_days` | as_of_date - latest product/catalog update date |
| `relationship_strength` | weighted recency, frequency, repeat business, saved contact, and message depth |
| `engagement_entropy` | entropy of active days/channels; low entropy can indicate one-channel dependency |
| `priority_score` | 0.40*risk + 0.25*value + 0.15*recoverability + 0.10*urgency + 0.10*strategic_weight |

## Reason Codes

| Code | Meaning |
| --- | --- |
| `response_rate_drop` | Current response rate is materially below baseline. |
| `low_response_rate` | Seller is ignoring too many leads. |
| `lead_utilization_decline` | Seller is receiving leads but not handling them effectively. |
| `slow_response_time` | Response latency is likely hurting conversions. |
| `catalog_staleness` | Catalog has not been refreshed recently. |
| `low_feature_adoption` | Premium features are not being used. |
| `low_premium_usage` | Paid plan usage is weak. |
| `renewal_in_90_days` | Account is inside renewal risk window. |
| `buyer_inquiry_decline` | Buyer inquiry behavior is down vs baseline. |
| `weak_repeat_relationships` | Buyer/seller repeat network is weak. |

