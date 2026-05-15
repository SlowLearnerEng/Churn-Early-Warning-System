#!/usr/bin/env python3
"""
Explainable rule-based churn scoring for generated datasets.

This script reads seller, subscription, and seller_health_daily CSVs and writes:
- churn_scores.csv
- alert_events.csv
- retention_actions.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


TODAY = date(2026, 5, 15)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fieldnames: List[str], rows: Iterable[Dict[str, object]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def as_float(row: Dict[str, str], key: str, default: float = 0.0) -> float:
    try:
        value = row.get(key, "")
        return default if value == "" else float(value)
    except Exception:
        return default


def band(score: float) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def parse_date(value: str) -> date:
    return datetime.fromisoformat(value[:10]).date()


def reason(code: str, severity: str, evidence: str) -> Dict[str, str]:
    return {"code": code, "severity": severity, "evidence": evidence}


def score_seller(
    seller: Dict[str, str], latest_health: Dict[str, str], prior_health: Dict[str, str], subscription: Dict[str, str] | None
) -> Tuple[float, float, List[Dict[str, str]], str, float, int | None]:
    reasons: List[Dict[str, str]] = []

    response_now = as_float(latest_health, "response_rate_30d")
    response_prior = as_float(prior_health, "response_rate_30d", response_now)
    response_drop = max(0.0, response_prior - response_now)
    lead_util = as_float(latest_health, "lead_utilization_score")
    catalog_stale = as_float(latest_health, "catalog_staleness_days")
    avg_response = as_float(latest_health, "avg_response_minutes_30d")
    sentiment = as_float(latest_health, "sentiment_avg_30d")
    graph_degree = as_float(latest_health, "graph_degree_90d")
    conversion = as_float(latest_health, "conversion_rate_90d")

    score = 0.0
    score += 28 * clamp(1 - response_now, 0, 1)
    score += 18 * clamp(response_drop / 0.35, 0, 1)
    score += 20 * clamp((55 - lead_util) / 55, 0, 1)
    score += 12 * clamp(avg_response / 1440, 0, 1)
    score += 9 * clamp(catalog_stale / 180, 0, 1)
    score += 7 * clamp((0.15 - conversion) / 0.15, 0, 1)
    score += 6 * clamp((0.05 - sentiment) / 1.05, 0, 1)

    days_to_renewal = None
    revenue_at_risk = 0.0
    if subscription:
        renewal_date = parse_date(subscription["renewal_date"])
        days_to_renewal = (renewal_date - TODAY).days
        revenue_at_risk = as_float(subscription, "package_value")
        usage_score = as_float(subscription, "usage_score")
        adoption = as_float(subscription, "feature_adoption_score")
        if 0 <= days_to_renewal <= 90:
            score += 10
            reasons.append(reason("renewal_in_90_days", "high", f"renewal is in {days_to_renewal} days"))
        if usage_score < 45:
            score += 8
            reasons.append(reason("low_premium_usage", "high", f"usage_score is {usage_score:.1f}"))
        if adoption < 40:
            score += 6
            reasons.append(reason("low_feature_adoption", "medium", f"feature_adoption_score is {adoption:.1f}"))

    if response_drop >= 0.18:
        reasons.append(reason("response_rate_drop", "high", f"response_rate_30d dropped from {response_prior:.2f} to {response_now:.2f}"))
    if response_now < 0.50:
        reasons.append(reason("low_response_rate", "high", f"response_rate_30d is {response_now:.2f}"))
    if lead_util < 45:
        reasons.append(reason("lead_utilization_decline", "high", f"lead_utilization_score is {lead_util:.1f}"))
    if avg_response > 720:
        reasons.append(reason("slow_response_time", "medium", f"avg_response_minutes_30d is {avg_response:.0f}"))
    if catalog_stale > 120:
        reasons.append(reason("catalog_staleness", "medium", f"catalog has not been refreshed for {catalog_stale:.0f} days"))
    if graph_degree < 3:
        reasons.append(reason("weak_buyer_network", "medium", f"only {graph_degree:.0f} active buyer relationships in 90 days"))

    score = clamp(score, 1, 99)
    confidence = clamp(0.55 + 0.08 * min(len(reasons), 4) + (0.08 if subscription else 0), 0.55, 0.95)
    risk_band = band(score)
    return round(score, 2), round(confidence, 3), reasons[:5], risk_band, revenue_at_risk, days_to_renewal


def action_for_reasons(reasons: List[Dict[str, str]], risk_band: str) -> str:
    codes = {r["code"] for r in reasons}
    if "renewal_in_90_days" in codes and risk_band in {"high", "critical"}:
        return "sales_call_with_roi_summary"
    if "catalog_staleness" in codes:
        return "catalog_optimization"
    if "slow_response_time" in codes or "low_response_rate" in codes:
        return "response_time_coaching"
    if "lead_utilization_decline" in codes:
        return "lead_handling_workshop"
    return "automated_health_nudge"


def build_latest_health(health_rows: List[Dict[str, str]]) -> Tuple[Dict[str, Dict[str, str]], Dict[str, Dict[str, str]]]:
    by_seller: Dict[str, List[Dict[str, str]]] = {}
    for row in health_rows:
        by_seller.setdefault(row["seller_id"], []).append(row)
    latest: Dict[str, Dict[str, str]] = {}
    prior: Dict[str, Dict[str, str]] = {}
    for seller_id, rows in by_seller.items():
        rows.sort(key=lambda r: r["as_of_date"])
        latest[seller_id] = rows[-1]
        prior[seller_id] = rows[0] if len(rows) > 1 else rows[-1]
    return latest, prior


def main() -> None:
    parser = argparse.ArgumentParser(description="Score generated churn data with an explainable rule engine.")
    parser.add_argument("--input-dir", default="data/demo", help="Directory containing csv/ or CSV files.")
    parser.add_argument("--output-dir", default="outputs/demo_scores")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    csv_dir = input_dir / "csv" if (input_dir / "csv").exists() else input_dir
    output_dir = Path(args.output_dir)

    sellers = read_csv(csv_dir / "sellers.csv")
    health_rows = read_csv(csv_dir / "seller_health_daily.csv")
    subs = read_csv(csv_dir / "subscriptions.csv") if (csv_dir / "subscriptions.csv").exists() else []
    latest_health, prior_health = build_latest_health(health_rows)
    subs_by_seller = {row["seller_id"]: row for row in subs}

    score_rows: List[Dict[str, object]] = []
    alert_rows: List[Dict[str, object]] = []
    action_rows: List[Dict[str, object]] = []
    for idx, seller in enumerate(sellers, start=1):
        seller_id = seller["seller_id"]
        if seller_id not in latest_health:
            continue
        score, confidence, reasons, risk_band, revenue_at_risk, days_to_renewal = score_seller(
            seller, latest_health[seller_id], prior_health[seller_id], subs_by_seller.get(seller_id)
        )
        action_code = action_for_reasons(reasons, risk_band)
        score_id = f"SC{idx:08d}"
        score_rows.append(
            {
                "score_id": score_id,
                "entity_type": "seller",
                "entity_id": seller_id,
                "as_of_date": TODAY.isoformat(),
                "model_name": "rule_engine",
                "model_version": "v1",
                "horizon_days": 90,
                "risk_score": score,
                "risk_band": risk_band,
                "confidence": confidence,
                "reason_codes": json.dumps(reasons),
                "revenue_at_risk": revenue_at_risk,
                "recommended_action": action_code,
            }
        )
        if risk_band in {"medium", "high", "critical"}:
            priority = round(
                clamp(0.58 * score + 0.22 * min(revenue_at_risk / 1500, 100) + 0.20 * (100 - min(days_to_renewal or 100, 100)), 1, 100),
                2,
            )
            alert_id = f"ALT{idx:08d}"
            alert_rows.append(
                {
                    "alert_id": alert_id,
                    "score_id": score_id,
                    "entity_type": "seller",
                    "entity_id": seller_id,
                    "severity": risk_band,
                    "title": "Churn risk requires retention action",
                    "status": "open",
                    "owner_id": f"E{(idx % 75) + 1:05d}",
                    "priority_score": priority,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                }
            )
            action_rows.append(
                {
                    "action_id": f"ACT{idx:08d}",
                    "alert_id": alert_id,
                    "entity_type": "seller",
                    "entity_id": seller_id,
                    "action_code": action_code,
                    "owner_id": f"E{(idx % 75) + 1:05d}",
                    "status": "scheduled" if risk_band in {"high", "critical"} else "recommended",
                    "expected_outcome": "recover_usage_and_improve_renewal_probability",
                }
            )

    write_csv(
        output_dir / "churn_scores.csv",
        [
            "score_id",
            "entity_type",
            "entity_id",
            "as_of_date",
            "model_name",
            "model_version",
            "horizon_days",
            "risk_score",
            "risk_band",
            "confidence",
            "reason_codes",
            "revenue_at_risk",
            "recommended_action",
        ],
        score_rows,
    )
    write_csv(
        output_dir / "alert_events.csv",
        ["alert_id", "score_id", "entity_type", "entity_id", "severity", "title", "status", "owner_id", "priority_score", "created_at"],
        alert_rows,
    )
    write_csv(
        output_dir / "retention_actions.csv",
        ["action_id", "alert_id", "entity_type", "entity_id", "action_code", "owner_id", "status", "expected_outcome"],
        action_rows,
    )
    print(json.dumps({"scores": len(score_rows), "alerts": len(alert_rows), "actions": len(action_rows), "output_dir": str(output_dir)}, indent=2))


if __name__ == "__main__":
    main()
