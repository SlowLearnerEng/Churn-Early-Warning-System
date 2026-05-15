# Churn Intelligence Platform: Hackathon Submission

## 1. Executive Summary

The Churn Intelligence Platform is an explainable AI operating system for retention across sellers, buyers, and premium subscribers in a B2B marketplace. It combines behavioral feature engineering, churn prediction, 90-day renewal risk detection, AI-generated retention narratives, and sales-ready intervention playbooks.

| Dimension | Submission Claim |
| --- | --- |
| Business problem | High-value sellers, buyers, and premium subscribers show measurable decline before churn, but signals are distributed across messaging, inquiries, subscription, catalog, and contactbook data. |
| Core solution | A daily risk engine that predicts churn, explains causes, raises alerts, and recommends next-best actions. |
| Demo strength | Synthetic ecosystem large enough for dashboards, ML, cohort analysis, RAG summaries, and intervention tracking. |
| Primary users | Sales managers, account executives, retention teams, category heads, and customer-success analysts. |
| Judge impact | Clear revenue-saved story, operational workflow, robust architecture, and reusable skill framework. |

### North-Star Outcome

Reduce avoidable premium churn by prioritizing the accounts most likely to leave and giving sales teams a specific, evidence-backed reason to intervene.

## 2. Problem Framing

### Business Problem Statement

Premium marketplace subscribers and high-value marketplace participants often reduce activity before they formally churn. The business loses renewal revenue, category liquidity, buyer trust, and sales productivity when these warning signs are not detected early. The platform must identify churn risk early enough for a human or automated retention workflow to change the outcome.

### Churn Definitions

| Entity | Operational Churn Definition | Prediction Horizon | Primary Business Loss |
| --- | --- | --- | --- |
| Seller | No meaningful lead response, catalog update, login, or buyer engagement for a configured inactivity window. | 30, 60, 90 days | Lost supply liquidity and lower buyer fulfillment. |
| Buyer | No inquiry, message, repeat interaction, or order activity after historically regular usage. | 30, 60 days | Lost demand and weaker marketplace density. |
| Premium subscriber | Subscription not renewed, downgraded, or renewed only after heavy discount due to declining usage/ROI. | 90 days before renewal | Direct revenue leakage. |

### KPIs

| KPI | Formula | Why It Matters |
| --- | --- | --- |
| Retention lift | Renewal rate treatment - renewal rate control | Measures real business outcome. |
| Revenue saved | Sum(package_value * retained_probability_lift) | Converts model value into money. |
| Alert precision | True positive churn alerts / all churn alerts | Prevents sales fatigue. |
| Intervention success | Accounts retained after action / accounts actioned | Measures playbook quality. |
| Lead utilization recovery | Post-action handled leads - pre-action handled leads | Shows behavior change before renewal. |
| Median days of early warning | Alert date to renewal/churn date | Proves proactive value. |

### Impact Estimation

Assumptions for hackathon demo:

| Assumption | Value |
| --- | --- |
| Premium sellers monitored | 10,000 |
| Average annual package value | INR 45,000 |
| Baseline churn | 18% |
| Addressable churn | 35% of churned premium sellers |
| Achievable retention lift | 8 percentage points on actioned high-risk accounts |

Estimated annual premium revenue at risk:

```text
10,000 sellers * INR 45,000 * 18% = INR 81,000,000
```

Conservative revenue saved:

```text
10,000 sellers * 20% actioned high-risk * INR 45,000 * 8% lift = INR 7,200,000
```

The larger operational upside is sales productivity: teams spend call capacity on accounts where the model sees both high risk and high recoverable value.

### Leading and Lagging Indicators

| Type | Indicators |
| --- | --- |
| Leading | Response-rate decline, response-time increase, login decay, lead utilization drop, message ghosting, buyer repeat score decline, feature adoption decline, catalog staleness. |
| Lagging | Non-renewal, downgrade, long inactivity, revenue loss, lost buyer repeat activity. |
| Actionable | Accounts with high risk, high value, clear reason codes, and recommended interventions. |

## 3. Data Understanding

The sample workbook contains representative operational tables:

