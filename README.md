# Churn Intelligence Platform

An end-to-end, explainable **B2B marketplace churn early-warning system** built for IndiaMART-like seller ecosystems. Processes real operational data (500+ sellers, 57K+ rows across 11 datasets), scores every seller for churn risk with deterministic reason codes, generates **AI-powered retention summaries** with personalized sales exec pitches, and surfaces everything through a premium dark-mode analytics dashboard.

---

## Key Capabilities

| Capability | Details |
|---|---|
| **Feature Engineering** | 111 behavioral features from 11 data sources — activity decay, call intent, CRM health, reputation signals |
| **Rule-Based Scoring** | Calibrated 10-signal scoring engine producing risk scores (0–100), bands, confidence, and evidence-backed reason codes |
| **ML Model** | GradientBoosting classifier — **0.97 ROC-AUC**, **0.98 PR-AUC** — validates the rule engine |
| **AI Retention Agent** | LLM-powered agent that generates structured retention summaries: risk explanation, reasons to stay, next best action, and **sales exec opening line** |
| **8-Page Dashboard** | Executive overview, watchlist, seller 360° deep-dive, renewal risk, cohort analysis, interventions, upsell signals, activation health |

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
        ├──► train_model_real.py ──► outputs/real/model_gb.joblib   (optional ML validation)
        │
        ▼
score_real_data.py ─────► outputs/real/churn_scores.csv
                          outputs/real/alert_events.csv
                          outputs/real/retention_actions.csv
        │
        ├──► ai_agent.py ──────────► outputs/real/ai_summaries.json   (optional, needs API key)
        │
        ▼
export_real_dashboard.py ► dashboard/data/dashboard_data.json   (~3.4 MB)
        │
        ▼
python -m http.server ──► http://localhost:8080
```

---

## Prerequisites

- **Python 3.8+**
- `indiamart_churn_dataset_v2.xlsx` in the project root (source dataset with 11 sheets, 500 sellers)
- Modern browser (Chrome, Edge, Firefox) for the dashboard
- *Optional:* OpenAI-compatible API key for AI retention summaries

---

## Installation

```bash
git clone https://github.com/SlowLearnerEng/Churn-Early-Warning-System.git
cd Churn-Early-Warning-System
pip install -r requirements.txt
```

Dependencies: `pandas`, `numpy`, `scikit-learn`, `joblib`, `pyarrow`, `faker`, `openai`, `python-dotenv`.

---

## Quick Start

Run these commands in order from the project root:

```bash
# 1. Export Excel sheets to CSVs
python scripts/export_excel_to_csv.py

# 2. Engineer behavioral features (500 sellers × 111 features)
python scripts/build_features.py

# 3. Score all sellers for churn risk
python scripts/score_real_data.py

# 4. Export dashboard JSON
python scripts/export_real_dashboard.py

# 5. Launch the dashboard
python -m http.server 8080 --directory dashboard
```

Open **http://localhost:8080** in your browser.

> **Note:** The dashboard uses `fetch()` to load data and must be served over HTTP — it won't work when opened as a `file://` URL.

---

## Data Pipeline

### Step 1 — Export Excel to CSVs

```bash
python scripts/export_excel_to_csv.py
```

Reads `indiamart_churn_dataset_v2.xlsx` and writes all 11 sheets to `data/csv/`:

| Sheet | CSV File |
|---|---|
| seller_profile | `dataset - seller_profile.csv` |
| seller_activity | `dataset - seller_activity.csv` |
| seller_catalogue | `dataset - seller_catalogue.csv` |
| seller_tickets | `dataset - seller_tickets.csv` |
| seller_transactions | `dataset - seller_transactions.csv` |
| seller_ratings | `dataset - seller_ratings.csv` |
| buyer_seller_calls | `dataset - buyer_seller_calls.csv` |
| seller_monthly_weekly_trends | `dataset - seller_monthly_weekly_trends.csv` |
| seller_low_rating_reviews | `dataset - seller_low_rating_reviews.csv` |
| seller_contact_book | `dataset - seller_contact_book.csv` |
| seller_buyer_chat | `dataset - seller_buyer_chat.csv` |

