#!/usr/bin/env python3
"""
Merge generated CSVs and scoring outputs into a single JSON file
for the static HTML dashboard.

Usage:
    python scripts/export_dashboard_data.py
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def safe_float(val: str, default: float = 0.0) -> float:
    try:
        return float(val) if val else default
    except ValueError:
        return default


def safe_int(val: str, default: int = 0) -> int:
    try:
        return int(float(val)) if val else default
    except ValueError:
        return default


def main() -> None:
    parser = argparse.ArgumentParser(description="Export dashboard JSON from CSVs.")
    parser.add_argument("--data-dir", default="data/demo/csv")
    parser.add_argument("--scores-dir", default="outputs/demo_scores")
    parser.add_argument("--output", default="dashboard/data/dashboard_data.json")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    scores_dir = Path(args.scores_dir)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # ---- Load all CSVs ----
    sellers_raw = read_csv(data_dir / "sellers.csv")
    subs_raw = read_csv(data_dir / "subscriptions.csv")
    health_raw = read_csv(data_dir / "seller_health_daily.csv")
    buyers_raw = read_csv(data_dir / "buyers.csv")
    scores_raw = read_csv(scores_dir / "churn_scores.csv")
    alerts_raw = read_csv(scores_dir / "alert_events.csv")
    actions_raw = read_csv(scores_dir / "retention_actions.csv")

    # ---- Index by seller_id ----
    subs_by_seller: Dict[str, Dict] = {}
    for s in subs_raw:
        subs_by_seller[s["seller_id"]] = s

    # Latest health per seller
    health_by_seller: Dict[str, List[Dict]] = defaultdict(list)
    for h in health_raw:
        health_by_seller[h["seller_id"]].append(h)

    scores_by_entity: Dict[str, Dict] = {}
    for sc in scores_raw:
        scores_by_entity[sc["entity_id"]] = sc

    alerts_by_entity: Dict[str, Dict] = {}
    for al in alerts_raw:
        alerts_by_entity[al["entity_id"]] = al

    actions_by_entity: Dict[str, Dict] = {}
    for ac in actions_raw:
        actions_by_entity[ac["entity_id"]] = ac

    # ---- Build enriched seller list ----
    sellers: List[Dict[str, Any]] = []
    for row in sellers_raw:
        sid = row["seller_id"]
        sub = subs_by_seller.get(sid, {})
        score_row = scores_by_entity.get(sid, {})
        alert_row = alerts_by_entity.get(sid, {})
        action_row = actions_by_entity.get(sid, {})

        # Health trend (all snapshots for sparklines)
        h_list = sorted(health_by_seller.get(sid, []), key=lambda x: x.get("as_of_date", ""))
        latest_h = h_list[-1] if h_list else {}

        reason_codes = []
        if score_row.get("reason_codes"):
            try:
                reason_codes = json.loads(score_row["reason_codes"])
            except Exception:
                pass

        sellers.append({
            "seller_id": sid,
            "business_name": row.get("business_name", sid),
            "category": row.get("business_category", ""),
            "city": row.get("city", ""),
            "state": row.get("state", ""),
            "region": row.get("region", ""),
            "tier": row.get("subscription_tier", "free"),
            "archetype": row.get("archetype", ""),
            "onboarding_date": row.get("onboarding_date", ""),
            "response_rate": safe_float(row.get("response_rate")),
            "avg_response_minutes": safe_float(row.get("avg_response_minutes")),
            "product_count": safe_int(row.get("product_count")),
            "catalog_quality_score": safe_float(row.get("catalog_quality_score")),
            "lead_utilization_score": safe_float(row.get("lead_utilization_score")),
            "gst_verified": row.get("gst_verified", "False") == "True",
            "trust_score": safe_float(row.get("trust_score")),
            "churn_label": safe_int(row.get("churn_label")),
            # Subscription
            "plan_type": sub.get("plan_type", row.get("subscription_tier", "free")),
            "renewal_date": sub.get("renewal_date", ""),
            "package_value": safe_float(sub.get("package_value")),
            "usage_score": safe_float(sub.get("usage_score")),
            "feature_adoption_score": safe_float(sub.get("feature_adoption_score")),
            "login_frequency": safe_float(sub.get("login_frequency")),
            # Scores
            "risk_score": safe_float(score_row.get("risk_score")),
            "risk_band": score_row.get("risk_band", "low"),
            "confidence": safe_float(score_row.get("confidence")),
            "revenue_at_risk": safe_float(score_row.get("revenue_at_risk")),
            "recommended_action": score_row.get("recommended_action", ""),
            "reason_codes": reason_codes,
            # Alert
            "alert_id": alert_row.get("alert_id", ""),
            "alert_severity": alert_row.get("severity", ""),
            "alert_status": alert_row.get("status", ""),
            "priority_score": safe_float(alert_row.get("priority_score")),
            "owner_id": alert_row.get("owner_id", ""),
            # Action
            "action_code": action_row.get("action_code", ""),
            "action_status": action_row.get("status", ""),
            # Health trend
            "health_trend": [
                {
                    "date": h.get("as_of_date", ""),
                    "response_rate": safe_float(h.get("response_rate_30d")),
                    "lead_util": safe_float(h.get("lead_utilization_score")),
                    "inquiries": safe_int(h.get("inquiries_received_30d")),
                    "handled": safe_int(h.get("handled_leads_30d")),
                    "conversion": safe_float(h.get("conversion_rate_90d")),
                    "sentiment": safe_float(h.get("sentiment_avg_30d")),
                    "catalog_staleness": safe_int(h.get("catalog_staleness_days")),
                    "graph_degree": safe_int(h.get("graph_degree_90d")),
                }
                for h in h_list
            ],
        })

    # ---- Executive aggregates ----
    band_counts = Counter(s["risk_band"] for s in sellers)
    band_revenue: Dict[str, float] = defaultdict(float)
    for s in sellers:
        band_revenue[s["risk_band"]] += s["revenue_at_risk"]

    reason_counter: Counter = Counter()
    for s in sellers:
        for rc in s["reason_codes"]:
            reason_counter[rc.get("code", "unknown")] += 1

    total_revenue_at_risk = sum(s["revenue_at_risk"] for s in sellers)
    total_alerts = len(alerts_raw)
    critical_count = band_counts.get("critical", 0)
    high_count = band_counts.get("high", 0)

    # Renewal funnel
    upcoming_renewals = sum(1 for s in sellers if s["renewal_date"] and s["package_value"] > 0)
    high_risk_renewals = sum(1 for s in sellers if s["risk_band"] in ("high", "critical") and s["renewal_date"])
    actioned = sum(1 for s in sellers if s["action_status"] in ("scheduled", "completed"))

    # Heatmap: category x city
    heatmap: Dict[str, Dict[str, Dict]] = defaultdict(lambda: defaultdict(lambda: {"count": 0, "avg_risk": 0, "total_risk": 0}))
    for s in sellers:
        cell = heatmap[s["category"]][s["city"]]
        cell["count"] += 1
        cell["total_risk"] += s["risk_score"]
    for cat in heatmap:
        for city in heatmap[cat]:
            c = heatmap[cat][city]
            c["avg_risk"] = round(c["total_risk"] / c["count"], 1) if c["count"] else 0
            del c["total_risk"]

    executive = {
        "total_sellers": len(sellers),
        "total_revenue_at_risk": round(total_revenue_at_risk, 2),
        "total_alerts": total_alerts,
        "critical_count": critical_count,
        "high_count": high_count,
        "band_counts": dict(band_counts),
        "band_revenue": {k: round(v, 2) for k, v in band_revenue.items()},
        "top_reasons": reason_counter.most_common(10),
        "renewal_funnel": {
            "upcoming": upcoming_renewals,
            "high_risk": high_risk_renewals,
            "actioned": actioned,
        },
        "heatmap": {cat: dict(cities) for cat, cities in heatmap.items()},
    }

    # ---- Cohorts ----
    def cohort_agg(key_fn):
        groups: Dict[str, List] = defaultdict(list)
        for s in sellers:
            k = key_fn(s)
            if k:
                groups[k].append(s)
        result = {}
        for k, members in groups.items():
            bc = Counter(m["risk_band"] for m in members)
            result[k] = {
                "count": len(members),
                "avg_risk": round(sum(m["risk_score"] for m in members) / len(members), 1),
                "bands": dict(bc),
                "revenue_at_risk": round(sum(m["revenue_at_risk"] for m in members), 2),
            }
        return result

    cohorts = {
        "by_category": cohort_agg(lambda s: s["category"]),
        "by_city": cohort_agg(lambda s: s["city"]),
        "by_tier": cohort_agg(lambda s: s["tier"]),
        "by_archetype": cohort_agg(lambda s: s["archetype"]),
    }

    # ---- Buyers (simple) ----
    buyers = [
        {
            "buyer_id": b["buyer_id"],
            "industry": b.get("industry", ""),
            "region": b.get("region", ""),
            "activity_level": b.get("activity_level", ""),
            "engagement_score": safe_float(b.get("engagement_score")),
            "churn_label": safe_int(b.get("churn_label")),
        }
        for b in buyers_raw
    ]

    # ---- Alerts list ----
    alerts = [
        {
            "alert_id": a["alert_id"],
            "entity_id": a["entity_id"],
            "severity": a["severity"],
            "status": a["status"],
            "owner_id": a["owner_id"],
            "priority_score": safe_float(a["priority_score"]),
        }
        for a in alerts_raw
    ]

    # ---- Write output ----
    output = {
        "executive": executive,
        "sellers": sellers,
        "buyers_summary": {
            "total": len(buyers),
            "churned": sum(1 for b in buyers if b["churn_label"] == 1),
            "by_activity": dict(Counter(b["activity_level"] for b in buyers)),
            "by_industry": dict(Counter(b["industry"] for b in buyers)),
        },
        "alerts": alerts,
        "cohorts": cohorts,
    }

    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    size_mb = out_path.stat().st_size / 1024 / 1024
    print(json.dumps({"output": str(out_path), "size_mb": round(size_mb, 2), "sellers": len(sellers), "alerts": len(alerts)}, indent=2))


if __name__ == "__main__":
    main()
