#!/usr/bin/env python3
"""
Train a baseline churn model from generated seller and feature data.

Uses scikit-learn when available. The script intentionally keeps features
simple and explainable for hackathon demos.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a baseline seller churn model.")
    parser.add_argument("--input-dir", default="data/demo")
    parser.add_argument("--output-dir", default="outputs/model")
    args = parser.parse_args()

    try:
        import joblib  # type: ignore
        import pandas as pd  # type: ignore
        from sklearn.compose import ColumnTransformer  # type: ignore
        from sklearn.ensemble import RandomForestClassifier  # type: ignore
        from sklearn.impute import SimpleImputer  # type: ignore
        from sklearn.metrics import average_precision_score, classification_report, roc_auc_score  # type: ignore
        from sklearn.model_selection import train_test_split  # type: ignore
        from sklearn.pipeline import Pipeline  # type: ignore
        from sklearn.preprocessing import OneHotEncoder  # type: ignore
    except Exception as exc:
        raise SystemExit(f"Missing training dependency: {exc}. Install with pip install -r requirements.txt")

    input_dir = Path(args.input_dir)
    csv_dir = input_dir / "csv" if (input_dir / "csv").exists() else input_dir
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    sellers = pd.read_csv(csv_dir / "sellers.csv")
    health = pd.read_csv(csv_dir / "seller_health_daily.csv")
    latest_health = health.sort_values("as_of_date").groupby("seller_id").tail(1)
    df = sellers.merge(latest_health, on="seller_id", how="left")

    target = "churn_label"
    numeric_features = [
        "response_rate",
        "avg_response_minutes",
        "product_count",
        "catalog_quality_score",
        "lead_utilization_score_x",
        "trust_score",
        "active_days_30d",
        "inquiries_received_30d",
        "handled_leads_30d",
        "response_rate_30d",
        "avg_response_minutes_30d",
        "conversion_rate_90d",
        "catalog_staleness_days",
        "buyer_repeat_count_90d",
        "sentiment_avg_30d",
        "graph_degree_90d",
    ]
    categorical_features = ["business_category", "city", "state", "subscription_tier", "archetype", "gst_verified"]
    numeric_features = [c for c in numeric_features if c in df.columns]
    categorical_features = [c for c in categorical_features if c in df.columns]

    X = df[numeric_features + categorical_features]
    y = df[target]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median"))]), numeric_features),
            ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical_features),
        ]
    )
    model = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=180,
                    max_depth=10,
                    min_samples_leaf=8,
                    class_weight="balanced_subsample",
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    model.fit(X_train, y_train)
    probabilities = model.predict_proba(X_test)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)

    metrics = {
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "pr_auc": float(average_precision_score(y_test, probabilities)),
        "classification_report": classification_report(y_test, predictions, output_dict=True),
        "features": {"numeric": numeric_features, "categorical": categorical_features},
    }
    joblib.dump(model, output_dir / "seller_churn_random_forest.joblib")
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps({"output_dir": str(output_dir), "roc_auc": metrics["roc_auc"], "pr_auc": metrics["pr_auc"]}, indent=2))


if __name__ == "__main__":
    main()
