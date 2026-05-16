#!/usr/bin/env python3
"""
Export real data into dashboard_data.json for the frontend.

Merges: seller profiles, features, scores, calls, reviews, tickets, ratings, trends, AI summaries.

Usage:
    python scripts/export_real_dashboard.py
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sf(v, d=0.0):
    try: return float(v) if v not in ("", None, "None") else d
    except: return d

def si(v, d=0):
    try: return int(float(v)) if v not in ("", None, "None") else d
    except: return d


def main() -> None:
    data_dir = Path("data/csv")
    real_dir = Path("outputs/real")
    out_dir = Path("dashboard/data")
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- Load sources ----
    profiles = read_csv(data_dir / "dataset - seller_profile.csv")
    features = read_csv(real_dir / "seller_features.csv")
    scores = read_csv(real_dir / "churn_scores.csv")
    alerts = read_csv(real_dir / "alert_events.csv")
    actions = read_csv(real_dir / "retention_actions.csv")
    calls = read_csv(data_dir / "dataset - buyer_seller_calls.csv")
    reviews = read_csv(data_dir / "dataset - seller_low_rating_reviews.csv")
    tickets = read_csv(data_dir / "dataset - seller_tickets.csv")
    ratings = read_csv(data_dir / "dataset - seller_ratings.csv")
    trends = read_csv(data_dir / "dataset - seller_monthly_weekly_trends.csv")
    catalogue = read_csv(data_dir / "dataset - seller_catalogue.csv")

    # AI summaries (if generated)
    ai_summaries = {}
    ai_path = real_dir / "ai_summaries.json"
    if ai_path.exists():
        ai_summaries = json.loads(ai_path.read_text(encoding="utf-8"))

    # ---- Index ----
    prof_idx = {p["seller_id"]: p for p in profiles}
    feat_idx = {f["seller_id"]: f for f in features}
    score_idx = {s["seller_id"]: s for s in scores}
    rat_idx = {r["seller_id"]: r for r in ratings}
    action_idx = {a["seller_id"]: a for a in actions}

    calls_by = defaultdict(list)
    for c in calls: calls_by[c["seller_id"]].append(c)
    reviews_by = defaultdict(list)
    for r in reviews: reviews_by[r["seller_id"]].append(r)
    tickets_by = defaultdict(list)
    for t in tickets: tickets_by[t["seller_id"]].append(t)
    trends_by = defaultdict(list)
    for t in trends:
        if t.get("period_type") == "Monthly":
            trends_by[t["seller_id"]].append(t)
    cat_by = defaultdict(list)
    for c in catalogue: cat_by[c["seller_id"]].append(c)

    # ---- Build seller list ----
    seller_list = []
    for p in profiles:
        sid = p["seller_id"]
        s = score_idx.get(sid, {})
        f = feat_idx.get(sid, {})
        r = rat_idx.get(sid, {})
        act = action_idx.get(sid, {})
        ai = ai_summaries.get(sid, None)

        risk_score = sf(s.get("risk_score"))
        risk_band = s.get("risk_band", "low")
        pkg_val = sf(s.get("revenue_at_risk"))

        # Priority score
        dtr = si(f.get("days_to_renewal"), 365)
        priority = round(0.50 * risk_score + 0.25 * min(pkg_val / 5000, 100) + 0.25 * (100 - min(dtr, 100)), 2)

        reason_codes = []
        try: reason_codes = json.loads(s.get("reason_codes", "[]"))
        except: pass

        # Trend data for sparklines
        monthly = sorted(trends_by.get(sid, []), key=lambda x: (x.get("year",""), x.get("month","")))
        health_trend = [
            {
                "period": m.get("period_label", ""),
                "buyleads": si(m.get("buyleads")),
                "enquiries": si(m.get("enquiries")),
                "call_pickup_pct": sf(m.get("call_pickup_pct")),
                "lms_active_days": si(m.get("lms_active_days")),
                "replies": si(m.get("replies")),
                "callbacks": si(m.get("callbacks")),
            }
            for m in monthly
        ]

        # Recent calls (top 8 most recent)
        seller_calls = sorted(calls_by.get(sid, []), key=lambda x: x.get("call_date",""), reverse=True)[:8]
        call_data = [
            {
                "date": c.get("call_date", ""),
                "buyer": c.get("buyer_name", ""),
                "product": c.get("mcat_name", ""),
                "duration": si(c.get("call_duration_mins")),
                "summary": c.get("call_summary", "")[:200],
                "seller_intent": c.get("seller_intent", ""),
                "buyer_intent": c.get("buyer_intent", ""),
            }
            for c in seller_calls
        ]

        # Recent reviews (top 5)
        seller_revs = sorted(reviews_by.get(sid, []), key=lambda x: x.get("review_date",""), reverse=True)[:5]
        review_data = [
            {
                "date": rv.get("review_date", ""),
                "rating": si(rv.get("rating")),
                "text": rv.get("review_text", "")[:200],
                "product": rv.get("product_name", ""),
                "responded": rv.get("response_by_seller", "No"),
            }
            for rv in seller_revs
        ]

        # Tickets
        seller_tkts = tickets_by.get(sid, [])
        ticket_data = [
            {
                "type": t.get("ticket_type", ""),
                "status": t.get("status", ""),
                "risk_level": t.get("risk_level", ""),
                "created": t.get("created_date", ""),
                "resolved": t.get("resolved_date", ""),
            }
            for t in seller_tkts
        ]

        # Catalogue
        cats = cat_by.get(sid, [])
        catalogue_data = [
            {
                "category": c.get("mcat_name", ""),
                "products": si(c.get("total_products")),
                "rank": c.get("best_rank", ""),
                "bl_6m": si(c.get("bl_purchased_6m")),
            }
            for c in cats
        ]

        seller_list.append({
            "seller_id": sid,
            "seller_name": p.get("seller_name", ""),
            "company_name": p.get("company_name", ""),
            "city": p.get("city", ""),
            "state": p.get("state", ""),
            "business_type": p.get("business_type", ""),
            "turnover_range": p.get("turnover_range", ""),
            "package": p.get("package", ""),
            "member_since_years": si(p.get("member_since_years")),
            "subscription_end_date": p.get("subscription_end_date", ""),
            "gst_verified": si(p.get("gst_verified")),
            "verification_score": si(p.get("verification_score")),
            "trustseal_active": si(p.get("trustseal_active")),
            "risk_score": risk_score,
            "risk_band": risk_band,
            "confidence": sf(s.get("confidence")),
            "reason_codes": reason_codes,
            "recommended_action": s.get("recommended_action", ""),
            "action_code": act.get("action_code", s.get("recommended_action", "")),
            "action_status": act.get("status", ""),
            "owner_id": act.get("owner_id", ""),
            "revenue_at_risk": pkg_val,
            "priority_score": priority,
            "days_to_renewal": dtr,
            # Key metrics for display
            "call_pickup_pct_30d": sf(f.get("act_30d_call_pickup_pct")),
            "total_enquiries_30d": si(f.get("act_30d_total_enquiries")),
            "callbacks_30d": si(f.get("act_30d_callbacks")),
            "catalogue_score": sf(f.get("act_30d_catalogue_score")),
            "overall_rating": sf(f.get("overall_rating")),
            "negative_intent_pct": sf(f.get("negative_intent_pct")),
            "cancellation_rate": sf(f.get("cancellation_rate")),
            "total_contacts": si(f.get("total_contacts")),
            "contacts_converted": si(f.get("contacts_converted")),
            "untouched_pct": sf(f.get("untouched_pct")),
            "low_review_response_rate": sf(f.get("low_review_response_rate")),
            "open_tickets": si(f.get("open_tickets")),
            "total_products": si(f.get("total_products")),
            "total_spend": sf(f.get("total_spend")),
            # Drill-down data
            "health_trend": health_trend,
            "calls": call_data,
            "reviews": review_data,
            "tickets": ticket_data,
            "catalogue": catalogue_data,
            "ai_summary": ai,
        })

    # ---- Executive summary ----
    band_counts = Counter(s["risk_band"] for s in seller_list)
    total_rev_risk = sum(s["revenue_at_risk"] for s in seller_list if s["risk_band"] in ("high","critical","medium"))

    upcoming_renewals = sum(1 for s in seller_list if 0 <= s["days_to_renewal"] <= 90)
    high_risk_renewals = sum(1 for s in seller_list if 0 <= s["days_to_renewal"] <= 90 and s["risk_band"] in ("high","critical"))

    # Top reasons
    reason_counter = Counter()
    for s in seller_list:
        for rc in s["reason_codes"]:
            reason_counter[rc.get("code", "")] += 1
    top_reasons = reason_counter.most_common(10)

    # Heatmap (state × package)
    heatmap: Dict[str, Dict[str, Dict]] = defaultdict(lambda: defaultdict(lambda: {"count": 0, "total_risk": 0}))
    for s in seller_list:
        cell = heatmap[s["package"]][s["state"]]
        cell["count"] += 1
        cell["total_risk"] += s["risk_score"]
    # Average risk
    for pkg in heatmap:
        for state in heatmap[pkg]:
            c = heatmap[pkg][state]
            c["avg_risk"] = round(c["total_risk"] / max(c["count"], 1), 1)

    # Cohorts
    def build_cohort(key_fn):
        cohort = defaultdict(lambda: {"count": 0, "total_risk": 0, "revenue_at_risk": 0, "bands": Counter()})
        for s in seller_list:
            k = key_fn(s)
            c = cohort[k]
            c["count"] += 1
            c["total_risk"] += s["risk_score"]
            c["revenue_at_risk"] += s["revenue_at_risk"]
            c["bands"][s["risk_band"]] += 1
        for k in cohort:
            cohort[k]["avg_risk"] = round(cohort[k]["total_risk"] / max(cohort[k]["count"], 1), 1)
        return dict(cohort)

    def turnover_tier(s):
        t = s.get("turnover_range", "")
        if "100" in t: return "Enterprise"
        if "25" in t: return "Large"
        if "5" in t: return "Mid"
        if "1" in t: return "Small"
        return "Micro"

    cohorts = {
        "by_package": build_cohort(lambda s: s["package"]),
        "by_state": build_cohort(lambda s: s["state"]),
        "by_business_type": build_cohort(lambda s: s["business_type"]),
        "by_turnover": build_cohort(lambda s: turnover_tier(s)),
    }

    actioned = sum(1 for s in seller_list if s.get("action_status") in ("scheduled", "completed"))

    executive = {
        "total_sellers": len(seller_list),
        "total_revenue_at_risk": round(total_rev_risk, 2),
        "band_counts": dict(band_counts),
        "critical_count": band_counts.get("critical", 0),
        "high_count": band_counts.get("high", 0),
        "total_alerts": len(alerts),
        "top_reasons": top_reasons,
        "heatmap": {k: dict(v) for k, v in heatmap.items()},
        "renewal_funnel": {
            "upcoming": upcoming_renewals,
            "high_risk": high_risk_renewals,
            "actioned": actioned,
        },
    }

    # ---- Final output ----
    dashboard = {
        "generated_at": "2025-12-15T00:00:00Z",
        "executive": executive,
        "sellers": seller_list,
        "cohorts": cohorts,
    }

    out_path = out_dir / "dashboard_data.json"
    out_path.write_text(json.dumps(dashboard, default=str), encoding="utf-8")

    size_mb = out_path.stat().st_size / 1024 / 1024
    print(json.dumps({
        "output": str(out_path),
        "size_mb": round(size_mb, 2),
        "sellers": len(seller_list),
        "with_ai_summary": sum(1 for s in seller_list if s.get("ai_summary")),
        "alerts": len(alerts),
        "executive": {k: v for k, v in executive.items() if k != "heatmap"},
    }, indent=2))


if __name__ == "__main__":
    main()
