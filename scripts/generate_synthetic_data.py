#!/usr/bin/env python3
"""
Rebuild supporting CSVs from the three real IndiaMART data files:
  - data/csv/dataset - seller_transactions.csv  (integer seller IDs, real service names)
  - data/csv/dataset - seller_buyer_chat.csv     (chat + call activity)
  - data/csv/dataset - seller_contact_book.csv   (contact pipeline data)

Produces:
  data/csv/dataset - seller_profile.csv          (integer IDs, real package names)
  data/csv/dataset - seller_monthly_weekly_trends.csv
  data/csv/dataset - seller_catalogue.csv
  data/csv/dataset - seller_ratings.csv
  data/csv/dataset - buyer_seller_calls.csv
  data/csv/dataset - seller_low_rating_reviews.csv
  data/csv/dataset - seller_tickets.csv

Does NOT touch seller_transactions.csv, seller_buyer_chat.csv, or seller_contact_book.csv.

Usage:
    python scripts/generate_synthetic_data.py
"""

from __future__ import annotations

import csv
import json
import math
import random
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

TODAY = date(2025, 12, 15)

# ── IndiaMART standard subscription tiers ───────────────────────────────────
SUBSCRIPTION_SERVICES = {
    "IM InstaPlatinum", "MDC Pro", "PRIME Package",
    "STAR Package", "STAR-MAXI Package", "VE-Gold",
}
ADD_ON_SERVICES = {"BuyLead Credits", "Domain Service", "Trust Seal", "TS Service"}

# Package → approximate annual value (INR)
PKG_VALUES = {
    "VE-Gold": 18000,
    "PRIME Package": 35000,
    "MDC Pro": 55000,
    "STAR Package": 75000,
    "STAR-MAXI Package": 110000,
    "IM InstaPlatinum": 160000,
}
PKG_TIER = {k: i for i, k in enumerate(PKG_VALUES)}  # lower = lower tier

# ── Name/location pools (for generated profile fields) ──────────────────────
FIRST_NAMES = [
    "Ramesh", "Suresh", "Mahesh", "Dinesh", "Rajesh", "Ganesh", "Naresh", "Mukesh",
    "Rakesh", "Hitesh", "Kamlesh", "Bhavesh", "Dilip", "Harish", "Girish", "Manish",
    "Ashish", "Santosh", "Vijay", "Sanjay", "Ajay", "Abhay", "Uday", "Bhushan",
    "Priya", "Sunita", "Anita", "Kavita", "Meena", "Rekha", "Nisha", "Bharti",
]
LAST_NAMES = [
    "Patel", "Shah", "Gupta", "Sharma", "Verma", "Singh", "Kumar", "Agarwal",
    "Jain", "Mehta", "Kapoor", "Srivastava", "Mishra", "Yadav", "Tiwari",
    "Pandey", "Chauhan", "Nair", "Reddy", "Iyer", "Pillai", "Naik", "Rao",
]
COMPANY_SUFFIXES = [
    "Industries", "Enterprises", "Traders", "Solutions", "Corp",
    "Manufacturing", "Exports", "Group", "Associates", "Brothers",
]
CITIES_STATES = [
    ("Mumbai", "Maharashtra"), ("Pune", "Maharashtra"), ("Nashik", "Maharashtra"),
    ("Delhi", "Delhi"), ("Noida", "Uttar Pradesh"), ("Gurgaon", "Haryana"),
    ("Bangalore", "Karnataka"), ("Chennai", "Tamil Nadu"), ("Hyderabad", "Telangana"),
    ("Ahmedabad", "Gujarat"), ("Surat", "Gujarat"), ("Rajkot", "Gujarat"),
    ("Kolkata", "West Bengal"), ("Jaipur", "Rajasthan"), ("Indore", "Madhya Pradesh"),
    ("Ludhiana", "Punjab"), ("Coimbatore", "Tamil Nadu"), ("Vadodara", "Gujarat"),
    ("Nagpur", "Maharashtra"), ("Chandigarh", "Punjab"), ("Bhopal", "Madhya Pradesh"),
    ("Kanpur", "Uttar Pradesh"), ("Agra", "Uttar Pradesh"), ("Faridabad", "Haryana"),
    ("Patna", "Bihar"), ("Lucknow", "Uttar Pradesh"), ("Kochi", "Kerala"),
    ("Visakhapatnam", "Andhra Pradesh"), ("Bhubaneswar", "Odisha"), ("Raipur", "Chhattisgarh"),
]
BUSINESS_TYPES = ["Manufacturer", "Trader", "Exporter", "Distributor", "Service Provider", "Wholesaler"]
TURNOVER_RANGES = ["Below 1 Cr", "1-5 Cr", "5-25 Cr", "25-100 Cr", "Above 100 Cr"]