### Step 2 — Build Features

```bash
python scripts/build_features.py
```

Engineers ~111 behavioral features per seller from the CSVs. Output: `outputs/real/seller_features.csv`.

**Key features:** rolling-window activity (7/30/90 days), negative call intent %, call pickup rate, cancellation rate, buylead trend slope, subscription days-to-renewal, untouched contact %, low-rating review response rate, open/conflict ticket counts, and a deterministic binary `churned` label derived from call intent and transaction signals.

### Step 3 — Score Sellers

```bash
python scripts/score_real_data.py
```

Applies a calibrated 10-signal rule engine to produce churn risk scores. Outputs:

| File | Contents |
|---|---|
| `churn_scores.csv` | Risk score (0–100), band, confidence, reason codes, recommended action per seller |
| `alert_events.csv` | Alerts for medium/high/critical sellers with priority scores |
| `retention_actions.csv` | Recommended interventions with owner assignment and status |

**Typical distribution:** ~338 low · ~147 medium · ~15 high risk.

### Step 4 — Export Dashboard Data

```bash
python scripts/export_real_dashboard.py
```

Merges all CSVs, scores, and AI summaries into `dashboard/data/dashboard_data.json` (~3.4 MB). Includes per-seller drill-down: calls, reviews, tickets, catalogue, health trends, and AI retention narratives.

---

## Optional Steps

### Train an ML Model

```bash
python scripts/train_model_real.py
```

Trains GradientBoosting and RandomForest classifiers on the real feature set. Results:
- **GradientBoosting:** ROC-AUC 0.97, PR-AUC 0.98
- **Top churn drivers:** `negative_intent_pct`, `cancellation_rate`, `deactivation_tickets`

Outputs: `outputs/real/model_gb.joblib`, `outputs/real/model_rf.joblib`.

### Generate AI Retention Summaries

Requires an OpenAI-compatible API key. Create a `.env` file in the project root:

```env
LLM_API_KEY=your-api-key-here
BASE_URL=https://your-llm-endpoint.com/v1
ANTHROPIC_MODEL=anthropic/claude-opus-4-6
```

Then run:

```bash
python scripts/ai_agent.py
```

The agent reads prompt templates from `prompts/`, gathers all evidence for each high-risk seller (profile, activity, calls, reviews, tickets, scores), and calls the LLM to generate structured JSON output:

```json
{
  "risk_explanation": "Why this seller is at risk, backed by data",
  "reasons_to_stay": ["Evidence-based reasons the seller should renew"],
  "next_best_action": "Specific recommended intervention",
  "sales_opening_line": "Ready-to-use pitch for the sales exec call"
}
```

Output: `outputs/real/ai_summaries.json`. The dashboard automatically embeds these in each Seller 360 profile.

#### Sales Exec Pitch

The **`sales_opening_line`** field is the sales exec pitch — a natural, personalized call opening line that the retention agent composes based on the seller's specific data. For example:

> *"I'm calling because your account generated 309 enquiries last month — buyers are actively searching for your products, and we want to help you capitalize on this momentum."*

This appears in the **Seller 360 → AI Retention Agent** panel at the bottom of each seller's detail page.

---

## Dashboard Pages

The dashboard has **8 interactive pages**, all powered by real data:

| Page | What it shows |
|---|---|
| **Executive Overview** | Revenue at risk (₹), risk distribution donut, renewal funnel, top 7 risk drivers bar chart, Package × State risk heatmap |
| **Sales Watchlist** | All medium/high/critical sellers in a sortable, filterable table — priority score, package, city, risk band, revenue at risk, reason codes, recommended action, status |
| **Seller 360** | Searchable seller picker (all 500 sellers) → full profile: header with risk ring, 8 explanation metric cards, buylead/enquiry trends, call pickup trends, call log with intent labels, low-rating reviews with response tracking, ticket table, catalogue, and AI retention agent panel |
| **Renewal Risk** | 90-day renewal queue, urgency timeline, risk vs. days-to-renewal bubble chart |
| **Cohorts** | Stacked bar charts with tab switching — risk by Package, State, Business Type, or Turnover tier, plus Revenue at Risk by cohort |
| **Interventions** | Action KPIs (total, scheduled, completed, recommended), action type donut, status donut, prioritized action queue table |
| **Upsell Signals** | Low-risk sellers with rising engagement flagged for package upgrade |
| **Activation** | New sellers (< 1 year) scored for onboarding health |

