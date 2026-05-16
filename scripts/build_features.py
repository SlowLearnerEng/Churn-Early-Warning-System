#!/usr/bin/env python3
"""
Build seller-level features from the real IndiaMART dataset (data/csv/).

Reads all 10 CSVs, engineers ~50 features per seller, derives a churn label,
and writes a single seller_features.csv for scoring and ML training.

Usage:
    python scripts/build_features.py
    python scripts/build_features.py --input-dir data/csv --output-dir outputs/real
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List

TODAY = date(2025, 12, 15)  # reference date for the dataset timeframe


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sf(val: str, default: float = 0.0) -> float:
    try:
        return float(val) if val not in ("", None) else default
    except (ValueError, TypeError):
        return default


def si(val: str, default: int = 0) -> int:
    try:
        return int(float(val)) if val not in ("", None) else default
    except (ValueError, TypeError):
        return default


def days_between(d1: str, d2: str) -> int | None:
    try:
        return (datetime.fromisoformat(d2[:10]).date() - datetime.fromisoformat(d1[:10]).date()).days
    except Exception:
        return None


def days_until(date_str: str) -> int | None:
    try:
        return (datetime.fromisoformat(date_str[:10]).date() - TODAY).days
    except Exception:
        return None


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build features from real dataset.")
    parser.add_argument("--input-dir", default="data/csv")
    parser.add_argument("--output-dir", default="outputs/real")
    args = parser.parse_args()

    inp = Path(args.input_dir)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # ---- Load all tables ----
    profiles = read_csv(inp / "dataset - seller_profile.csv")
    activity = read_csv(inp / "dataset - seller_activity.csv")
    catalogue = read_csv(inp / "dataset - seller_catalogue.csv")
    contacts = read_csv(inp / "dataset - seller_contact_book.csv")
    calls = read_csv(inp / "dataset - buyer_seller_calls.csv")
    reviews_low = read_csv(inp / "dataset - seller_low_rating_reviews.csv")
    trends = read_csv(inp / "dataset - seller_monthly_weekly_trends.csv")
    ratings = read_csv(inp / "dataset - seller_ratings.csv")
    tickets = read_csv(inp / "dataset - seller_tickets.csv")
    transactions = read_csv(inp / "dataset - seller_transactions.csv")

    # ---- Index by seller_id ----
    # Activity: group by seller_id → period_days
    act_by_seller: Dict[str, Dict[int, Dict]] = defaultdict(dict)
    for r in activity:
        act_by_seller[r["seller_id"]][si(r["period_days"])] = r

    # Catalogue: group by seller_id
    cat_by_seller: Dict[str, List[Dict]] = defaultdict(list)
    for r in catalogue:
        cat_by_seller[r["seller_id"]].append(r)

    # Contact book: group by seller_id
    con_by_seller: Dict[str, List[Dict]] = defaultdict(list)
    for r in contacts:
        con_by_seller[r["seller_id"]].append(r)

    # Calls: group by seller_id
    call_by_seller: Dict[str, List[Dict]] = defaultdict(list)
    for r in calls:
        call_by_seller[r["seller_id"]].append(r)

    # Reviews: group by seller_id
    rev_by_seller: Dict[str, List[Dict]] = defaultdict(list)
    for r in reviews_low:
        rev_by_seller[r["seller_id"]].append(r)

    # Trends (monthly only): group by seller_id
    trend_by_seller: Dict[str, List[Dict]] = defaultdict(list)
    for r in trends:
        if r.get("period_type") == "Monthly":
            trend_by_seller[r["seller_id"]].append(r)

    # Ratings: index by seller_id
    rat_by_seller: Dict[str, Dict] = {}
    for r in ratings:
        rat_by_seller[r["seller_id"]] = r

    # Tickets: group by seller_id
    tkt_by_seller: Dict[str, List[Dict]] = defaultdict(list)
    for r in tickets:
        tkt_by_seller[r["seller_id"]].append(r)

    # Transactions: group by seller_id
    txn_by_seller: Dict[str, List[Dict]] = defaultdict(list)
    for r in transactions:
        txn_by_seller[r["seller_id"]].append(r)

    # ---- Build features per seller ----
    features_list: List[Dict[str, Any]] = []

    for profile in profiles:
        sid = profile["seller_id"]
        f: Dict[str, Any] = {"seller_id": sid}

        # --- Profile features ---
        f["city"] = profile.get("city", "")
        f["state"] = profile.get("state", "")
        f["business_type"] = profile.get("business_type", "")
        f["turnover_range"] = profile.get("turnover_range", "")
        f["package"] = profile.get("package", "")
        f["member_since_years"] = si(profile.get("member_since_years"))
        f["client_since_years"] = si(profile.get("client_since_years"))
        f["gst_verified"] = si(profile.get("gst_verified"))
        f["cin_verified"] = si(profile.get("cin_verified"))
        f["address_verified"] = si(profile.get("address_verified"))
        f["verification_score"] = si(profile.get("verification_score"))
        f["awards_count"] = si(profile.get("awards_count"))
        f["trustseal_active"] = si(profile.get("trustseal_active"))
        f["trustseal_days_remaining"] = si(profile.get("trustseal_days_remaining"))
        f["bs_conflict_tickets"] = si(profile.get("bs_conflict_tickets"))

        # Subscription dates
        sub_end = profile.get("subscription_end_date", "")
        f["days_to_renewal"] = days_until(sub_end) if sub_end else None

        # --- Activity features (7d, 30d, 90d) ---
        act = act_by_seller.get(sid, {})
        for period in [7, 30, 90]:
            a = act.get(period, {})
            prefix = f"act_{period}d_"
            f[prefix + "bl_active"] = si(a.get("bl_active"))
            f[prefix + "total_enquiries"] = si(a.get("total_enquiries"))
            f[prefix + "total_calls"] = si(a.get("total_calls"))
            f[prefix + "call_pickup_pct"] = sf(a.get("call_pickup_pct"))
            f[prefix + "callbacks"] = si(a.get("callbacks"))
            f[prefix + "replies"] = si(a.get("replies"))
            f[prefix + "conn_attempted"] = si(a.get("conn_attempted"))
            f[prefix + "conn_connected"] = si(a.get("conn_connected"))
            f[prefix + "products_added"] = si(a.get("products_added"))
            f[prefix + "products_deactivated"] = si(a.get("products_deactivated"))
            f[prefix + "lead_mgr_active_days"] = si(a.get("lead_mgr_active_days"))
            f[prefix + "catalogue_score"] = sf(a.get("catalogue_score"))

        # --- Decay signals (7d vs 90d) ---
        a7 = act.get(7, {})
        a90 = act.get(90, {})
        pickup_7 = sf(a7.get("call_pickup_pct"))
        pickup_90 = sf(a90.get("call_pickup_pct"))
        f["pickup_decay"] = round(pickup_90 - pickup_7, 4) if pickup_90 else 0
        enq_7 = si(a7.get("total_enquiries"))
        enq_90 = si(a90.get("total_enquiries"))
        f["enquiry_velocity_ratio"] = round(enq_7 / max(enq_90 / 12.86, 1), 4)  # 90d/7 ≈ 12.86
        cat_7 = sf(a7.get("catalogue_score"))
        cat_90 = sf(a90.get("catalogue_score"))
        f["catalogue_score_change"] = round(cat_7 - cat_90, 2)

        conn_att_90 = si(a90.get("conn_attempted"))
        conn_con_90 = si(a90.get("conn_connected"))
        f["connection_rate_90d"] = round(conn_con_90 / max(conn_att_90, 1), 4)

        # --- Catalogue features ---
        cats = cat_by_seller.get(sid, [])
        f["total_mcats"] = len(cats)
        f["total_products"] = sum(si(c.get("total_products")) for c in cats)
        f["total_bl_purchased_6m"] = sum(si(c.get("bl_purchased_6m")) for c in cats)
        rank_scores = [si(c.get("rank_score")) for c in cats if c.get("rank_score")]
        f["avg_rank_score"] = round(sum(rank_scores) / max(len(rank_scores), 1), 2)

        # --- Contact book features ---
        cons = con_by_seller.get(sid, [])
        f["total_contacts"] = len(cons)
        cat_counts = Counter(c.get("contact_category", "") for c in cons)
        f["contacts_hot"] = cat_counts.get("Hot", 0)
        f["contacts_warm"] = cat_counts.get("Warm", 0)
        f["contacts_cold"] = cat_counts.get("Cold", 0)
        f["contacts_converted"] = cat_counts.get("Converted", 0)
        f["contacts_inactive"] = cat_counts.get("Inactive", 0)
        status_counts = Counter(c.get("contact_status", "") for c in cons)
        f["contacts_active"] = status_counts.get("Active", 0)
        f["contacts_status_inactive"] = status_counts.get("Inactive", 0)
        f["contacts_status_converted"] = status_counts.get("Converted", 0)
        untouched = sum(1 for c in cons if c.get("untouched_flag") == "1")
        f["untouched_pct"] = round(untouched / max(len(cons), 1), 4)
        unread = sum(si(c.get("unread_message_count")) for c in cons)
        f["total_unread_messages"] = unread
        starred = sum(1 for c in cons if c.get("starred_flag") == "1")
        f["starred_pct"] = round(starred / max(len(cons), 1), 4)
        rated = [sf(c.get("buyer_rating_by_seller")) for c in cons if c.get("buyer_rating_by_seller")]
        f["avg_buyer_rating_by_seller"] = round(sum(rated) / max(len(rated), 1), 2)
        hot_warm_pct = (cat_counts.get("Hot", 0) + cat_counts.get("Warm", 0)) / max(len(cons), 1)
        f["hot_warm_contact_pct"] = round(hot_warm_pct, 4)

        # --- Call features ---
        seller_calls = call_by_seller.get(sid, [])
        f["total_calls_recorded"] = len(seller_calls)
        intent_counts = Counter(c.get("seller_intent", "") for c in seller_calls)
        total_intents = max(len(seller_calls), 1)
        f["intent_high_interest_pct"] = round(intent_counts.get("High Interest", 0) / total_intents, 4)
        f["intent_moderate_pct"] = round(intent_counts.get("Moderate Interest", 0) / total_intents, 4)
        f["intent_low_interest_pct"] = round(intent_counts.get("Low Interest", 0) / total_intents, 4)
        f["intent_considering_cancel_pct"] = round(intent_counts.get("Considering Cancellation", 0) / total_intents, 4)
        f["intent_disengaged_pct"] = round(intent_counts.get("Disengaged", 0) / total_intents, 4)
        f["intent_renewal_pct"] = round(intent_counts.get("Interested in Renewal", 0) / total_intents, 4)
        f["negative_intent_pct"] = round(
            (intent_counts.get("Considering Cancellation", 0) + intent_counts.get("Disengaged", 0)) / total_intents, 4
        )
        durations = [si(c.get("call_duration_mins")) for c in seller_calls]
        f["avg_call_duration"] = round(sum(durations) / max(len(durations), 1), 2)

        # --- Review / Rating features ---
        rat = rat_by_seller.get(sid, {})
        f["overall_rating"] = sf(rat.get("overall_rating"))
        f["total_reviews"] = si(rat.get("total_reviews"))
        f["five_star_pct"] = sf(rat.get("five_star_pct"))
        f["one_star_pct"] = sf(rat.get("one_star_pct"))
        f["response_satisfaction_pct"] = sf(rat.get("response_satisfaction_pct"))
        f["quality_satisfaction_pct"] = sf(rat.get("quality_satisfaction_pct"))
        f["delivery_satisfaction_pct"] = sf(rat.get("delivery_satisfaction_pct"))
        req_90 = si(rat.get("reviews_requested_90d"))
        rec_90 = si(rat.get("reviews_received_90d"))
        f["review_response_rate_90d"] = round(rec_90 / max(req_90, 1), 4)

        # Low-rating reviews
        low_revs = rev_by_seller.get(sid, [])
        f["low_rating_review_count"] = len(low_revs)
        responded = sum(1 for r in low_revs if r.get("response_by_seller", "").lower() == "yes")
        f["low_review_response_rate"] = round(responded / max(len(low_revs), 1), 4)

        # --- Ticket features ---
        tkts = tkt_by_seller.get(sid, [])
        f["total_tickets"] = len(tkts)
        f["open_tickets"] = sum(1 for t in tkts if t.get("status") == "Open")
        f["high_risk_tickets"] = sum(1 for t in tkts if t.get("risk_level") == "High")
        f["conflict_tickets"] = sum(1 for t in tkts if t.get("ticket_type") == "Buyer-Supplier Conflict")
        f["deactivation_tickets"] = sum(1 for t in tkts if t.get("ticket_type") == "Service Deactivation")
        res_days = [si(t.get("resolution_days")) for t in tkts if t.get("resolution_days")]
        f["avg_resolution_days"] = round(sum(res_days) / max(len(res_days), 1), 1)

        # --- Transaction features ---
        txns = txn_by_seller.get(sid, [])
        f["total_transactions"] = len(txns)
        f["cancelled_transactions"] = sum(1 for t in txns if t.get("is_cancellation") == "1")
        f["cancellation_rate"] = round(
            sum(1 for t in txns if t.get("is_cancellation") == "1") / max(len(txns), 1), 4
        )
        f["total_spend"] = sum(sf(t.get("total_amount_rs")) for t in txns if t.get("is_cancellation") != "1")
        services = set(t.get("service_name", "") for t in txns if t.get("is_cancellation") != "1" and t.get("status") == "Approved")
        f["unique_services_purchased"] = len(services)

        # --- Trend features (monthly) ---
        monthly = sorted(trend_by_seller.get(sid, []), key=lambda x: (x.get("year", ""), x.get("month", "")))
        if len(monthly) >= 3:
            recent_3 = monthly[-3:]
            older = monthly[:-3] if len(monthly) > 3 else monthly[:1]
            avg_recent_bl = sum(si(m.get("buyleads")) for m in recent_3) / 3
            avg_older_bl = sum(si(m.get("buyleads")) for m in older) / max(len(older), 1)
            f["buylead_trend"] = round(avg_recent_bl - avg_older_bl, 2)
            avg_recent_enq = sum(si(m.get("enquiries")) for m in recent_3) / 3
            avg_older_enq = sum(si(m.get("enquiries")) for m in older) / max(len(older), 1)
            f["enquiry_trend"] = round(avg_recent_enq - avg_older_enq, 2)
            avg_recent_pickup = sum(sf(m.get("call_pickup_pct")) for m in recent_3) / 3
            avg_older_pickup = sum(sf(m.get("call_pickup_pct")) for m in older) / max(len(older), 1)
            f["pickup_trend"] = round(avg_recent_pickup - avg_older_pickup, 4)
            avg_recent_lms = sum(si(m.get("lms_active_days")) for m in recent_3) / 3
            avg_older_lms = sum(si(m.get("lms_active_days")) for m in older) / max(len(older), 1)
            f["lms_active_trend"] = round(avg_recent_lms - avg_older_lms, 2)
        else:
            f["buylead_trend"] = 0
            f["enquiry_trend"] = 0
            f["pickup_trend"] = 0
            f["lms_active_trend"] = 0

        # ============================
        # DERIVED CHURN LABEL
        # ============================
        churn_signals = 0
        # Signal 1: High negative intent in calls
        if f["negative_intent_pct"] > 0.30:
            churn_signals += 2
        elif f["negative_intent_pct"] > 0.15:
            churn_signals += 1
        # Signal 2: Service cancellations
        if f["cancellation_rate"] > 0.30:
            churn_signals += 2
        elif f["cancellation_rate"] > 0.15:
            churn_signals += 1
        # Signal 3: Service deactivation tickets
        if f["deactivation_tickets"] > 0:
            churn_signals += 2
        # Signal 4: Low call pickup and declining
        if f["act_30d_call_pickup_pct"] < 0.40:
            churn_signals += 1
        # Signal 5: Open conflict tickets
        if f["conflict_tickets"] > 1:
            churn_signals += 1
        # Signal 6: Low overall rating
        if f["overall_rating"] < 2.5:
            churn_signals += 1
        # Signal 7: Negative trends
        if f["buylead_trend"] < -20:
            churn_signals += 1
        # Signal 8: High untouched contacts
        if f["untouched_pct"] > 0.30:
            churn_signals += 1

        f["churn_signal_count"] = churn_signals
        f["churn_label"] = 1 if churn_signals >= 3 else 0

        features_list.append(f)

    # ---- Write output ----
    if not features_list:
        print("No features generated!")
        return

    fieldnames = list(features_list[0].keys())
    out_path = out / "seller_features.csv"
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in features_list:
            writer.writerow(row)

    churned = sum(1 for f in features_list if f["churn_label"] == 1)
    print(json.dumps({
        "output": str(out_path),
        "sellers": len(features_list),
        "features": len(fieldnames),
        "churned": churned,
        "churn_rate": f"{churned / len(features_list) * 100:.1f}%"
    }, indent=2))


if __name__ == "__main__":
    main()