TICKET_TYPES = [
    "Billing Issue", "Product Quality", "Delivery Delay", "Technical Support",
    "Account Access", "Lead Quality", "Subscription Query", "Refund Request",
    "Buyer-Supplier Conflict", "Service Deactivation",
]
REVIEW_TEXTS = [
    "Product quality is good but delivery was delayed.",
    "Not as described in catalogue. Very disappointed.",
    "Excellent service and quick response. Highly recommend.",
    "Poor communication from the seller. Hard to reach.",
    "Good quality products but packaging needs improvement.",
    "Fast delivery and exactly as described. Will order again.",
    "Price is high compared to market. But quality is acceptable.",
    "Seller did not respond to my calls. Had to escalate.",
    "Great experience overall. Professional and reliable.",
    "Product has defects. Seller refused to replace.",
]

BUYER_NAMES = [
    "Rajesh Kumar", "Priya Sharma", "Amit Patel", "Sunita Verma", "Vikram Singh",
    "Meena Gupta", "Suresh Nair", "Anita Reddy", "Ravi Chandrasekhar", "Pooja Iyer",
    "Mohit Agarwal", "Kavita Joshi", "Deepak Malhotra", "Nisha Kapoor", "Sanjeev Rao",
    "Bharti Mehta", "Vinod Shah", "Rekha Sinha", "Ajay Mishra", "Seema Tiwari",
]


# ── Utilities ────────────────────────────────────────────────────────────────

def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict], fieldnames: List[str] = None) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fns = fieldnames or list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  Wrote {len(rows):,} rows -> {path}")


def sf(v, d=0.0):
    try:
        return float(v) if v not in ("", None, "None") else d
    except Exception:
        return d


def si(v, d=0):
    try:
        return int(float(v)) if v not in ("", None, "None") else d
    except Exception:
        return d


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def seeded(seller_id: str, salt: str = "") -> random.Random:
    key = int(seller_id) * 31337 + sum(ord(c) for c in salt)
    return random.Random(key)


def parse_date(s: str) -> date | None:
    try:
        return datetime.fromisoformat(s[:10]).date()
    except Exception:
        return None


def fmt(d: date) -> str:
    return d.strftime("%Y-%m-%d")


# ── Step 1: derive seller info from transactions ─────────────────────────────