---

## Project Structure

```
Churn-Early-Warning-System/
├── indiamart_churn_dataset_v2.xlsx    # Source dataset (11 sheets, 500 sellers)
├── requirements.txt                   # Python dependencies
├── .env                               # LLM API credentials (not committed)
├── .gitignore
├── README.md
│
├── data/
│   └── csv/                           # Generated by export_excel_to_csv.py
│       ├── dataset - seller_profile.csv
│       ├── dataset - seller_activity.csv
│       ├── dataset - buyer_seller_calls.csv
│       └── ... (11 CSV files)
│
├── outputs/
│   └── real/                          # Generated by pipeline scripts
│       ├── seller_features.csv        # 500 × 111 feature matrix
│       ├── churn_scores.csv           # Risk scores + reason codes
│       ├── alert_events.csv           # Medium/high/critical alerts
│       ├── retention_actions.csv      # Intervention assignments
│       ├── ai_summaries.json          # AI retention narratives (optional)
│       ├── model_gb.joblib            # Trained GradientBoosting (optional)
│       └── model_rf.joblib            # Trained RandomForest (optional)
│
├── dashboard/
│   ├── index.html                     # 8 tab panels, Chart.js 4.4.7 CDN
│   ├── app.js                         # Data load, navigation, KPI cards, watchlist
│   ├── views.js                       # Seller 360, cohorts, interventions, renewal, upsell
│   ├── styles.css                     # Dark glassmorphism theme, CSS custom properties
│   └── data/
│       └── dashboard_data.json        # Generated by export_real_dashboard.py
│
├── scripts/
│   ├── export_excel_to_csv.py         # Step 1: Excel → CSVs
│   ├── build_features.py              # Step 2: CSVs → seller_features.csv (111 features)
│   ├── score_real_data.py             # Step 3: Features → churn scores + alerts + actions
│   ├── export_real_dashboard.py       # Step 4: All outputs → dashboard_data.json
│   ├── train_model_real.py            # Optional: Train ML churn classifier (0.97 AUC)
│   ├── ai_agent.py                    # Optional: Generate AI retention summaries
│   ├── churn_scoring.py               # Core scoring engine (used by score_real_data.py)
│   ├── export_dashboard_data.py       # Legacy dashboard exporter
│   ├── generate_synthetic_data.py     # Generate synthetic seller data for testing
│   └── train_baseline_model.py        # Baseline model on synthetic data
│
├── prompts/                           # AI agent prompt templates (modular, A/B testable)
│   ├── retention_summary.txt          # System prompt: risk explanation + sales pitch
│   ├── call_insights.txt              # Call log sentiment and engagement analysis
│   └── review_analyzer.txt            # Low-rating review complaint pattern analysis
│
├── skills/                            # Agent Skills (agentskills.io format)
│   ├── churn-intelligence/            # Score, explain, and operate churn workflows
│   ├── marketplace-feature-engineering/  # ETL: raw CSVs → behavioral features
│   ├── retention-playbook/            # Map risk signals → interventions and talk tracks
│   ├── b2b-churn-ml/                  # Train and evaluate churn ML models
│   └── churn-dashboard/               # Build and extend the JS analytics dashboard
│
└── docs/                              # Design documents and specifications
    ├── hackathon_submission.md         # Full end-to-end submission narrative
    ├── feature_engineering.md          # Feature definitions and engineering decisions
    ├── data_dictionary.md             # Field-level data dictionary for all entities
    ├── database_design.md             # Warehouse schema and entity relationships
    ├── api_design.md                  # REST API contracts for scoring and alerts
    ├── dashboard_design.md            # UX design and component specifications
    ├── dataset_design.md              # Dataset structure and generation logic
    ├── demo_plan.md                   # Demo script and fallback plan
    └── source_workbook_notes.md       # Notes on the source Excel workbook
```

