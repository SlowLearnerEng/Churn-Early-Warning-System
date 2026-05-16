#!/usr/bin/env python3
"""
Train a baseline churn model on real seller features.

Usage:
    python scripts/train_model_real.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="outputs/real/seller_features.csv")
    parser.add_argument("--output-dir", default="outputs/real/model")
    args = parser.parse_args()

    try:
        import joblib
        import pandas as pd
        from sklearn.compose import ColumnTransformer
        from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
        from sklearn.impute import SimpleImputer
        from sklearn.metrics import average_precision_score, classification_report, roc_auc_score
        from sklearn.model_selection import train_test_split
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder
    except Exception as exc:
        raise SystemExit(f"Missing dependency: {exc}. pip install -r requirements.txt")

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.input)
    target = "churn_label"

    # Select numeric features (exclude identifiers and target)
    exclude = {"seller_id", "city", "state", "business_type", "turnover_range", "package",
               "churn_label", "churn_signal_count"}
    numeric_features = [c for c in df.columns if c not in exclude and df[c].dtype in ("float64", "int64", "float32", "int32")]
    categorical_features = ["package", "business_type", "turnover_range"]
    categorical_features = [c for c in categorical_features if c in df.columns]

    # Handle None/NaN in days_to_renewal
    if "days_to_renewal" in df.columns:
        df["days_to_renewal"] = pd.to_numeric(df["days_to_renewal"], errors="coerce").fillna(365)

    X = df[numeric_features + categorical_features]
    y = df[target]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

    preprocessor = ColumnTransformer(transformers=[
        ("num", Pipeline([("imputer", SimpleImputer(strategy="median"))]), numeric_features),
        ("cat", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore"))
        ]), categorical_features),
    ])

    model = Pipeline(steps=[
        ("preprocess", preprocessor),
        ("model", GradientBoostingClassifier(
            n_estimators=200, max_depth=5, min_samples_leaf=10,
            learning_rate=0.1, random_state=42
        )),
    ])

    model.fit(X_train, y_train)
    probs = model.predict_proba(X_test)[:, 1]
    preds = (probs >= 0.5).astype(int)

    metrics = {
        "roc_auc": round(float(roc_auc_score(y_test, probs)), 4),
        "pr_auc": round(float(average_precision_score(y_test, probs)), 4),
        "classification_report": classification_report(y_test, preds, output_dict=True),
        "features": {"numeric": numeric_features, "categorical": categorical_features},
        "train_size": len(X_train),
        "test_size": len(X_test),
    }

    # Feature importance
    gb_model = model.named_steps["model"]
    feature_names = numeric_features.copy()
    if categorical_features:
        ohe = model.named_steps["preprocess"].named_transformers_["cat"].named_steps["onehot"]
        feature_names += list(ohe.get_feature_names_out(categorical_features))
    importances = gb_model.feature_importances_
    top_features = sorted(zip(feature_names, importances), key=lambda x: -x[1])[:20]
    metrics["top_features"] = [{"feature": f, "importance": round(float(i), 4)} for f, i in top_features]

    joblib.dump(model, out / "churn_model_gb.joblib")
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(json.dumps({
        "output_dir": str(out),
        "roc_auc": metrics["roc_auc"],
        "pr_auc": metrics["pr_auc"],
        "top_3_features": [f["feature"] for f in metrics["top_features"][:3]],
    }, indent=2))


if __name__ == "__main__":
    main()
