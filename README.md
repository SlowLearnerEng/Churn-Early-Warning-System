# Churn Intelligence Platform

An end-to-end B2B marketplace churn early-warning system built for IndiaMART. Scores 500 real sellers for churn risk, explains every score with deterministic reason codes, and surfaces actionable retention interventions through a live analytics dashboard.

---

## Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Data Pipeline](#data-pipeline)
- [Running the Dashboard](#running-the-dashboard)
- [Project Structure](#project-structure)
- [Scripts Reference](#scripts-reference)
- [Agent Skills](#agent-skills)
- [Dashboard Pages](#dashboard-pages)
- [Output Files](#output-files)
- [Documentation](#documentation)

---

## Architecture

```
indiamart_churn_dataset_v2.xlsx
        │
        ▼
export_excel_to_csv.py ──► data/csv/dataset - *.csv   (11 sheets)
        │
        ▼
build_features.py ──────► outputs/real/seller_features.csv   (500 sellers × 111 features)
        │
        ▼
score_real_data.py ─────► outputs/real/churn_scores.csv
                          outputs/real/alert_events.csv
                          outputs/real/retention_actions.csv
        │
        ▼
export_real_dashboard.py ► dashboard/data/dashboard_data.json   (3.4 MB)
        │
        ▼
python -m http.server ──► http://localhost:8765
```

---

## Prerequisites

- Python 3.8 or higher
- `indiamart_churn_dataset_v2.xlsx` in the project root (required for the real data pipeline)
- Modern browser for the dashboard

---

## Installation

```bash
# Clone or download the repository, then install dependencies
pip install -r requirements.txt
```

`requirements.txt` installs: `pandas`, `numpy`, `scikit-learn`, `joblib`, `openpyxl`, `faker`, `pyarrow`, `openai`, `python-dotenv`.

---

## Data Pipeline

Run these four commands in order from the project root. Each step depends on the previous one.

### Step 1 — Export Excel to CSVs

```bash
python scripts/export_excel_to_csv.py
```

Reads `indiamart_churn_dataset_v2.xlsx` and writes all 11 sheets to `data/csv/`:

| Sheet | CSV file |
| --- | --- |
| seller_profile | `data/csv/dataset - seller_profile.csv` |
| seller_activity | `data/csv/dataset - seller_activity.csv` |
| seller_catalogue | `data/csv/dataset - seller_catalogue.csv` |
| seller_tickets | `data/csv/dataset - seller_tickets.csv` |
| seller_transactions | `data/csv/dataset - seller_transactions.csv` |
| seller_ratings | `data/csv/dataset - seller_ratings.csv` |
| buyer_seller_calls | `data/csv/dataset - buyer_seller_calls.csv` |
| seller_monthly_weekly_trends | `data/csv/dataset - seller_monthly_weekly_trends.csv` |
| seller_low_rating_reviews | `data/csv/dataset - seller_low_rating_reviews.csv` |
| seller_contact_book | `data/csv/dataset - seller_contact_book.csv` |
| seller_buyer_chat | `data/csv/dataset - seller_buyer_chat.csv` |

### Step 2 — Build Features

```bash
python scripts/build_features.py
```

Engineers ~111 behavioral features per seller from the CSVs. Output: `outputs/real/seller_features.csv`.

Key features computed: rolling-window activity (7/30/90 days), negative call intent %, call pickup rate, cancellation rate, buylead trend, subscription days-to-renewal, untouched contact %, low-rating review response rate, open and conflict ticket counts, and a binary `churned` label.

### Step 3 — Score Sellers

```bash
python scripts/score_real_data.py
```

Applies a calibrated rule engine to produce churn risk scores. Writes three files to `outputs/real/`:

| File | Contents |
| --- | --- |
| `churn_scores.csv` | Risk score (0–100), band, confidence, reason codes, recommended action per seller |
| `alert_events.csv` | Alerts for medium/high/critical sellers with priority scores |
| `retention_actions.csv` | Recommended interventions with owner assignment |

Typical distribution: ~60% low · ~37% medium · ~3% high · 0% critical.

### Step 4 — Export Dashboard Data

```bash
python scripts/export_real_dashboard.py
```

Merges all CSVs and scored outputs into `dashboard/data/dashboard_data.json`. Includes drill-down data (calls, reviews, tickets, catalogue, health trends) for each seller. Output is ~3.4 MB.

---

## Running the Dashboard

After completing all four pipeline steps:

```bash
cd dashboard
python -m http.server 8765
```

Open **http://localhost:8765** in your browser.

> The dashboard must be served over HTTP — it uses `fetch()` to load data and will not work if opened directly as a `file://` URL.

---

## Optional Steps

### Train an ML Model

Train a scikit-learn churn classifier on the real feature set:

```bash
python scripts/train_model_real.py
```

Outputs saved models to `outputs/real/model_rf.joblib` and `outputs/real/model_gb.joblib`. Prints ROC-AUC, PR-AUC, and precision-at-top-decile for each model.

### Generate AI Retention Summaries

Requires an OpenAI-compatible API key set in `.env`:

```bash
# .env
OPENAI_API_KEY=your-key-here
```

```bash
python scripts/ai_agent.py
```

Writes `outputs/real/ai_summaries.json`. The dashboard will automatically embed AI narratives in each Seller 360 profile when this file exists.

---

## Project Structure

```
Churn-Early-Warning-System/
├── indiamart_churn_dataset_v2.xlsx   # Source dataset (11 sheets, 500 sellers)
├── requirements.txt
├── README.md
│
├── data/
│   └── csv/                          # Generated by export_excel_to_csv.py
│
├── outputs/
│   └── real/                         # Generated by build_features.py + score_real_data.py
│       ├── seller_features.csv
│       ├── churn_scores.csv
│       ├── alert_events.csv
│       └── retention_actions.csv
│
├── dashboard/
│   ├── index.html                    # Tab panels, Chart.js 4.4.7 CDN
│   ├── app.js                        # Data load, navigation, KPI cards, watchlist
│   ├── views.js                      # Seller 360, cohorts, interventions, upsell, activation
│   ├── styles.css                    # Dark theme, CSS custom properties
│   └── data/
│       └── dashboard_data.json       # Generated by export_real_dashboard.py
│
├── scripts/
│   ├── export_excel_to_csv.py        # Step 1: Excel → CSVs
│   ├── build_features.py             # Step 2: CSVs → seller_features.csv
│   ├── score_real_data.py            # Step 3: Features → churn scores + alerts
│   ├── export_real_dashboard.py      # Step 4: All outputs → dashboard_data.json
│   ├── train_model_real.py           # Optional: train ML churn classifier
│   ├── ai_agent.py                   # Optional: generate AI retention summaries
│   ├── churn_scoring.py              # Core scoring engine (used by score_real_data.py)
│   └── train_baseline_model.py       # Baseline model on synthetic data
│
├── skills/                           # Agent Skills (agentskills.io format)
│   ├── churn-intelligence/           # Score, explain, and operate churn workflows
│   ├── marketplace-feature-engineering/  # ETL: raw CSVs → behavioral features
│   ├── retention-playbook/           # Map risk signals → interventions and talk tracks
│   ├── b2b-churn-ml/                 # Train and evaluate churn ML models
│   └── churn-dashboard/              # Build and extend the JS analytics dashboard
│
├── docs/
│   ├── hackathon_submission.md
│   ├── feature_engineering.md
│   ├── data_dictionary.md
│   ├── database_design.md
│   ├── api_design.md
│   ├── dashboard_design.md
│   ├── dataset_design.md
│   ├── demo_plan.md
│   └── source_workbook_notes.md
│
└── prompts/
    ├── retention_summary.txt
    ├── call_insights.txt
    └── review_analyzer.txt
```

---

## Scripts Reference

| Script | Purpose | Input | Output |
| --- | --- | --- | --- |
| `export_excel_to_csv.py` | Export all Excel sheets to CSV | `indiamart_churn_dataset_v2.xlsx` | `data/csv/dataset - *.csv` |
| `build_features.py` | Engineer behavioral features | `data/csv/` | `outputs/real/seller_features.csv` |
| `score_real_data.py` | Rule-based churn scoring | `seller_features.csv` | `churn_scores.csv`, `alert_events.csv`, `retention_actions.csv` |
| `export_real_dashboard.py` | Merge all outputs to JSON | `data/csv/` + `outputs/real/` | `dashboard/data/dashboard_data.json` |
| `train_model_real.py` | Train churn ML classifier | `seller_features.csv` | `model_rf.joblib`, `model_gb.joblib` |
| `ai_agent.py` | Generate AI retention summaries | Scored sellers + API key | `outputs/real/ai_summaries.json` |
| `churn_scoring.py` | Core scoring library | JSON payload | Structured score dict |
| `train_baseline_model.py` | Baseline model (synthetic data) | Any features CSV | Saved model |

---

## Agent Skills

Five [Agent Skills](https://agentskills.io/) are bundled in `skills/`. Any compatible agent (Claude Code, Gemini CLI, VS Code Copilot, etc.) loads them automatically.

| Skill | Directory | When it activates |
| --- | --- | --- |
| **churn-intelligence** | `skills/churn-intelligence/` | Churn scoring, reason codes, AI retention summaries, renewal risk |
| **marketplace-feature-engineering** | `skills/marketplace-feature-engineering/` | ETL pipeline, rolling-window features, churn label definition |
| **retention-playbook** | `skills/retention-playbook/` | Action code mapping, talk tracks, escalation rules, ROI framework |
| **b2b-churn-ml** | `skills/b2b-churn-ml/` | Training classifiers, evaluation metrics, feature importance |
| **churn-dashboard** | `skills/churn-dashboard/` | Adding tabs, fixing charts, modifying the data export |

Each skill follows the [agentskills.io specification](https://agentskills.io/specification): a `SKILL.md` file with `name`, `description`, `compatibility`, and `metadata` frontmatter, plus step-by-step instructions and examples in the body.

---

## Dashboard Pages

| Page | What it shows |
| --- | --- |
| **Executive** | Revenue at risk, risk distribution donut, renewal funnel, top risk drivers |
| **Sales Watchlist** | All medium/high/critical sellers, sortable by priority score, filterable by band/package/city |
| **Seller 360** | Full profile: health trends, call log, reviews, tickets, catalogue, alert tab with AI narrative |
| **Renewal Risk** | 90-day renewal queue, urgency timeline, risk vs. days-to-renewal bubble chart |
| **Cohorts** | Risk by package, state, business type, and turnover tier |
| **Interventions** | Action queue, playbook performance, ROI tracker by intervention type |
| **Upsell Signals** | Low-risk sellers with rising engagement flagged for package upgrade |
| **Activation** | New sellers (< 1 year) scored for onboarding health |

---

## Output Files

| File | Rows | Key columns |
| --- | --- | --- |
| `outputs/real/seller_features.csv` | 500 | `seller_id`, `churned`, ~111 behavioral features |
| `outputs/real/churn_scores.csv` | 500 | `risk_score`, `risk_band`, `confidence`, `reason_codes`, `recommended_action`, `revenue_at_risk` |
| `outputs/real/alert_events.csv` | ~199 | `severity`, `title`, `priority_score`, `owner_id` |
| `outputs/real/retention_actions.csv` | ~199 | `action_code`, `owner_id`, `status` |
| `dashboard/data/dashboard_data.json` | — | Full seller objects with drill-down data, executive summary, cohorts |

---

## Documentation

| Document | Contents |
| --- | --- |
| `docs/hackathon_submission.md` | Full end-to-end submission narrative |
| `docs/feature_engineering.md` | Feature definitions and engineering decisions |
| `docs/data_dictionary.md` | Field-level data dictionary for all entities |
| `docs/database_design.md` | Warehouse schema and entity relationships |
| `docs/api_design.md` | REST API contracts for scoring and alerts |
| `docs/dashboard_design.md` | UX design and component specifications |
| `docs/demo_plan.md` | Demo script and fallback plan |
| `docs/source_workbook_notes.md` | Notes on the source Excel workbook |