| Workbook Sheet | Interpreted Entity | Useful Signals |
| --- | --- | --- |
| `cb` | Seller-buyer contactbook relationships | Last contact, unread count, starred flag, message snippet, relationship status. |
| `cust_to_serv` | Customer-to-service subscription mapping | Start date, valid-up-to, service id, sales ownership, grace period, upgrade info. |
| `mcd` and `mcd all txn` | Message center detail | Sender/receiver, product, message type, read status, inquiry/reply/system events, timestamps. |
| `txn` | Transaction code dictionary | Meaning of event/ref types such as enquiry, buylead, PNS, C2C, system. |
| `Subscription dates` | Premium subscription status | Hosted date, expiry date, days before expiry, service id. |

### Inferred Entity Relationships

| Relationship | Cardinality | Notes |
| --- | --- | --- |
| Seller to subscription | 1 to many | A seller may renew, upgrade, downgrade, or churn across plan periods. |
| Buyer to inquiry | 1 to many | Buyers initiate enquiries across sellers and categories. |
| Seller to inquiry | 1 to many | Sellers receive leads and respond with varying speed/quality. |
| Inquiry to messages | 1 to many | Conversation depth and latency become churn features. |
| Seller to contactbook | 1 to many | Relationship strength supports repeat business and retention. |
| Seller/buyer to churn score | 1 to many over time | Daily snapshots support trend analysis. |

### Feature Inventory

| Category | Examples |
| --- | --- |
| Engagement | logins_30d, active_days_30d, messages_sent_30d, inquiry_count_30d |
| Monetization | package_value, order_value_90d, lead_value_estimate, revenue_at_risk |
| Responsiveness | response_rate_7d, avg_response_minutes_30d, sla_breach_rate_30d |
| Trust | gst_verified, trust_score, catalog_quality_score, dispute_rate |
| Activity | product_updates_60d, catalog_staleness_days, last_seen_days |
| Transaction quality | conversion_rate_90d, abandoned_inquiry_rate, spam_lead_rate |
| Communication | unread_count, ghosted_threads_30d, sentiment_avg_30d |
| Subscription health | days_to_renewal, feature_adoption_score, usage_score, renewal_history |
| Retention signals | historical_success_count, repeat_buyer_count, recovered_after_intervention |
| Decline signals | wo_w_drop_in_leads, response_rate_delta, usage_score_decay_90d |

## 4. Solution Architecture

### Logical Architecture

```text
Raw events -> Data quality checks -> Feature jobs -> Feature store
                         |                 |
                         v                 v
                  Entity profiles     Churn models
                         |                 |
                         v                 v
                 Risk explanations -> Alert engine -> Next best action
                         |                 |
                         v                 v
                   RAG context       Sales/dashboard APIs
                         |                 |
                         v                 v
                   AI retention agent and business impact tracker
```

### Services

| Service | Responsibility | SLA |
| --- | --- | --- |
| Event ingestion | Load inquiries, messages, catalog, subscription, contactbook events. | Near-real-time for events, daily for subscriptions. |
| Feature builder | Compute daily/weekly/monthly features and trend deltas. | Daily by 7 AM IST. |
| Model serving | Score seller, buyer, and subscription risk. | p95 under 200 ms for one account. |
| Explanation service | Convert top features into reason codes and human explanations. | p95 under 300 ms. |
| Alert engine | Apply thresholds, suppress duplicates, route by owner. | Daily batch plus streaming severe alerts. |
| AI retention agent | Generate personalized reasons to stay and intervention scripts. | p95 under 5 seconds. |
| Impact tracker | Attribute interventions to retention and revenue saved. | Daily refresh. |

## 5. ML Strategy

### Baseline: Rule Engine

| Aspect | Detail |
| --- | --- |
| Inputs | Recency, response-rate drop, lead utilization, days to renewal, feature adoption, catalog quality. |
| Output | Risk score 0-100, band, reason codes. |
| Pros | Explainable, fast, demo-ready, no label dependency. |
| Cons | Needs calibration, can miss nonlinear interactions. |
| Best use | MVP and fallback for cold-start or sparse labels. |

### Intermediate: LightGBM/XGBoost

