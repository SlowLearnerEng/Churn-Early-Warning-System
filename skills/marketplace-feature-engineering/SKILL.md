---
name: marketplace-feature-engineering
description: Engineer behavioral features from raw B2B marketplace CSV exports for churn prediction and seller health analysis. Use when an agent needs to transform transaction, call, ticket, catalogue, or rating data into rolling-window features, trend deltas, engagement scores, or churn labels ready for ML models or rule engines.
compatibility: Requires Python 3.8+ with pandas and openpyxl installed.
metadata:
  author: IndiaMART
  version: "1.0"
---

# Marketplace Feature Engineering

Transform raw B2B marketplace exports into ML-ready behavioral feature sets covering seller activity, communication quality, product catalogue health, and subscription signals.

## Pipeline

Run in order:

```bash
# Step 1: Export Excel workbook to CSVs
python scripts/export_excel_to_csv.py

# Step 2: Engineer features from CSVs
python scripts/build_features.py
```

Output: `outputs/real/seller_features.csv` — one row per seller, ~111 features.

## Input Sources

| Dataset | CSV Path | Key Fields |
| --- | --- | --- |
| Seller profiles | `data/csv/dataset - seller_profile.csv` | seller_id, package, subscription dates, verification |
| Seller activity | `data/csv/dataset - seller_activity.csv` | period_days (7/30/90), bl_active, call_pickup_pct, replies |
| Buyer-seller calls | `data/csv/dataset - buyer_seller_calls.csv` | seller_intent, call_duration_mins |
| Tickets | `data/csv/dataset - seller_tickets.csv` | ticket_type, risk_level, status |
| Transactions | `data/csv/dataset - seller_transactions.csv` | is_cancellation, total_amount_rs |
| Ratings | `data/csv/dataset - seller_ratings.csv` | overall_rating, response_satisfaction_pct |
| Reviews | `data/csv/dataset - seller_low_rating_reviews.csv` | rating, response_by_seller |
| Contact book | `data/csv/dataset - seller_contact_book.csv` | untouched_flag |
| Trends | `data/csv/dataset - seller_monthly_weekly_trends.csv` | period_type, buyleads, enquiries |

## Feature Groups

### Activity Features (`act_7d_`, `act_30d_`, `act_90d_` prefix)

Derived per rolling period from `seller_activity.csv`:

- `bl_active` — BuyLead days active in window
- `call_pickup_pct` — call answer rate
- `total_enquiries` — inbound enquiries received
- `total_calls` — total calls attempted
- `callbacks`, `replies` — seller-initiated engagement

### Communication Quality

- `negative_intent_pct` — share of calls where seller intent is "Considering Cancellation" or "Disengaged" (from `buyer_seller_calls.csv`)
- `untouched_pct` — share of contact book entries with `untouched_flag = 1`
- `low_review_response_rate` — fraction of sub-4-star reviews that received a seller reply

### Subscription Health

- `days_to_renewal` — integer days from today to `subscription_end_date`; negative means expired
- `cancellation_rate` — cancelled transactions / total transactions
- `total_spend` — sum of all non-cancellation transaction amounts

### Trend Signals

- `buylead_trend` — % change in buyleads: current month vs prior month (from monthly trends)
- `enquiry_trend` — % change in enquiries: current month vs prior month

### Support Signals

- `open_tickets` — count of unresolved tickets
- `conflict_tickets` — count of buyer-supplier conflict tickets
- `deactivation_tickets` — count of service deactivation requests

### Churn Label

`churned = 1` when any of the following is true:

- A service deactivation ticket exists
- `days_to_renewal < -30` AND `act_30d_total_enquiries = 0` AND `act_30d_total_calls = 0`
- `cancellation_rate > 0.40`

## Key Rules

- Use 30-day window as primary period; 90-day for baselines and trend comparison.
- `days_to_renewal` below −180 means long-lapsed — treat separately from recently expired (−30 to 0).
- `negative_intent_pct` is derived from the `seller_intent` field in calls, not from chat messages.
- Exclude test or unverified accounts (`verification_score < 2`) when computing churn labels.
- Point-in-time safety: never leak future-period activity into past-period feature windows.

## Common Issues

| Issue | Fix |
| --- | --- |
| Missing `seller_activity.csv` | Run `export_excel_to_csv.py` first |
| All sellers show 0 for `negative_intent_pct` | Check that `seller_intent` column uses exact strings "Considering Cancellation" / "Disengaged" |
| `days_to_renewal` is float | Cast to int after computing; null means no subscription end date on record |
| Imbalanced churn label | Expected ~40–60% churn rate for this dataset; use `class_weight='balanced'` in downstream ML |
