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
    """
    Thresholds calibrated to actual IndiaMART dataset distributions:
      neg_intent:    median=0.20, p75=0.28, max=0.75
      pickup_30d:    median=0.63, p25=0.45
      cancel_rate:   median=0.21, p75=0.33
      overall_rating: median=3.6, p25=2.8
      buylead_trend:  p25=-17%, min=-86%
      days_to_renewal: -349 to +15 (94% already expired)
    """
    reasons: List[Dict] = []
    score = 0.0

    # 1. Negative call intent — Considering Cancellation + Disengaged (weight: 22)
    # Range 0–0.75; median=0.20. Threshold at 0.40 for max score.
    neg_intent = sf(f.get("negative_intent_pct"))
    score += 22 * clamp(neg_intent / 0.40, 0, 1)
    if neg_intent > 0.20:
        reasons.append(reason("high_negative_intent", "high",
            f"{neg_intent*100:.0f}% of calls show cancellation/disengaged intent"))

    # 2. Call pickup rate (weight: 15)
    # Median=0.63, p25=0.45. Start scoring below 0.70, max at 0.10.
    pickup_30 = sf(f.get("act_30d_call_pickup_pct"))
    score += 15 * clamp((0.70 - pickup_30) / 0.60, 0, 1)
    if pickup_30 < 0.45:
        reasons.append(reason("low_call_pickup", "high",
            f"Call pickup rate is {pickup_30*100:.0f}% (30-day)"))

    # 3. Cancellation rate (weight: 14)
    # Median=0.21, p75=0.33. Threshold at 0.40 for max score.
    cancel_rate = sf(f.get("cancellation_rate"))
    score += 14 * clamp(cancel_rate / 0.40, 0, 1)
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
    # Median=3.6, range 2.0–5.0. Threshold at 4.0 (below median is concern).
    rating = sf(f.get("overall_rating"))
    score += 8 * clamp((4.0 - rating) / 3.0, 0, 1)
    if rating < 3.0:
        reasons.append(reason("low_rating", "medium",
            f"Overall rating is {rating:.1f}/5"))

    # 6. Low review response (weight: 6)
    rev_resp = sf(f.get("low_review_response_rate"))
    low_count = si(f.get("low_rating_review_count"))
    score += 6 * clamp((0.60 - rev_resp) / 0.60, 0, 1)
    if rev_resp < 0.30 and low_count >= 5:
        reasons.append(reason("unresponsive_to_reviews", "medium",
            f"Only {rev_resp*100:.0f}% of {low_count} negative reviews addressed"))

    # 7. Open/conflict tickets (weight: 7)
    open_tkt = si(f.get("open_tickets"))
    conflict = si(f.get("conflict_tickets"))
    score += 4 * clamp(open_tkt / 3, 0, 1)
    score += 3 * clamp(conflict / 2, 0, 1)
    if open_tkt >= 2:
        reasons.append(reason("open_tickets", "medium", f"{open_tkt} open support tickets"))
    if conflict >= 1:
        reasons.append(reason("buyer_conflicts", "high", f"{conflict} buyer-supplier conflict ticket(s)"))

    # 8. Untouched contacts (weight: 5)
    # Median=0.167, p75=0.258. Threshold at 0.30.
    untouched = sf(f.get("untouched_pct"))
    score += 5 * clamp(untouched / 0.30, 0, 1)
    if untouched > 0.20:
        reasons.append(reason("untouched_leads", "medium",
            f"{untouched*100:.0f}% of contacts untouched"))

    # 9. Trend decay — buylead/enquiry % change vs prior months (weight: 10)
    # bl_trend range: -86 to +68; p25=-17.7%. Max at -50%.
    bl_trend  = sf(f.get("buylead_trend"))
    enq_trend = sf(f.get("enquiry_trend"))
    score += 6 * clamp(-bl_trend / 50, 0, 1)
    score += 4 * clamp(-enq_trend / 100, 0, 1)
    if bl_trend < -20:
        reasons.append(reason("declining_buyleads", "medium",
            f"BuyLead volume down {abs(bl_trend):.0f}% vs prior period"))

    # 10. Subscription status (weight: 10)
    # Dataset: dtr range -349 to +15; 94% expired. Most actionable: dtr -90 to +90.
    days_renew = f.get("days_to_renewal")
    if days_renew not in ("", None, "None"):
        dr = si(days_renew)
        if 0 <= dr <= 90:
            # About to expire — highest urgency
            score += 10 * clamp((90 - dr) / 90, 0, 1)
            reasons.append(reason("renewal_approaching", "critical",
                f"Subscription expires in {dr} days"))
        elif -30 <= dr < 0:
            # Just expired — still recoverable
            score += 8
            reasons.append(reason("subscription_expired", "high",
                f"Subscription expired {abs(dr)} days ago"))
        elif -90 <= dr < -30:
            score += 5
            reasons.append(reason("subscription_lapsed", "medium",
                f"Subscription lapsed {abs(dr)} days ago"))
        elif -180 <= dr < -90:
            score += 3

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