| Aspect | Detail |
| --- | --- |
| Inputs | Aggregated numeric features and categorical encodings by account/day. |
| Output | Probability of churn by horizon. |
| Pros | Strong tabular performance, feature importance, fast inference. |
| Cons | Needs clean labels and drift monitoring. |
| Best use | Main hackathon model if enough synthetic or historical labels exist. |

### Advanced: Hybrid ML + LLM Explanation

| Aspect | Detail |
| --- | --- |
| Inputs | ML probability, SHAP/top feature reasons, historical account facts, playbooks. |
| Output | Personalized explanation, reasons to stay, next-best action. |
| Pros | Converts scores into action. |
| Cons | Requires guardrails, retrieval, and evidence grounding. |
| Best use | Demo differentiator. |

### Optional: Graph-Based Intelligence

Graph features identify isolated sellers, weakening buyer-seller relationships, power buyers shifting categories, and ecosystem risk around anchor sellers.

| Feature | Formula |
| --- | --- |
| seller_degree_90d | Unique buyers interacting with seller in last 90 days. |
| repeat_edge_ratio | Repeat buyer-seller edges / total edges. |
| power_buyer_dependency | Share of seller value from top 3 buyers. |
| relationship_decay | 1 - recent_edge_weight / historical_edge_weight. |

### Recommended Hackathon Approach

Use a three-layer stack:

1. Rule engine for transparent MVP scoring.
2. Scikit-learn gradient boosting/random forest fallback for trainable demo.
3. LLM-style retention agent using retrieved account facts and deterministic reason codes.

## 6. Early Warning Engine

### 90-Day Renewal Logic

| Signal | Trigger |
| --- | --- |
| Usage decay | usage_score_30d down more than 30% vs previous 90-day baseline. |
| Lead utilization decline | handled_leads_30d down more than 25% and unhandled leads rising. |
| Response degradation | response_rate_30d below 55% or down more than 20 points. |
| ROI risk | estimated order value or qualified leads below plan-cost benchmark. |
| Feature non-adoption | feature_adoption_score below 35 for premium plan. |
| Renewal proximity | days_to_renewal between 1 and 90. |

### Severity Bands

| Band | Score | Meaning | Action |
| --- | --- | --- | --- |
| Low | 0-39 | Healthy or insufficient risk. | Monitor. |
| Medium | 40-59 | Early decline visible. | Automated nudge or training content. |
| High | 60-79 | Clear churn pattern and value at risk. | Sales call within 72 hours. |
| Critical | 80-100 | Severe decline near renewal or repeated failed interventions. | Manager escalation and custom offer. |

### Alert Examples

| Alert | Evidence |
| --- | --- |
| Seller response rate dropped 42%. | response_rate_30d 81% to 47%; three-week negative trend. |
| Buyer inquiry activity down 65%. | inquiries_30d 23 vs baseline 66. |
| Lead utilization dropped for 3 consecutive weeks. | handled_leads weekly counts 18, 11, 7, 4. |
| Premium usage decline before renewal. | usage_score down 38%, renewal in 48 days. |

## 7. AI Agent Design

### Agent Workflow

| Step | Action |
| --- | --- |
| 1 | Receive entity id, score, band, horizon, and reason codes. |
| 2 | Retrieve account profile, subscription facts, recent trends, historical wins, and relevant playbook. |
| 3 | Generate a grounded risk explanation using only retrieved evidence. |
| 4 | Produce reasons to stay tailored to category, location, and historical success. |
| 5 | Recommend next best action and sales talking points. |
| 6 | Emit structured JSON for dashboard and CRM routing. |

### Prompt Template

```text
You are a retention intelligence assistant for a B2B marketplace.
Use only the provided account evidence. Do not invent metrics.

Account:
{account_profile}

Risk score:
{risk_score}

Top reason codes:
{reason_codes}

Historical wins:
{historical_success}

Applicable playbooks:
{playbook_snippets}

Return:
1. short risk explanation
2. three evidence-backed reasons to stay
3. next best action
4. sales call opening line
5. JSON-safe action summary
```

### Example Output

