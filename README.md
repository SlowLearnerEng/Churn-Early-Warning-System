# Churn Intelligence Platform

Hackathon-ready AI system design and implementation package for an IndiaMART-like B2B churn early-warning platform.

## What Is Included

| Area | Artifact |
| --- | --- |
| End-to-end submission | `docs/hackathon_submission.md` |
| Source workbook notes | `docs/source_workbook_notes.md` |
| Synthetic dataset design | `docs/dataset_design.md` |
| Data dictionary | `docs/data_dictionary.md` |
| Feature engineering | `docs/feature_engineering.md` |
| Database and warehouse model | `docs/database_design.md` |
| API contracts | `docs/api_design.md` |
| Dashboard/UX plan | `docs/dashboard_design.md` |
| Demo script and fallback plan | `docs/demo_plan.md` |
| Data generator | `scripts/generate_synthetic_data.py` |
| Rule-based risk engine | `scripts/churn_scoring.py` |
| Baseline ML trainer | `scripts/train_baseline_model.py` |
| Reusable AI skill | `skills/churn-intelligence/` |

## Quick Start

Install dependencies on a machine with Python 3.10+:

```bash
pip install -r requirements.txt
```

Generate a small demo dataset:

```bash
python scripts/generate_synthetic_data.py --scale demo --output-dir data/demo --formats csv sql --seed 42
```

Generate a larger hackathon dataset:

```bash
python scripts/generate_synthetic_data.py --scale hackathon --output-dir data/hackathon --formats csv parquet sql --seed 42
```

Score accounts with the explainable rule engine:

```bash
python scripts/churn_scoring.py --input-dir data/demo --output-dir outputs/demo_scores
```

Train a baseline model:

```bash
python scripts/train_baseline_model.py --input-dir data/demo --output-dir outputs/model
```

## Workbook Context Used

The supplied `seller-buyer-churn.xlsx` was inspected as representative schema context. It contains contactbook, customer-to-service/subscription, message-center, transaction-code, and subscription-date sheets. The generated platform normalizes those patterns into clean entities for sellers, buyers, inquiries, messages, subscriptions, contactbook relationships, features, alerts, scores, and interventions.

## Hackathon Positioning

This package is intentionally not "just a model." It frames churn as a measurable retention operating system:

- Predict risk for sellers, buyers, and premium subscribers.
- Detect 90-day renewal warning signals.
- Explain the reasons behind each score.
- Recommend next-best sales and product interventions.
- Generate personalized reasons to stay.
- Track revenue saved, retention lift, and intervention success.