---

## Scripts Reference

| Script | Purpose | Input | Output |
|---|---|---|---|
| `export_excel_to_csv.py` | Export all Excel sheets to CSV | `indiamart_churn_dataset_v2.xlsx` | `data/csv/dataset - *.csv` |
| `build_features.py` | Engineer 111 behavioral features | `data/csv/` | `outputs/real/seller_features.csv` |
| `score_real_data.py` | Rule-based churn scoring (10 signals) | `seller_features.csv` | `churn_scores.csv`, `alert_events.csv`, `retention_actions.csv` |
| `export_real_dashboard.py` | Merge all outputs to dashboard JSON | `data/csv/` + `outputs/real/` | `dashboard/data/dashboard_data.json` |
| `train_model_real.py` | Train ML churn classifier | `seller_features.csv` | `model_gb.joblib`, `model_rf.joblib` |
| `ai_agent.py` | Generate AI retention summaries | Scored sellers + `.env` API key | `outputs/real/ai_summaries.json` |
| `churn_scoring.py` | Core scoring engine library | JSON payload | Structured score dict |
| `generate_synthetic_data.py` | Generate synthetic test data | Config params | Synthetic CSVs |
| `train_baseline_model.py` | Baseline model (synthetic data) | Any features CSV | Saved model |

---

## Agent Skills

Five [Agent Skills](https://agentskills.io/) are bundled in `skills/`. Any compatible agent (Claude Code, Gemini CLI, VS Code Copilot, etc.) loads them automatically.

| Skill | Directory | When it activates |
|---|---|---|
| **churn-intelligence** | `skills/churn-intelligence/` | Churn scoring, reason codes, AI retention summaries, renewal risk |
| **marketplace-feature-engineering** | `skills/marketplace-feature-engineering/` | ETL pipeline, rolling-window features, churn label definition |
| **retention-playbook** | `skills/retention-playbook/` | Action code mapping, talk tracks, escalation rules, ROI framework |
| **b2b-churn-ml** | `skills/b2b-churn-ml/` | Training classifiers, evaluation metrics, feature importance |
| **churn-dashboard** | `skills/churn-dashboard/` | Adding tabs, fixing charts, modifying the data export |

---

## Output Files

| File | Rows | Key Columns |
|---|---|---|
| `seller_features.csv` | 500 | `seller_id`, `churned`, ~111 behavioral features |
| `churn_scores.csv` | 500 | `risk_score`, `risk_band`, `confidence`, `reason_codes`, `recommended_action`, `revenue_at_risk` |
| `alert_events.csv` | ~162 | `severity`, `title`, `priority_score`, `owner_id` |
| `retention_actions.csv` | ~162 | `action_code`, `owner_id`, `status` |
| `ai_summaries.json` | ~15 | `risk_explanation`, `reasons_to_stay`, `next_best_action`, `sales_opening_line` |
| `dashboard_data.json` | — | Full seller objects with drill-down data, executive summary, cohorts |

---

## Documentation

| Document | Contents |
|---|---|
| [hackathon_submission.md](docs/hackathon_submission.md) | Full end-to-end submission narrative |
| [feature_engineering.md](docs/feature_engineering.md) | Feature definitions and engineering decisions |
| [data_dictionary.md](docs/data_dictionary.md) | Field-level data dictionary for all entities |
| [database_design.md](docs/database_design.md) | Warehouse schema and entity relationships |
| [api_design.md](docs/api_design.md) | REST API contracts for scoring and alerts |
| [dashboard_design.md](docs/dashboard_design.md) | UX design and component specifications |
| [dataset_design.md](docs/dataset_design.md) | Dataset structure and generation logic |
| [demo_plan.md](docs/demo_plan.md) | Demo script and fallback plan |
| [source_workbook_notes.md](docs/source_workbook_notes.md) | Notes on the source Excel workbook |

---

## License

Private repository — internal use only.
