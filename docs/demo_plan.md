# Hackathon Demo Plan

## Five-Minute Demo Script

### 0:00-0:40: Set The Problem

"In a B2B marketplace, churn rarely starts on renewal day. It starts weeks earlier: response times slip, leads go unused, buyer relationships weaken, and premium features stop being used. Our system finds those patterns 90 days before renewal and turns them into specific retention actions."

Show:

| Visual | Point |
| --- | --- |
| Executive revenue-at-risk card | Business impact. |
| Renewal watchlist | Operational actionability. |

### 0:40-1:30: Show The Watchlist

Filter to premium sellers with renewal in 90 days. Sort by priority.

Talk track:

"This queue is not simply highest risk. It blends risk, package value, recoverability, renewal urgency, and category importance so sales teams use time where it can change the outcome."

### 1:30-2:40: Drill Into Seller 360

Open a high-risk seller.

Show:

| Card | Talking Point |
| --- | --- |
| Risk score | High risk with confidence. |
| Response decline | Clear behavioral signal. |
| Lead utilization | Recoverable operating issue. |
| Days to renewal | Why action is urgent. |
| Historical wins | Why retention is plausible. |

### 2:40-3:35: AI Retention Agent

Generate summary.

Talk track:

"The agent is grounded in retrieved account evidence. It does not just say 'customer may churn.' It tells the account manager what changed, why the seller should stay, and what to do next."

Show:

| Output | Example |
| --- | --- |
| Reason to stay | Qualified leads, repeat buyers, category demand. |
| Sales opener | Short personalized call opening. |
| Action | Sales call plus catalog/response workflow fix. |

### 3:35-4:20: Architecture And Robustness

Show architecture slide or doc.

Mention:

| Capability | Why Judges Care |
| --- | --- |
| Rule fallback | Robust if ML/LLM service fails. |
| Feature store | Repeatable scoring and training. |
| Alert suppression | Avoids sales spam. |
| Monitoring | Production readiness. |
| A/B test | Measures real retention lift. |

### 4:20-5:00: Impact Close

"For 10,000 premium sellers at INR 45,000 average package value, even an 8 point lift on 20% of high-risk accounts saves about INR 72 lakh annually in this conservative simulation. The platform also reduces wasted calls by showing exactly which accounts need action and why."

## Ten-Minute Expanded Demo

| Minute | Focus |
| --- | --- |
| 0-1 | Problem and revenue leakage. |
| 1-2 | Synthetic data ecosystem and workbook-inspired schema. |
| 2-3 | Feature engineering and risk scoring. |
| 3-5 | Dashboard watchlist and seller drilldown. |
| 5-6 | AI retention agent output. |
| 6-7 | Intervention tracking and A/B test design. |
| 7-8 | System architecture and failure handling. |
| 8-9 | Skill folder and reusable workflows. |
| 9-10 | Business impact and future scope. |

## Judge-Focused Narrative

| Rubric Area | Demo Proof |
| --- | --- |
| Impact | Revenue at risk, revenue saved, sales productivity. |
| Pinch metrics | Renewal lift, alert precision, top-risk recall, action success. |
| Completeness | Data, features, model, agent, APIs, dashboards, DB, demo. |
| Robustness | Fallback rule engine, monitoring, data quality, drift checks. |
| Skill quality | Canonical skill folder with scripts, references, schemas, and playbooks. |

## Live Demo Ideas

| Demo | Implementation |
| --- | --- |
| Generate data live | Run `generate_synthetic_data.py --scale demo`. |
| Score accounts live | Run `churn_scoring.py` and open output CSV. |
| Show top risk accounts | Sort `churn_scores.csv` by `risk_score`. |
| Generate summary | Use skill workflow/prompt with one high-risk record. |
| Show architecture | Open `docs/hackathon_submission.md` system section. |

## Fallback Demo Plan

| Risk | Fallback |
| --- | --- |
| Python unavailable | Use pre-generated screenshots/CSV exports and docs. |
| Dashboard fails | Show watchlist CSV and Seller 360 mock in `assets/dashboard_wireframe.md`. |
| AI call unavailable | Use deterministic reason-code summary from scoring script. |
| Data generation too slow | Use `--scale demo` or `--sellers 1000 --buyers 5000 --inquiries 50000`. |
| Parquet dependency missing | Generate CSV and SQL only. |

## Final Slide

One sentence:

"We turn churn from a renewal-day surprise into a 90-day, explainable, measurable retention workflow."