| Output | Example |
| --- | --- |
| Explanation | "Risk is high because response rate fell from 78% to 46%, lead utilization declined for 3 weeks, and renewal is 41 days away." |
| Reasons to stay | "You received 420 qualified leads in 6 months; 67 came from repeat buyers; your category demand is up 18% in your city." |
| Action | "Schedule sales call; focus on lead handling workflow and catalog refresh." |

## 8. Intervention Recommendation Engine

### Priority Score

```text
priority = 0.40 * churn_risk
         + 0.25 * revenue_at_risk_percentile
         + 0.15 * recoverability_score
         + 0.10 * days_to_renewal_urgency
         + 0.10 * strategic_category_weight
```

### Intervention Matrix

| Risk Driver | Recommended Intervention | Owner |
| --- | --- | --- |
| Slow response | Response-time coaching, WhatsApp quick-reply setup, SLA reminder. | Customer success |
| Low lead utilization | Lead handling walkthrough, lead quality review, CRM setup. | Sales |
| Poor catalog quality | Catalog optimization, product photo refresh, category tagging. | Seller ops |
| Low ROI perception | ROI summary, historical wins, category demand report. | Account manager |
| Renewal price sensitivity | Targeted discount only after usage fix attempted. | Retention manager |
| Negative sentiment | Escalation call and service recovery. | Support lead |

## 9. System Design

### Production Stack

| Component | Recommended Technology |
| --- | --- |
| Event bus | Kafka or cloud pub/sub |
| Batch orchestration | Airflow or Dagster |
| OLTP store | PostgreSQL |
| Warehouse | BigQuery, Snowflake, or Redshift |
| Feature store | Feast or custom daily feature tables |
| Cache | Redis |
| Vector DB | pgvector, OpenSearch, or managed vector store |
| Model serving | FastAPI + model registry |
| Monitoring | Prometheus, Grafana, Evidently, Great Expectations |

### Data Flow

1. Ingest raw operational tables from contactbook, message center, transactions, subscriptions, catalog, and user activity.
2. Normalize into seller, buyer, inquiry, message, subscription, and contactbook facts.
3. Build daily feature snapshots with rolling windows and trend deltas.
4. Score daily churn probability and 90-day renewal risk.
5. Generate reason codes and AI summaries.
6. Route alerts to dashboards/CRM.
7. Track interventions and outcomes.
8. Retrain monthly or when drift exceeds threshold.

### Failure Handling

| Failure | Handling |
| --- | --- |
| Late event arrival | Recompute features for affected entity/date partitions. |
| Missing subscription data | Fall back to behavioral churn score and mark confidence lower. |
| Model service unavailable | Use rule engine cached in Redis. |
| LLM unavailable | Show deterministic reason-code explanation. |
| Data drift | Alert ML owner and trigger retraining candidate. |

## 10. APIs

API details are in `docs/api_design.md`. Core endpoints:

| Endpoint | Purpose |
| --- | --- |
| `POST /v1/churn/predict` | Score one or many entities. |
| `GET /v1/sellers/{seller_id}/health` | Seller health and reasons. |
| `GET /v1/buyers/{buyer_id}/health` | Buyer health and trends. |
| `GET /v1/alerts` | Paginated alert queue. |
| `POST /v1/recommendations/next-best-action` | Intervention recommendation. |
| `POST /v1/ai/retention-summary` | AI-generated reasons to stay. |

## 11. Database

Database details are in `docs/database_design.md`. Core tables:

| Table | Purpose |
| --- | --- |
| `seller_health_daily` | Daily seller feature and health snapshot. |
| `buyer_health_daily` | Daily buyer feature and health snapshot. |
| `engagement_features` | Shared rolling-window metrics. |
| `subscription_risk` | 90-day renewal monitoring. |
| `churn_scores` | Model outputs and explanations. |
| `alert_events` | Routed alerts and state. |
| `retention_actions` | Recommended and completed interventions. |
| `intervention_history` | Outcome attribution. |

## 12. Dashboards

Dashboard details are in `docs/dashboard_design.md`.

| Dashboard | Audience | Main Questions |
| --- | --- | --- |
| Executive | Leadership | How much revenue is at risk and saved? |
| Sales manager | Sales leads | Which accounts need action this week? |
| Seller health | Account owners | Why is this seller at risk and what should I say? |
| Cohort analysis | Product/analytics | Which cohorts are declining and why? |

