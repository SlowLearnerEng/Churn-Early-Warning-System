# Data Dictionary

## sellers.csv

| Field | Type | Null Handling | Sample | Business Interpretation |
| --- | --- | --- | --- | --- |
| `seller_id` | string | required | S000042 | Seller primary key. |
| `business_name` | string | generated fallback | Aakriti Collection | Display name for demo. |
| `business_category` | string | required | Industrial Pumps | Main selling category. |
| `city` | string | required | Pune | Seller city. |
| `state` | string | required | Maharashtra | Seller state. |
| `region` | string | required | West | Sales/analytics region. |
| `subscription_tier` | string | required | premium_plus | Plan tier. |
| `archetype` | string | required | premium_at_risk | Synthetic behavior segment. |
| `onboarding_date` | date | required | 2023-08-12 | Seller tenure start. |
| `response_rate` | float | default 0 | 0.74 | Recent inquiry response share. |
| `avg_response_minutes` | float | default large | 82.4 | Seller response speed. |
| `product_count` | int | default 0 | 36 | Catalog breadth. |
| `catalog_quality_score` | float | median impute | 78.0 | Catalog completeness. |
| `lead_utilization_score` | float | median impute | 64.0 | Lead handling health. |
| `gst_verified` | bool | false | true | Trust signal. |
| `trust_score` | float | median impute | 84.0 | Composite trust/quality. |
| `churn_label` | int | required for training | 0 | Synthetic ground truth. |
| `churn_risk_score` | float | optional | 37.2 | Latent synthetic risk. |

## buyers.csv

| Field | Type | Null Handling | Sample | Business Interpretation |
| --- | --- | --- | --- | --- |
| `buyer_id` | string | required | B0000121 | Buyer primary key. |
| `industry` | string | unknown | Construction | Buyer business segment. |
| `region` | string | unknown | West | Buyer region. |
| `inquiry_frequency` | float | default 0 | 4.8 | Average monthly inquiry behavior. |
| `average_order_value` | float | default 0 | 72000 | Purchase intent proxy. |
| `engagement_score` | float | median impute | 63.2 | Buyer activity health. |
| `repeat_interaction_score` | float | median impute | 44.7 | Relationship stickiness. |
| `activity_level` | string | unknown | declining | Synthetic buyer segment. |
| `churn_label` | int | required for training | 0 | Buyer churn label. |

## inquiries.csv

| Field | Type | Null Handling | Sample | Business Interpretation |
| --- | --- | --- | --- | --- |
| `transaction_id` | string | required | T0000000042 | Inquiry primary key. |
| `buyer_id` | string | required | B0000121 | Demand-side entity. |
| `seller_id` | string | required | S000042 | Supply-side entity. |
| `transaction_type` | string | required | ENQ | Enquiry, buylead, C2C, PNS. |
| `inquiry_timestamp` | datetime | required | 2026-02-10 12:35:00 | Inquiry creation time. |
| `response_timestamp` | datetime | nullable | 2026-02-10 13:14:00 | First seller response. |
| `response_sla` | string | no_response | within_2h | Response quality bucket. |
| `conversion_status` | string | pending | converted | Outcome proxy. |
| `order_value` | float | 0 | 118000 | Estimated/actual value. |
| `payment_status` | string | not_applicable | paid | Payment state. |
| `communication_count` | int | 0 | 7 | Conversation depth. |
| `negotiation_duration_hours` | float | 0 | 26.5 | Deal cycle proxy. |
| `lead_source` | string | unknown | search | Source channel. |

## messages.csv

| Field | Type | Null Handling | Sample | Business Interpretation |
| --- | --- | --- | --- | --- |
| `message_id` | string | required | M000000000001 | Message primary key. |
| `sender_id` | string | required | B0000121 | Sender entity. |
| `receiver_id` | string | required | S000042 | Receiver entity. |
| `txn_id` | string | required | T0000000042 | Transaction link. |
| `message_type` | string | unknown | reply | Communication type. |
| `timestamp` | datetime | required | 2026-02-10 12:36:00 | Event time. |
| `read_status` | string | unread | read | Engagement signal. |
| `response_latency_minutes` | float | nullable | 39 | Response speed. |
| `sentiment` | float | 0 | 0.34 | Message sentiment. |
| `escalation_flag` | bool | false | false | Support/friction indicator. |

## subscriptions.csv

| Field | Type | Null Handling | Sample | Business Interpretation |
| --- | --- | --- | --- | --- |
| `subscription_id` | string | required | SUB000042 | Subscription primary key. |
| `seller_id` | string | required | S000042 | Seller. |
| `plan_type` | string | required | premium_plus | Paid plan. |
| `renewal_date` | date | required | 2026-07-20 | Renewal or expiry date. |
| `renewal_history` | int | 0 | 3 | Prior renewal count. |
| `package_value` | float | 0 | 65000 | Revenue at risk. |
| `usage_score` | float | median impute | 58.0 | Recent plan usage. |
| `feature_adoption_score` | float | median impute | 45.0 | Premium feature adoption. |
| `login_frequency` | float | 0 | 5.2 | Weekly login count. |
| `churn_outcome` | int | nullable until renewal | 0 | Non-renewal/downgrade outcome. |

## contactbook.csv

| Field | Type | Null Handling | Sample | Business Interpretation |
| --- | --- | --- | --- | --- |
| `contactbook_id` | string | required | CB00000001 | Relationship primary key. |
| `seller_id` | string | required | S000042 | Seller. |
| `buyer_id` | string | required | B0000121 | Buyer. |
| `interaction_frequency` | float | 0 | 3.1 | Monthly touch frequency. |
| `last_contacted_at` | datetime | nullable | 2026-03-01 09:10:00 | Recency. |
| `relationship_strength` | float | median impute | 72.0 | Edge strength. |
| `repeat_business_score` | float | median impute | 60.0 | Repeat likelihood. |
| `saved_contact_flag` | bool | false | true | Explicit seller-buyer relationship. |

## seller_health_daily.csv

| Field | Type | Null Handling | Sample | Business Interpretation |
| --- | --- | --- | --- | --- |
| `seller_id` | string | required | S000042 | Seller. |
| `as_of_date` | date | required | 2026-05-15 | Feature snapshot date. |
| `active_days_30d` | int | 0 | 12 | Recent active days. |
| `inquiries_received_30d` | int | 0 | 42 | Lead demand. |
| `handled_leads_30d` | int | 0 | 21 | Leads seller handled. |
| `response_rate_30d` | float | 0 | 0.50 | Recent response rate. |
| `avg_response_minutes_30d` | float | high default | 340 | Recent response latency. |
| `conversion_rate_90d` | float | 0 | 0.18 | Lead to order conversion. |
| `lead_utilization_score` | float | median impute | 44.0 | Lead handling composite. |
| `catalog_quality_score` | float | median impute | 67.0 | Catalog quality. |
| `catalog_staleness_days` | int | 999 when missing | 145 | Catalog freshness. |
| `buyer_repeat_count_90d` | int | 0 | 5 | Repeat buyer relationships. |
| `sentiment_avg_30d` | float | 0 | 0.12 | Communication tone. |
| `graph_degree_90d` | int | 0 | 11 | Relationship graph breadth. |

