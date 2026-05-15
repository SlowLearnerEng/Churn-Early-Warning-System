# Dashboard And UI Design

## Design Principles

The demo UI should feel like an operational sales and retention command center, not a marketing landing page. Prioritize dense, scannable tables, drilldowns, filters, and evidence cards.

## Global Navigation

| Area | Purpose |
| --- | --- |
| Executive | Retention KPIs and revenue-at-risk. |
| Watchlist | Prioritized sellers/subscribers needing action. |
| Seller 360 | Account-level explanation and next action. |
| Cohorts | Category, city, tier, and tenure analysis. |
| Interventions | Action status and outcome tracking. |
| Model Monitor | Precision, recall, drift, and alert health. |

## Executive Dashboard

| Widget | Description |
| --- | --- |
| Revenue at risk | INR value by risk band and renewal month. |
| Retention lift estimate | Simulated or measured uplift from interventions. |
| Renewal funnel | Upcoming renewals, high-risk renewals, actioned, retained. |
| Churn heatmap | Category by city risk concentration. |
| Top drivers | Aggregate reason-code distribution. |
| Intervention ROI | Revenue saved by action type and owner team. |

## Sales Watchlist

| Column | Description |
| --- | --- |
| Priority | Composite priority score. |
| Seller | Name/id, category, city. |
| Renewal | Days to renewal and package value. |
| Risk | Score and band. |
| Reasons | Top 2 reason chips. |
| Recommended action | Playbook action. |
| Owner | Sales/account owner. |
| Status | Open, scheduled, completed, suppressed. |

Filters:

| Filter | Values |
| --- | --- |
| Risk band | medium, high, critical |
| Renewal window | 0-30, 31-60, 61-90 days |
| Package value | percentile buckets |
| Category | marketplace category |
| City/state | geography |
| Owner | sales owner |

## Seller Health Dashboard

### Header

| Field | Example |
| --- | --- |
| Seller | S000042 |
| Category | Industrial Pumps |
| City | Pune |
| Plan | premium_plus |
| Renewal | 41 days |
| Package value | INR 65,000 |

### Explanation Cards

| Card | Example |
| --- | --- |
| Risk score | 78 high, confidence 0.86. |
| Response decline | 78% to 46% in 30 days. |
| Lead utilization | Three consecutive weekly drops. |
| Catalog staleness | 122 days since last product refresh. |
| ROI evidence | 420 qualified leads in 6 months. |

### Trend Charts

| Chart | Reason |
| --- | --- |
| Leads received vs handled | Shows utilization and missed opportunity. |
| Response rate over time | Shows behavioral decline. |
| Conversion rate by week | Shows ROI realization. |
| Feature adoption | Shows premium value usage. |
| Buyer relationship graph summary | Shows repeat business strength. |

### AI Retention Panel

Outputs:

| Section | Content |
| --- | --- |
| Risk explanation | One paragraph grounded in metrics. |
| Reasons to stay | Three account-specific proof points. |
| Sales opener | Short call script opening. |
| Next best action | Action, due date, owner, expected outcome. |

## Cohort Dashboard

| View | Description |
| --- | --- |
| Renewal month cohort | Churn risk by renewal month. |
| Category cohort | Risk and drivers by category. |
| Tenure cohort | New, mature, long-tenure seller patterns. |
| Geography cohort | City/state risk map. |
| Tier cohort | Free/basic/premium/premium_plus behavior. |

## Intervention Tracker

| Widget | Description |
| --- | --- |
| Action queue | Scheduled and overdue actions. |
| Playbook success | Renewal lift by action code. |
| Owner leaderboard | Retained revenue and completed actions. |
| Discount dependency | Retention achieved with and without discount. |
| Outcome timeline | Pre-risk and post-risk changes. |

## Demo Interaction Flow

1. Start on Executive dashboard and point to revenue at risk.
2. Click high-risk premium renewals.
3. Sort watchlist by priority score.
4. Open Seller 360 for a high-value seller.
5. Review explanation cards and trends.
6. Generate AI retention summary.
7. Create intervention record.
8. Return to Executive dashboard and show projected revenue saved.

## Visual Encoding

| Element | Encoding |
| --- | --- |
| Risk band | Low green, medium amber, high orange, critical red. |
| Trend direction | Up/down arrows with absolute and percent delta. |
| Confidence | Small meter or text next to score. |
| Reason codes | Compact chips with hover detail. |
| Action state | Open, scheduled, completed, suppressed badges. |

