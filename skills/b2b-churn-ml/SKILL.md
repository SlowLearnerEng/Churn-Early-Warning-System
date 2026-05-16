---
name: b2b-churn-ml
description: Train, evaluate, and compare machine learning models for B2B marketplace seller churn prediction. Use when an agent needs to build a baseline churn classifier, run cross-validation, generate feature importance rankings, compare scikit-learn pipelines, tune precision-recall tradeoffs, or produce calibrated churn probability scores for a seller base.
compatibility: Requires Python 3.8+ with scikit-learn, pandas, numpy, and joblib installed.
metadata:
  author: IndiaMART
  version: "1.0"
  domain: churn-prediction
---

# B2B Churn ML

Train and evaluate scikit-learn pipelines that predict seller churn probability from behavioral features.

## Prerequisites

Ensure features are ready before training:

```bash
python scripts/export_excel_to_csv.py  # if using real data
python scripts/build_features.py       # produces outputs/real/seller_features.csv
```

## Training

```bash
# Train on real IndiaMART data
python scripts/train_model_real.py

# Train on synthetic data (for experimentation)
python scripts/train_baseline_model.py
```

## Model Architecture

Two-stage sklearn `Pipeline` per model:

1. **Preprocessor** — `ColumnTransformer`:
   - `StandardScaler` on numeric features (activity counts, rates, scores, trend deltas)
   - `OneHotEncoder` on categoricals: `package`, `business_type`, `city`

2. **Classifier** — pluggable estimator. Defaults and alternatives:

| Estimator | When to use |
| --- | --- |
| `RandomForestClassifier` | Default; robust, handles missing values, good feature importance |
| `GradientBoostingClassifier` | Better calibration; slower to train |
| `LogisticRegression` | Baseline reference; interpretable coefficients |

## Key Hyperparameters

| Parameter | Default | Notes |
| --- | --- | --- |
| `n_estimators` | 100 | Increase to 300 for production |
| `max_depth` | 6 | Prevents overfitting on small datasets (<2000 sellers) |
| `class_weight` | `balanced` | Required — churn label can be imbalanced |
| `test_size` | 0.2 | Stratified on `churned` label |
| `random_state` | 42 | Fix for reproducibility |

## Evaluation Metrics

Report all four for every model run:

| Metric | Why it matters |
| --- | --- |
| **ROC-AUC** | Overall discrimination; use as primary ranking metric |
| **PR-AUC** | Accounts for class imbalance better than ROC-AUC |
| **Precision at top decile** | Business-critical: are the top 10% flagged sellers actually churning? |
| **Recall at action capacity** | Given finite outreach capacity, are we catching enough true churners? |

Also check **calibration error (ECE)** — use `sklearn.calibration.calibration_curve`. Poorly calibrated probabilities mislead retention teams on confidence.

## Feature Importance

After training, rank features by importance:

```python
# Random Forest / Gradient Boosting
importances = model.named_steps['clf'].feature_importances_
feature_names = model.named_steps['pre'].get_feature_names_out()

# Logistic Regression
importances = abs(model.named_steps['clf'].coef_[0])
```

Cross-reference the top ML features with the rule-engine reason codes. If a feature ranks high in ML but rarely fires in the rule engine, the rule threshold may be miscalibrated.

## Output Files

| File | Contents |
| --- | --- |
| `outputs/real/model_rf.joblib` | Saved Random Forest pipeline |
| `outputs/real/model_gb.joblib` | Saved Gradient Boosting pipeline |
| `outputs/real/model_comparison.csv` | Side-by-side metric comparison across models |

## Deployment Rules

- Use ML churn probability as a **soft signal only** alongside rule-engine reason codes.
- Never surface raw probability to sales teams — map to low/medium/high/critical bands.
- Retrain monthly or whenever the seller base grows by > 20%.
- If PR-AUC drops below 0.60 on a fresh hold-out, recheck for data leakage (especially `days_to_renewal` and `deactivation_tickets`).

## Common Issues

| Issue | Fix |
| --- | --- |
| AUC = 0.50 (random) | Check `churned` label distribution; may be all-zero after join |
| High train AUC, low test AUC | Overfitting — reduce `max_depth`, increase `min_samples_leaf` |
| Feature importance dominated by one feature | Check for data leakage from that feature |
| `class_weight` has no effect | Confirm `churned` column is int (0/1), not string |
