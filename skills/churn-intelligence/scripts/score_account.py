#!/usr/bin/env python3
"""Score one account payload for churn risk using deterministic rules."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List


def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


THRESHOLDS = {
    "medium": env_float("CHURN_SCORE_THRESHOLD_MEDIUM", 40),
    "high": env_float("CHURN_SCORE_THRESHOLD_HIGH", 60),
    "critical": env_float("CHURN_SCORE_THRESHOLD_CRITICAL", 80),
}
RENEWAL_WINDOW_DAYS = int(env_float("CHURN_RENEWAL_WINDOW_DAYS", 90))


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def f(payload: Dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        value = payload.get(key, default)
        return default if value is None or value == "" else float(value)
    except Exception:
        return default


def band(score: float) -> str:
    if score >= THRESHOLDS["critical"]:
        return "critical"
    if score >= THRESHOLDS["high"]:
        return "high"
    if score >= THRESHOLDS["medium"]:
        return "medium"
    return "low"


def add_reason(reasons: List[Dict[str, Any]], code: str, severity: str, evidence: str, contribution: float) -> None:
    reasons.append({"code": code, "severity": severity, "evidence": evidence, "contribution": round(contribution, 2)})


def score(payload: Dict[str, Any]) -> Dict[str, Any]:
    entity_type = payload.get("entity_type", "seller")
    reasons: List[Dict[str, Any]] = []
    score_value = 0.0

    if entity_type == "buyer":
        inquiry_now = f(payload, "inquiries_30d")
        inquiry_base = max(f(payload, "inquiries_baseline_90d", inquiry_now), 1)
        repeat_sellers = f(payload, "repeat_seller_count_90d")
        engagement = f(payload, "engagement_score", 50)
        decline = clamp((inquiry_base - inquiry_now) / inquiry_base, 0, 1)
        score_value += 35 * decline
        score_value += 25 * clamp((45 - engagement) / 45, 0, 1)
        score_value += 15 * clamp((2 - repeat_sellers) / 2, 0, 1)
        if decline >= 0.45:
            add_reason(reasons, "buyer_inquiry_decline", "high", f"inquiries_30d declined {decline:.0%} vs baseline", 35 * decline)
        if repeat_sellers < 2:
            add_reason(reasons, "weak_repeat_relationships", "medium", f"repeat_seller_count_90d is {repeat_sellers:.0f}", 15)
    else:
        response_now = f(payload, "response_rate_30d", f(payload, "response_rate", 0.6))
        response_base = f(payload, "response_rate_baseline_90d", response_now)
        response_drop = clamp(response_base - response_now, 0, 1)
        lead_util = f(payload, "lead_utilization_score", 55)
        avg_response = f(payload, "avg_response_minutes_30d", f(payload, "avg_response_minutes", 120))
        catalog_stale = f(payload, "catalog_staleness_days", 60)
        adoption = f(payload, "feature_adoption_score", 60)
        usage = f(payload, "usage_score", 60)
        days_to_renewal = f(payload, "days_to_renewal", 999)

        response_contribution = 28 * clamp(1 - response_now, 0, 1)
        drop_contribution = 18 * clamp(response_drop / 0.35, 0, 1)
        util_contribution = 20 * clamp((55 - lead_util) / 55, 0, 1)
        latency_contribution = 12 * clamp(avg_response / 1440, 0, 1)
        catalog_contribution = 9 * clamp(catalog_stale / 180, 0, 1)
        adoption_contribution = 8 * clamp((45 - adoption) / 45, 0, 1)
        usage_contribution = 8 * clamp((45 - usage) / 45, 0, 1)

        score_value += response_contribution + drop_contribution + util_contribution
        score_value += latency_contribution + catalog_contribution + adoption_contribution + usage_contribution

        if response_drop >= 0.18:
            add_reason(reasons, "response_rate_drop", "high", f"response rate dropped from {response_base:.2f} to {response_now:.2f}", drop_contribution)
        if response_now < 0.50:
            add_reason(reasons, "low_response_rate", "high", f"response_rate_30d is {response_now:.2f}", response_contribution)
        if lead_util < 45:
            add_reason(reasons, "lead_utilization_decline", "high", f"lead_utilization_score is {lead_util:.1f}", util_contribution)
        if avg_response > 720:
            add_reason(reasons, "slow_response_time", "medium", f"avg_response_minutes_30d is {avg_response:.0f}", latency_contribution)
        if catalog_stale > 120:
            add_reason(reasons, "catalog_staleness", "medium", f"catalog_staleness_days is {catalog_stale:.0f}", catalog_contribution)
        if adoption < 40:
            add_reason(reasons, "low_feature_adoption", "medium", f"feature_adoption_score is {adoption:.1f}", adoption_contribution)
        if 0 <= days_to_renewal <= RENEWAL_WINDOW_DAYS:
            score_value += 10
            add_reason(reasons, "renewal_in_90_days", "high", f"renewal is in {days_to_renewal:.0f} days", 10)

    score_value = round(clamp(score_value, 1, 99), 2)
    reasons = sorted(reasons, key=lambda item: item["contribution"], reverse=True)[:5]
    risk_band = band(score_value)
    codes = {item["code"] for item in reasons}
    if "renewal_in_90_days" in codes and risk_band in {"high", "critical"}:
        action = "sales_call_with_roi_summary"
    elif "catalog_staleness" in codes:
        action = "catalog_optimization"
    elif "low_response_rate" in codes or "slow_response_time" in codes:
        action = "response_time_coaching"
    elif "buyer_inquiry_decline" in codes:
        action = "buyer_reactivation_campaign"
    else:
        action = "automated_health_nudge"

    return {
        "entity_type": entity_type,
        "entity_id": payload.get("entity_id"),
        "risk_score": score_value,
        "risk_band": risk_band,
        "confidence": round(clamp(0.56 + 0.08 * len(reasons), 0.56, 0.94), 3),
        "reason_codes": reasons,
        "recommended_action": action,
        "revenue_at_risk": f(payload, "package_value", 0),
    }


def load_payload(args: argparse.Namespace) -> Dict[str, Any]:
    if args.example:
        return {
            "entity_type": "seller",
            "entity_id": "S000042",
            "response_rate_30d": 0.46,
            "response_rate_baseline_90d": 0.78,
            "lead_utilization_score": 38,
            "avg_response_minutes_30d": 910,
            "catalog_staleness_days": 145,
            "feature_adoption_score": 36,
            "usage_score": 42,
            "days_to_renewal": 41,
            "package_value": 65000,
        }
    if args.input:
        return json.loads(Path(args.input).read_text(encoding="utf-8"))
    return json.load(sys.stdin)


def main() -> None:
    parser = argparse.ArgumentParser(description="Score a churn intelligence account JSON payload.")
    parser.add_argument("--input", help="Path to JSON payload. Reads stdin when omitted.")
    parser.add_argument("--example", action="store_true", help="Score a built-in example payload.")
    args = parser.parse_args()
    print(json.dumps(score(load_payload(args)), indent=2))


if __name__ == "__main__":
    main()
