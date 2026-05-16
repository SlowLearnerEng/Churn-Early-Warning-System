#!/usr/bin/env python3
"""
Score real seller features with an explainable rule engine.

Reads outputs/real/seller_features.csv and writes:
- churn_scores.csv   (risk score, band, reasons, action per seller)
- alert_events.csv   (alerts for medium/high/critical sellers)
- retention_actions.csv  (recommended interventions)

Usage:
    python scripts/score_real_data.py
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def sf(val, default=0.0):
    try:
        return float(val) if val not in ("", None, "None") else default
    except (ValueError, TypeError):
        return default


def si(val, default=0):
    try:
        return int(float(val)) if val not in ("", None, "None") else default
    except (ValueError, TypeError):
        return default


def band(score: float) -> str:
    if score >= 80: return "critical"
    if score >= 60: return "high"
    if score >= 40: return "medium"
    return "low"


def reason(code: str, severity: str, evidence: str) -> Dict[str, str]:
    return {"code": code, "severity": severity, "evidence": evidence}


def score_seller(f: Dict[str, str]) -> Tuple[float, float, List[Dict], str]:
    reasons: List[Dict] = []
    score = 0.0

    # 1. Negative call intent (weight: 22)
    neg_intent = sf(f.get("negative_intent_pct"))
    score += 22 * clamp(neg_intent / 0.40, 0, 1)
    if neg_intent > 0.20:
        reasons.append(reason("high_negative_intent", "high",
            f"{neg_intent*100:.0f}% of calls show Cancellation/Disengaged intent"))

    # 2. Call pickup decline (weight: 15)
    pickup_30 = sf(f.get("act_30d_call_pickup_pct"))
    score += 15 * clamp((0.70 - pickup_30) / 0.40, 0, 1)
    if pickup_30 < 0.50:
        reasons.append(reason("low_call_pickup", "high",
            f"Call pickup rate is {pickup_30*100:.0f}% (30-day)"))

    # 3. Cancellation rate (weight: 14)
    cancel_rate = sf(f.get("cancellation_rate"))
    score += 14 * clamp(cancel_rate / 0.35, 0, 1)
    if cancel_rate > 0.20:
        cancelled = si(f.get("cancelled_transactions"))
        reasons.append(reason("high_cancellation_rate", "high",
            f"{cancelled} service cancellations ({cancel_rate*100:.0f}% of transactions)"))

    # 4. Service deactivation tickets (weight: 10)
    deact = si(f.get("deactivation_tickets"))
    if deact > 0:
        score += 10
        reasons.append(reason("service_deactivation", "critical",
            f"{deact} service deactivation ticket(s) raised"))

    # 5. Overall rating (weight: 8)
    rating = sf(f.get("overall_rating"))
    score += 8 * clamp((3.0 - rating) / 2.0, 0, 1)
    if rating < 2.5:
        reasons.append(reason("low_rating", "medium",
            f"Overall rating is {rating:.1f}/5"))

    # 6. Low review response (weight: 6)
    rev_resp = sf(f.get("low_review_response_rate"))
    low_count = si(f.get("low_rating_review_count"))
    score += 6 * clamp((0.50 - rev_resp) / 0.50, 0, 1)
    if rev_resp < 0.30 and low_count > 5:
        reasons.append(reason("unresponsive_to_reviews", "medium",
            f"Only {rev_resp*100:.0f}% of {low_count} negative reviews addressed"))

    # 7. Open/conflict tickets (weight: 7)
    open_tkt = si(f.get("open_tickets"))
    conflict = si(f.get("conflict_tickets"))
    score += 4 * clamp(open_tkt / 3, 0, 1)
    score += 3 * clamp(conflict / 2, 0, 1)
    if open_tkt >= 2:
        reasons.append(reason("open_tickets", "medium", f"{open_tkt} open support tickets"))
    if conflict >= 2:
        reasons.append(reason("buyer_conflicts", "high", f"{conflict} buyer-supplier conflict tickets"))

    # 8. Untouched contacts (weight: 5)
    untouched = sf(f.get("untouched_pct"))
    score += 5 * clamp(untouched / 0.35, 0, 1)
    if untouched > 0.25:
        reasons.append(reason("untouched_leads", "medium",
            f"{untouched*100:.0f}% of contacts are untouched"))

    # 9. Trend decay (weight: 8)
    bl_trend = sf(f.get("buylead_trend"))
    enq_trend = sf(f.get("enquiry_trend"))
    score += 4 * clamp(-bl_trend / 30, 0, 1)
    score += 4 * clamp(-enq_trend / 50, 0, 1)
    if bl_trend < -15:
        reasons.append(reason("declining_buyleads", "medium",
            f"BuyLead volume trending down by {abs(bl_trend):.0f} per month"))

    # 10. Renewal proximity amplifier (weight: 5)
    days_renew = f.get("days_to_renewal")
    if days_renew not in ("", None, "None"):
        dr = si(days_renew)
        if 0 <= dr <= 90:
            score += 5 * clamp((90 - dr) / 90, 0, 1)
            reasons.append(reason("renewal_approaching", "high",
                f"Subscription renews in {dr} days"))

    score = round(clamp(score, 1, 99), 2)
    confidence = round(clamp(0.55 + 0.07 * min(len(reasons), 5), 0.55, 0.95), 3)
    risk_band = band(score)

    return score, confidence, reasons[:6], risk_band


def action_for_reasons(reasons: List[Dict], risk_band: str) -> str:
    codes = {r["code"] for r in reasons}
    if "service_deactivation" in codes:
        return "urgent_manager_escalation"
    if "high_negative_intent" in codes and risk_band in ("high", "critical"):
        return "sales_call_with_roi_summary"
    if "low_call_pickup" in codes:
        return "response_time_coaching"
    if "high_cancellation_rate" in codes:
        return "service_value_review"
    if "unresponsive_to_reviews" in codes:
        return "review_response_training"
    if "untouched_leads" in codes:
        return "lead_handling_workshop"
    return "automated_health_nudge"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="outputs/real/seller_features.csv")
    parser.add_argument("--output-dir", default="outputs/real")
    args = parser.parse_args()

    features = []
    with open(args.input, "r", encoding="utf-8") as fh:
        features = list(csv.DictReader(fh))

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    scores, alerts, actions = [], [], []
    for idx, f in enumerate(features, 1):
        risk_score, confidence, reasons, risk_band = score_seller(f)
        action_code = action_for_reasons(reasons, risk_band)
        pkg_value = sf(f.get("total_spend")) * 0.3  # rough annual value proxy

        score_id = f"SC{idx:05d}"
        scores.append({
            "score_id": score_id,
            "seller_id": f["seller_id"],
            "risk_score": risk_score,
            "risk_band": risk_band,
            "confidence": confidence,
            "reason_codes": json.dumps(reasons),
            "recommended_action": action_code,
            "revenue_at_risk": round(pkg_value, 2),
            "package": f.get("package", ""),
            "days_to_renewal": f.get("days_to_renewal", ""),
        })

        if risk_band in ("medium", "high", "critical"):
            dtr = si(f.get("days_to_renewal")) if f.get("days_to_renewal") not in ("", None, "None") else 100
            priority = round(clamp(
                0.50 * risk_score +
                0.25 * min(pkg_value / 5000, 100) +
                0.25 * (100 - min(dtr, 100)),
                1, 100
            ), 2)
            alert_id = f"ALT{idx:05d}"
            alerts.append({
                "alert_id": alert_id, "score_id": score_id,
                "seller_id": f["seller_id"], "severity": risk_band,
                "title": f"Churn risk: {action_code.replace('_',' ')}",
                "status": "open", "owner_id": f"MGR{(idx % 20)+1:03d}",
                "priority_score": priority,
            })
            actions.append({
                "action_id": f"ACT{idx:05d}", "alert_id": alert_id,
                "seller_id": f["seller_id"], "action_code": action_code,
                "owner_id": f"MGR{(idx % 20)+1:03d}",
                "status": "scheduled" if risk_band in ("high", "critical") else "recommended",
            })

    # Write outputs
    def write(path, fieldnames, rows):
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)

    write(out / "churn_scores.csv",
          ["score_id","seller_id","risk_score","risk_band","confidence","reason_codes","recommended_action","revenue_at_risk","package","days_to_renewal"],
          scores)
    write(out / "alert_events.csv",
          ["alert_id","score_id","seller_id","severity","title","status","owner_id","priority_score"],
          alerts)
    write(out / "retention_actions.csv",
          ["action_id","alert_id","seller_id","action_code","owner_id","status"],
          actions)

    band_counts = {}
    for s in scores:
        band_counts[s["risk_band"]] = band_counts.get(s["risk_band"], 0) + 1

    print(json.dumps({
        "scores": len(scores), "alerts": len(alerts), "actions": len(actions),
        "bands": band_counts,
        "output_dir": str(out),
    }, indent=2))


if __name__ == "__main__":
    main()