## 13. Evaluation Metrics

### ML Metrics

| Metric | Target |
| --- | --- |
| Recall at top 10% risk | Capture majority of preventable churn. |
| Precision at action capacity | Match sales bandwidth. |
| PR AUC | Prefer for imbalanced churn labels. |
| Calibration error | Make risk probabilities trustworthy. |
| Feature drift | Detect broken data or behavior shifts. |

### Business Metrics

| Metric | Formula |
| --- | --- |
| Retention lift | treatment renewal rate - control renewal rate |
| Revenue saved | retained package value attributable to intervention |
| Sales productivity | retained revenue / sales call hour |
| Intervention conversion | retained accounts / accounts actioned |
| Discount efficiency | retained revenue / discount cost |

### A/B Test

| Element | Design |
| --- | --- |
| Population | Premium sellers with renewal in next 90 days. |
| Randomization | By account owner and risk band to avoid capacity bias. |
| Treatment | Model-prioritized alert plus AI talk track. |
| Control | Existing renewal process. |
| Success | Renewal lift, revenue saved, lower discount dependency. |

## 14. Demo Plan

Detailed demo flow is in `docs/demo_plan.md`.

Five-minute story:

1. Show executive revenue-at-risk and renewal watchlist.
2. Drill into one high-risk premium seller.
3. Explain score with concrete declining signals.
4. Generate reasons to stay and sales call script.
5. Mark intervention and show projected revenue saved.
6. Show synthetic data and system architecture credibility.

## 15. Skill Folder

The reusable skill is in `skills/churn-intelligence/`. It includes:

| File | Purpose |
| --- | --- |
| `SKILL.md` | Activation, workflows, environment variables, examples, edge cases, evaluation logic. |
| `scripts/score_account.py` | Deterministic account-level risk scoring helper. |
| `references/schemas.md` | Domain schema and feature reference. |
| `references/playbooks.md` | Retention playbooks and intervention mapping. |
| `references/output_schemas.json` | Structured output contracts. |
| `assets/dashboard_wireframe.md` | Demo dashboard layout reference. |

## 16. Implementation Roadmap

### First 4 Hours

| Time | Output |
| --- | --- |
| 0-1 hr | Normalize problem framing, churn definitions, and data schema. |
| 1-2 hr | Generate synthetic data and first feature snapshots. |
| 2-3 hr | Implement rule score, reason codes, and alert queue. |
| 3-4 hr | Build demo dashboard mock and one AI retention summary path. |

### MVP

| Phase | Scope |
| --- | --- |
| Data | Generate sellers, buyers, inquiries, messages, subscriptions, contactbook. |
| Scoring | Rule engine plus trainable tabular baseline. |
| Alerts | 90-day renewal watchlist and risk bands. |
| Agent | Grounded retention summary and next-best-action output. |
| Dashboard | Executive view and seller drilldown. |

### Polish Last

| Polish Item | Why |
| --- | --- |
| Cohort charts | Helps judges see analytics maturity. |
| Before/after intervention story | Makes impact tangible. |
| Failure-mode slide | Signals production thinking. |
| Skill folder validation | Captures 20% rubric weight. |

## 17. Business Impact

| Lever | Impact |
| --- | --- |
| Early renewal detection | Gives sales teams up to 90 days to reverse decline. |
| Explainability | Reduces blind calling and improves trust. |
| Personalized reasons to stay | Converts platform usage history into renewal evidence. |
| Intervention tracking | Learns which actions work for which risk patterns. |
| Synthetic data ecosystem | Enables credible demo without exposing production data. |

## 18. Future Scope

| Feature | Value |
| --- | --- |
| Conversational churn copilot | Ask natural-language questions across risk, reasons, cohorts, and playbooks. |
| Relationship risk graph | Detect ecosystem-level churn from buyer-seller network decay. |
| Renewal simulation | Estimate retention probability under discount, training, or catalog optimization. |
| Auto campaigns | Generate WhatsApp/email nudges based on reason codes. |
| Seller benchmarking | Show a seller how peers in the same city/category perform. |
| Causal uplift modeling | Prioritize accounts most likely to respond to action, not just most likely to churn. |