def derive_from_transactions(txns: List[Dict]) -> Dict[str, Dict]:
    """
    For each seller derive: package, subscription_end_date, total_spend,
    cancellation_rate, member_since_years, unique_services.
    """
    by_seller: Dict[str, List[Dict]] = defaultdict(list)
    for t in txns:
        by_seller[t["seller_id"]].append(t)

    result = {}
    for sid, st in by_seller.items():
        # Latest approved subscription service → package name
        subs = [t for t in st if t["service_name"] in SUBSCRIPTION_SERVICES and t["status"] == "Approved"]
        subs_sorted = sorted(subs, key=lambda x: x["created_date"], reverse=True)
        if subs_sorted:
            pkg = subs_sorted[0]["service_name"]
            # Subscription end ≈ last subscription date + 1 year
            last_sub_date = parse_date(subs_sorted[0]["created_date"])
            sub_end = last_sub_date + timedelta(days=365) if last_sub_date else TODAY + timedelta(days=180)
        else:
            # Fallback: use most common service as package
            service_counter = Counter(t["service_name"] for t in st if t["status"] == "Approved")
            pkg = service_counter.most_common(1)[0][0] if service_counter else "PRIME Package"
            sub_end = TODAY + timedelta(days=seeded(sid).randint(30, 365))

        # Dates
        dates = [parse_date(t["created_date"]) for t in st if parse_date(t["created_date"])]
        first_date = min(dates) if dates else TODAY - timedelta(days=365)
        member_since_years = max(1, (TODAY - first_date).days // 365)

        # Financial
        approved_non_cancel = [t for t in st if t["is_cancellation"] != "1" and t["status"] == "Approved"]
        total_spend = sum(sf(t["total_amount_rs"]) for t in approved_non_cancel)
        cancelled = sum(1 for t in st if t["is_cancellation"] == "1")
        cancel_rate = round(cancelled / max(len(st), 1), 4)
        unique_services = len(set(t["service_name"] for t in approved_non_cancel))

        result[sid] = {
            "seller_id": sid,
            "package": pkg,
            "subscription_end_date": fmt(sub_end),
            "total_spend": round(total_spend, 2),
            "cancellation_rate": cancel_rate,
            "member_since_years": member_since_years,
            "unique_services_purchased": unique_services,
        }
    return result


# ── Step 2: derive activity from chat ────────────────────────────────────────

def derive_from_chat(chats: List[Dict]) -> Dict[str, Any]:
    """
    Returns per-seller dict with:
      - monthly_trends: list of monthly aggregated metrics
      - act_30d_* features
      - overall call metrics
      - top_mcats: list of mcat names
    """
    by_seller: Dict[str, List[Dict]] = defaultdict(list)
    for c in chats:
        by_seller[c["seller_id"]].append(c)

    result = {}
    for sid, rows in by_seller.items():
        # ── Monthly trends ──
        monthly: Dict[str, Dict] = defaultdict(lambda: {
            "enq": 0, "bl": 0, "pns": 0, "reply": 0, "callback": 0,
            "calls_total": 0, "calls_answered": 0, "active_days": set(),
        })
        for r in rows:
            d = parse_date(r["message_date"])
            if not d:
                continue
            key = f"{d.year}-{d.month:02d}"
            m = monthly[key]
            mt = r.get("message_type", "")
            if mt == "ENQ":
                m["enq"] += 1
            elif mt == "BL":
                m["bl"] += 1
            elif mt == "PNS":
                m["pns"] += 1
            elif mt == "REPLY":
                m["reply"] += 1
            elif mt == "CALLBACK":
                m["callback"] += 1
            cs = r.get("call_status", "")
            if cs:
                m["calls_total"] += 1
                if cs == "Answered":
                    m["calls_answered"] += 1
            m["active_days"].add(d)

        # Sorted monthly trend
        sorted_months = sorted(monthly.keys())
        MONTH_NAMES = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        trends = []
        for key in sorted_months:
            yr, mo = key.split("-")
            m = monthly[key]
            calls_total = m["calls_total"]
            pickup = round(m["calls_answered"] / max(calls_total, 1), 3) if calls_total else 0.0
            trends.append({
                "year": yr,
                "month": str(int(mo)),
                "period_label": f"{MONTH_NAMES[int(mo)]} {yr}",
                "enquiries": m["enq"],
                "buyleads": m["bl"],
                "call_pickup_pct": pickup,
                "lms_active_days": len(m["active_days"]),
                "replies": m["reply"],
                "callbacks": m["callback"],
            })

        # ── Last 30-day activity ──
        cutoff_30 = TODAY - timedelta(days=30)
        recent = [r for r in rows if (d := parse_date(r["message_date"])) and d >= cutoff_30]
        calls_30 = [r for r in recent if r.get("call_status")]
        enq_30 = sum(1 for r in recent if r.get("message_type") == "ENQ")
        bl_30  = sum(1 for r in recent if r.get("message_type") == "BL")
        cb_30  = sum(1 for r in recent if r.get("message_type") == "CALLBACK")
        pickup_30 = round(
            sum(1 for r in calls_30 if r.get("call_status") == "Answered") / max(len(calls_30), 1), 3
        )

        # ── Negative intent: (unread ENQ/BL + missed calls) / (total ENQ/BL + total calls)
        # seller_responded=="1" only appears on seller-sent rows — buyer rows always have "" regardless.
        # Use message_read_status and call_status as the real signal instead.
        total_enq_bl = sum(1 for r in rows if r.get("message_type") in ("ENQ", "BL"))
        unread_enq   = sum(1 for r in rows if r.get("message_type") in ("ENQ", "BL")
                           and r.get("message_read_status") == "Unread")
        calls_all    = [r for r in rows if r.get("call_status")]
        missed_calls = sum(1 for r in calls_all
                           if r["call_status"] in ("Missed", "Not Reachable", "Busy", "Call Back Later"))
        neg_intent = round(
            (unread_enq + missed_calls) / max(total_enq_bl + len(calls_all), 1), 4
        )

        # ── Top product categories from chat ──
        mcat_counter = Counter(r["mcat_name"] for r in rows if r.get("mcat_name"))
        top_mcats = [m for m, _ in mcat_counter.most_common(5)]

        # ── Call details for buyer_seller_calls.csv ──
        call_rows = [r for r in rows if r.get("call_status") and r.get("call_duration_mins")]
        call_rows_sorted = sorted(call_rows, key=lambda x: x.get("message_date", ""), reverse=True)[:8]

        result[sid] = {
            "trends": trends,
            "act_30d_total_enquiries": enq_30,
            "act_30d_bl_active": bl_30,
            "act_30d_callbacks": cb_30,
            "act_30d_call_pickup_pct": pickup_30,
            "act_30d_catalogue_score": 0,  # derived later
            "negative_intent_pct": neg_intent,
            "top_mcats": top_mcats,
            "call_rows": call_rows_sorted,
        }
    return result


# ── Step 3: derive contact features ─────────────────────────────────────────

def derive_from_contacts(contacts: List[Dict]) -> Dict[str, Dict]:
    by_seller: Dict[str, List[Dict]] = defaultdict(list)
    for c in contacts:
        by_seller[c["seller_id"]].append(c)

    result = {}
    for sid, cons in by_seller.items():
        cat_counts = Counter(c.get("contact_category", "") for c in cons)
        status_counts = Counter(c.get("contact_status", "") for c in cons)
        untouched = sum(1 for c in cons if c.get("untouched_flag") == "1")
        untouched_pct = round(untouched / max(len(cons), 1), 4)
        converted = status_counts.get("Converted", 0)

        # Catalogue score proxy: % hot+warm contacts
        hot_warm = cat_counts.get("Hot", 0) + cat_counts.get("Warm", 0)
        cat_score = round((hot_warm / max(len(cons), 1)) * 100, 1)

        # Overall rating proxy: based on converted % and hot/warm
        base_rating = 2.5 + (converted / max(len(cons), 1)) * 1.5 + (hot_warm / max(len(cons), 1)) * 1.0
        overall_rating = round(clamp(base_rating, 1.0, 5.0), 2)

        # Top product categories from contact book
        mcat_counter = Counter(c.get("product_enquired", "") for c in cons if c.get("product_enquired"))

        result[sid] = {
            "total_contacts": len(cons),
            "contacts_hot": cat_counts.get("Hot", 0),
            "contacts_warm": cat_counts.get("Warm", 0),
            "contacts_cold": cat_counts.get("Cold", 0),
            "contacts_converted": converted,
            "contacts_inactive": cat_counts.get("Inactive", 0),
            "untouched_pct": untouched_pct,
            "act_30d_catalogue_score": cat_score,
            "overall_rating": overall_rating,
            "top_products": [p for p, _ in mcat_counter.most_common(5)],
        }
    return result


# ── Step 4: Build seller_profile.csv ─────────────────────────────────────────

def build_profiles(
    seller_ids: List[str],
    txn_data: Dict[str, Dict],
) -> List[Dict]:
    profiles = []
    for sid in seller_ids:
        r = seeded(sid)
        td = txn_data.get(sid, {})
        pkg = td.get("package", "PRIME Package")
        spend = td.get("total_spend", 0)

        # Derive turnover from total spend
        if spend > 300000:
            turnover = "Above 100 Cr"
        elif spend > 100000:
            turnover = "25-100 Cr"
        elif spend > 50000:
            turnover = "5-25 Cr"
        elif spend > 10000:
            turnover = "1-5 Cr"
        else:
            turnover = "Below 1 Cr"

        # Derive business type from package tier
        tier = PKG_TIER.get(pkg, 0)
        if tier >= 4:
            btype = r.choice(["Manufacturer", "Exporter"])
        elif tier >= 2:
            btype = r.choice(["Manufacturer", "Trader", "Distributor"])
        else:
            btype = r.choice(BUSINESS_TYPES)

        fname = r.choice(FIRST_NAMES)
        lname = r.choice(LAST_NAMES)
        city, state = r.choice(CITIES_STATES)

        # Verification score correlated to package tier
        gst = 1 if r.random() > (0.35 - tier * 0.05) else 0
        ver_score = min(100, 40 + tier * 12 + r.randint(0, 20))
        trust = 1 if r.random() > (0.6 - tier * 0.08) else 0

        profiles.append({
            "seller_id": sid,
            "seller_name": f"{fname} {lname}",
            "company_name": f"{lname} {r.choice(COMPANY_SUFFIXES)}",
            "city": city,
            "state": state,
            "business_type": btype,
            "turnover_range": turnover,
            "package": pkg,
            "member_since_years": td.get("member_since_years", r.randint(1, 8)),
            "subscription_end_date": td.get("subscription_end_date", fmt(TODAY + timedelta(days=r.randint(30, 365)))),
            "gst_verified": gst,
            "verification_score": ver_score,
            "trustseal_active": trust,
        })
    return profiles


# ── Step 5: Build seller_features.csv ────────────────────────────────────────

def build_features(
    profiles: List[Dict],
    txn_data: Dict[str, Dict],
    chat_data: Dict[str, Any],
    contact_data: Dict[str, Dict],
) -> List[Dict]:
    features = []
    for p in profiles:
        sid = p["seller_id"]
        td = txn_data.get(sid, {})
        cd = chat_data.get(sid, {})
        con = contact_data.get(sid, {})

        # Dates
        sub_end = p.get("subscription_end_date", "")
        dtr = (datetime.fromisoformat(sub_end).date() - TODAY).days if sub_end else None

        # Trends
        trends = cd.get("trends", [])
        monthly = sorted(trends, key=lambda x: (x["year"], x["month"].zfill(2)))
        if len(monthly) >= 3:
            recent3 = monthly[-3:]
            older = monthly[:-3] if len(monthly) > 3 else monthly[:1]
            avg_recent_bl  = sum(m["buyleads"] for m in recent3) / 3
            avg_older_bl   = sum(m["buyleads"] for m in older) / max(len(older), 1)
            avg_recent_enq = sum(m["enquiries"] for m in recent3) / 3
            avg_older_enq  = sum(m["enquiries"] for m in older) / max(len(older), 1)
            # Percentage change: positive = growing, negative = declining
            buylead_trend = round((avg_recent_bl  - avg_older_bl)  / max(avg_older_bl,  1) * 100, 1)
            enquiry_trend = round((avg_recent_enq - avg_older_enq) / max(avg_older_enq, 1) * 100, 1)
        else:
            buylead_trend = 0
            enquiry_trend = 0

        # Use contact-derived catalogue score
        cat_score = con.get("act_30d_catalogue_score", cd.get("act_30d_catalogue_score", 50))
        overall_rating = con.get("overall_rating", 3.5)

        features.append({
            "seller_id": sid,
            # Profile
            "city": p.get("city", ""),
            "state": p.get("state", ""),
            "business_type": p.get("business_type", ""),
            "turnover_range": p.get("turnover_range", ""),
            "package": p.get("package", ""),
            "member_since_years": p.get("member_since_years", 1),
            "gst_verified": p.get("gst_verified", 0),
            "verification_score": p.get("verification_score", 50),
            "trustseal_active": p.get("trustseal_active", 0),
            "days_to_renewal": dtr,
            # Activity (from chat)
            "act_30d_total_enquiries": cd.get("act_30d_total_enquiries", 0),
            "act_30d_bl_active": cd.get("act_30d_bl_active", 0),
            "act_30d_call_pickup_pct": cd.get("act_30d_call_pickup_pct", 0),
            "act_30d_callbacks": cd.get("act_30d_callbacks", 0),
            "act_30d_catalogue_score": cat_score,
            "negative_intent_pct": cd.get("negative_intent_pct", 0),
            # Contact book
            "total_contacts": con.get("total_contacts", 0),
            "contacts_converted": con.get("contacts_converted", 0),
            "contacts_hot": con.get("contacts_hot", 0),
            "contacts_warm": con.get("contacts_warm", 0),
            "untouched_pct": con.get("untouched_pct", 0),
            "hot_warm_contact_pct": round(
                (con.get("contacts_hot", 0) + con.get("contacts_warm", 0)) / max(con.get("total_contacts", 1), 1), 4
            ),
            # Ratings
            "overall_rating": overall_rating,
            "total_reviews": 0,  # filled by ratings file
            "low_rating_review_count": 0,
            "low_review_response_rate": 0,
            # Tickets
            "open_tickets": 0,
            "conflict_tickets": 0,
            "deactivation_tickets": 0,
            # Transactions
            "total_spend": td.get("total_spend", 0),
            "cancellation_rate": td.get("cancellation_rate", 0),
            "cancelled_transactions": 0,
            "unique_services_purchased": td.get("unique_services_purchased", 0),
            # Trends
            "buylead_trend": buylead_trend,
            "enquiry_trend": enquiry_trend,
            # Total products
            "total_products": 0,  # filled from catalogue
        })
    return features


# ── Step 6: Build monthly/weekly trends CSV ──────────────────────────────────

def build_trends(seller_ids: List[str], chat_data: Dict[str, Any]) -> List[Dict]:
    rows = []
    for sid in seller_ids:
        cd = chat_data.get(sid, {})
        monthly = cd.get("trends", [])
        for m in monthly:
            rows.append({
                "seller_id": sid,
                "period_type": "Monthly",
                "year": m["year"],
                "month": m["month"],
                "period_label": m["period_label"],
                "enquiries": m["enquiries"],
                "buyleads": m["buyleads"],
                "call_pickup_pct": m["call_pickup_pct"],
                "lms_active_days": m["lms_active_days"],
                "replies": m["replies"],
                "callbacks": m["callbacks"],
            })
            # Generate 4 weekly rows from monthly totals
            r = seeded(sid, m["year"] + m["month"])
            for w in range(1, 5):
                rows.append({
                    "seller_id": sid,
                    "period_type": "Weekly",
                    "year": m["year"],
                    "month": m["month"],
                    "period_label": f"W{w} {m['period_label']}",
                    "enquiries": max(0, round(m["enquiries"] / 4 * r.uniform(0.6, 1.4))),
                    "buyleads": max(0, round(m["buyleads"] / 4 * r.uniform(0.6, 1.4))),
                    "call_pickup_pct": round(clamp(m["call_pickup_pct"] * r.uniform(0.85, 1.15), 0, 1), 3),
                    "lms_active_days": max(0, round(m["lms_active_days"] / 4 * r.uniform(0.5, 1.5))),
                    "replies": max(0, round(m["replies"] / 4 * r.uniform(0.6, 1.4))),
                    "callbacks": max(0, round(m["callbacks"] / 4 * r.uniform(0.5, 1.5))),
                })
    return rows


# ── Step 7: Build catalogue from chat mcat_names ────────────────────────────

def build_catalogue(seller_ids: List[str], chat_data: Dict[str, Any], contact_data: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for sid in seller_ids:
        r = seeded(sid)
        cd = chat_data.get(sid, {})
        con = contact_data.get(sid, {})

        # Merge top product categories from chat and contacts
        mcats = list(dict.fromkeys(cd.get("top_mcats", []) + con.get("top_products", [])))[:5]
        if not mcats:
            mcats = ["General Products"]

        for mcat in mcats:
            rows.append({
                "seller_id": sid,
                "mcat_name": mcat,
                "total_products": max(1, r.randint(2, 20)),
                "best_rank": str(r.randint(1, 150)),
                "bl_purchased_6m": r.randint(0, 25),
            })
    return rows


# ── Step 8: Build ratings from contact + chat signals ────────────────────────

def build_ratings(profiles: List[Dict], contact_data: Dict[str, Dict], chat_data: Dict[str, Any]) -> List[Dict]:
    rows = []
    for p in profiles:
        sid = p["seller_id"]
        r = seeded(sid)
        con = contact_data.get(sid, {})
        cd = chat_data.get(sid, {})

        overall = con.get("overall_rating", 3.5)
        total_reviews = max(5, con.get("total_contacts", 10) // 3)
        rows.append({
            "seller_id": sid,
            "overall_rating": overall,
            "response_rating": round(clamp(overall + r.gauss(0, 0.3), 1, 5), 2),
            "product_quality_rating": round(clamp(overall + r.gauss(0, 0.4), 1, 5), 2),
            "total_reviews": total_reviews,
            "recent_30d_reviews": r.randint(0, 8),
        })
    return rows


# ── Step 9: Build buyer_seller_calls from chat call rows ─────────────────────

def build_calls(seller_ids: List[str], chat_data: Dict[str, Any]) -> List[Dict]:
    rows = []
    CALL_SUMMARIES = [
        "Discussed product specifications and pricing.",
        "Followed up on previous enquiry, sent catalogue.",
        "Buyer asked about bulk pricing and minimum order.",
        "Technical query on product certifications addressed.",
        "Buyer comparing with competitors, highlighted quality.",
        "Repeat buyer checking new product range.",
        "Complaint about delivery timeline, escalated.",
        "Discussed payment terms and credit period.",
        "New enquiry for custom order, sent quotation.",
        "Call about GST invoice requirement.",
    ]
    SELLER_INTENTS = ["interested", "negotiating", "call back later", "deal discussed", "sample request"]
    BUYER_INTENTS  = ["interested", "price inquiry", "sample request", "comparing", "not interested", "deal closed"]

    for sid in seller_ids:
        r = seeded(sid)
        cd = chat_data.get(sid, {})
        call_rows = cd.get("call_rows", [])
        for cr in call_rows:
            d = parse_date(cr.get("message_date", ""))
            if not d:
                continue
            rows.append({
                "seller_id": sid,
                "buyer_name": r.choice(BUYER_NAMES),
                "mcat_name": cr.get("mcat_name", "General Products"),
                "call_date": fmt(d),
                "call_duration_mins": si(cr.get("call_duration_mins", 0)),
                "call_summary": r.choice(CALL_SUMMARIES),
                "seller_intent": r.choice(SELLER_INTENTS),
                "buyer_intent": r.choice(BUYER_INTENTS),
            })
    return rows


# ── Step 10: Build tickets (consistent with integer IDs) ─────────────────────

def build_tickets(profiles: List[Dict]) -> List[Dict]:
    rows = []
    for p in profiles:
        sid = p["seller_id"]
        r = seeded(sid, "tickets")
        pkg = p.get("package", "PRIME Package")
        tier = PKG_TIER.get(pkg, 0)
        # Lower-tier sellers have more tickets
        n_tickets = r.choices([0, 1, 2, 3, 4], weights=[20 + tier * 5, 30, 25 - tier * 2, 15, 10])[0]
        for j in range(n_tickets):
            created = TODAY - timedelta(days=r.randint(0, 90))
            is_resolved = r.random() < 0.5
            is_deactivation = r.random() < 0.04  # ~4% chance
            is_conflict = r.random() < 0.06
            if is_deactivation:
                ttype = "Service Deactivation"
                risk = "Critical"
            elif is_conflict:
                ttype = "Buyer-Supplier Conflict"
                risk = "High"
            else:
                ttype = r.choice(TICKET_TYPES[:8])
                risk = r.choices(["Low", "Medium", "High"], weights=[40, 40, 20])[0]
            rows.append({
                "seller_id": sid,
                "ticket_type": ttype,
                "status": "Resolved" if is_resolved else r.choice(["Open", "In Progress"]),
                "risk_level": risk,
                "created_date": fmt(created),
                "resolved_date": fmt(created + timedelta(days=r.randint(1, 14))) if is_resolved else "",
            })
    return rows


# ── Step 11: Build low-rating reviews ────────────────────────────────────────

def build_reviews(profiles: List[Dict], contact_data: Dict[str, Dict], chat_data: Dict[str, Any]) -> List[Dict]:
    rows = []
    for p in profiles:
        sid = p["seller_id"]
        r = seeded(sid, "reviews")
        con = contact_data.get(sid, {})
        cd = chat_data.get(sid, {})
        # Sellers with lower ratings get more low-rating reviews
        overall_rating = con.get("overall_rating", 3.5)
        n_reviews = max(0, round((4.0 - overall_rating) * 4 * r.uniform(0.5, 2.0)))
        mcats = cd.get("top_mcats", ["General Products"])
        for _ in range(n_reviews):
            review_date = TODAY - timedelta(days=r.randint(0, 180))
            rows.append({
                "seller_id": sid,
                "review_date": fmt(review_date),
                "rating": r.choices([1, 2, 3], weights=[30, 40, 30])[0],
                "review_text": r.choice(REVIEW_TEXTS),
                "product_name": r.choice(mcats) if mcats else "Product",
                "response_by_seller": r.choice(["Yes", "No", "No"]),
            })
    return rows


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    data_dir = Path("data/csv")

    print("Reading real data files...")
    txns = read_csv(data_dir / "dataset - seller_transactions.csv")
    chats = read_csv(data_dir / "dataset - seller_buyer_chat.csv")
    contacts = read_csv(data_dir / "dataset - seller_contact_book.csv")

    print(f"  Transactions: {len(txns)} rows, {len(set(t['seller_id'] for t in txns))} sellers")
    print(f"  Chat:         {len(chats)} rows")
    print(f"  Contacts:     {len(contacts)} rows")

    # Derive from real sources
    print("\nDeriving from real data...")
    txn_data    = derive_from_transactions(txns)
    chat_data   = derive_from_chat(chats)
    contact_data = derive_from_contacts(contacts)

    # Seller ID list (integer, from transactions — authoritative)
    seller_ids = sorted(txn_data.keys(), key=lambda x: int(x))
    print(f"  Sellers: {len(seller_ids)} ({seller_ids[0]}..{seller_ids[-1]})")

    # Build all CSVs
    print("\nBuilding CSVs...")
    profiles  = build_profiles(seller_ids, txn_data)
    features  = build_features(profiles, txn_data, chat_data, contact_data)
    trends    = build_trends(seller_ids, chat_data)
    catalogue = build_catalogue(seller_ids, chat_data, contact_data)
    ratings   = build_ratings(profiles, contact_data, chat_data)
    calls     = build_calls(seller_ids, chat_data)
    tickets   = build_tickets(profiles)
    reviews   = build_reviews(profiles, contact_data, chat_data)

    # Update features with catalogue/ticket/review info
    cat_totals = defaultdict(int)
    for c in catalogue:
        cat_totals[c["seller_id"]] += si(c.get("total_products", 0))
    tkt_open = Counter()
    tkt_conflict = Counter()
    tkt_deact = Counter()
    for t in tickets:
        if t["status"] in ("Open", "In Progress"):
            tkt_open[t["seller_id"]] += 1
        if t["ticket_type"] == "Buyer-Supplier Conflict":
            tkt_conflict[t["seller_id"]] += 1
        if t["ticket_type"] == "Service Deactivation":
            tkt_deact[t["seller_id"]] += 1
    rev_count = Counter(rv["seller_id"] for rv in reviews)
    rev_responded = Counter(rv["seller_id"] for rv in reviews if rv.get("response_by_seller") == "Yes")

    feat_idx = {f["seller_id"]: f for f in features}
    for sid in seller_ids:
        f = feat_idx[sid]
        f["total_products"] = cat_totals.get(sid, 0)
        f["open_tickets"] = tkt_open.get(sid, 0)
        f["conflict_tickets"] = tkt_conflict.get(sid, 0)
        f["deactivation_tickets"] = tkt_deact.get(sid, 0)
        f["low_rating_review_count"] = rev_count.get(sid, 0)
        f["low_review_response_rate"] = round(
            rev_responded.get(sid, 0) / max(rev_count.get(sid, 1), 1), 4
        )

    # Write data/csv files
    write_csv(data_dir / "dataset - seller_profile.csv", profiles)
    write_csv(data_dir / "dataset - seller_monthly_weekly_trends.csv", trends)
    write_csv(data_dir / "dataset - seller_catalogue.csv", catalogue)
    write_csv(data_dir / "dataset - seller_ratings.csv", ratings)
    write_csv(data_dir / "dataset - buyer_seller_calls.csv", calls)
    write_csv(data_dir / "dataset - seller_tickets.csv", tickets)
    write_csv(data_dir / "dataset - seller_low_rating_reviews.csv", reviews)

    # Write outputs/real/seller_features.csv
    out_dir = Path("outputs/real")
    write_csv(out_dir / "seller_features.csv", features)

    print(f"\nDone. {len(seller_ids)} sellers, IDs {seller_ids[0]}..{seller_ids[-1]}")
    print("Next: python scripts/score_real_data.py && python scripts/export_real_dashboard.py")


if __name__ == "__main__":
    main()
