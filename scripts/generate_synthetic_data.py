#!/usr/bin/env python3
"""
Generate a synthetic B2B marketplace churn dataset ecosystem.

The generator is intentionally deterministic with --seed and dependency-light.
It uses Faker when available, then falls back to built-in synthetic names.
CSV is always supported. Parquet is optional when pandas/pyarrow are installed.
SQL output is capped by --sql-max-rows so demos do not create huge SQL files.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

try:
    from faker import Faker  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Faker = None


CATEGORIES = [
    "Industrial Pumps",
    "Packaging Machines",
    "Solar Water Heaters",
    "Plastic Granules",
    "Ladies Kurtis",
    "Steel Pipes",
    "Electrical Panels",
    "Pharmaceutical Chemicals",
    "Office Furniture",
    "Food Processing Machines",
]

CITIES = [
    ("Mumbai", "Maharashtra", "West"),
    ("Pune", "Maharashtra", "West"),
    ("Delhi", "Delhi", "North"),
    ("Jaipur", "Rajasthan", "North"),
    ("Ahmedabad", "Gujarat", "West"),
    ("Bengaluru", "Karnataka", "South"),
    ("Chennai", "Tamil Nadu", "South"),
    ("Hyderabad", "Telangana", "South"),
    ("Kolkata", "West Bengal", "East"),
    ("Lucknow", "Uttar Pradesh", "North"),
]

INDUSTRIES = [
    "Construction",
    "Manufacturing",
    "Retail",
    "Textiles",
    "Pharma",
    "Agriculture",
    "Hospitality",
    "Education",
    "Government",
    "Export Trading",
]

PLAN_VALUES = {
    "free": 0,
    "basic": 18000,
    "premium": 45000,
    "premium_plus": 75000,
    "enterprise": 135000,
}

SCALE_PRESETS = {
    "demo": {"sellers": 500, "buyers": 3000, "inquiries": 20000, "contactbook": 8000},
    "hackathon": {"sellers": 10000, "buyers": 50000, "inquiries": 1000000, "contactbook": 150000},
}


@dataclass
class Seller:
    seller_id: str
    category: str
    city: str
    state: str
    region: str
    tier: str
    archetype: str
    onboarding_date: date
    response_rate: float
    avg_response_minutes: float
    product_count: int
    catalog_quality_score: float
    lead_utilization_score: float
    gst_verified: bool
    trust_score: float
    churn_label: int
    churn_risk_score: float


@dataclass
class Buyer:
    buyer_id: str
    industry: str
    region: str
    activity_level: str
    inquiry_frequency: float
    average_order_value: float
    engagement_score: float
    repeat_interaction_score: float
    churn_label: int


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def logistic(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def weighted_choice(rng: random.Random, items: Sequence[tuple[str, float]]) -> str:
    total = sum(weight for _, weight in items)
    pick = rng.random() * total
    running = 0.0
    for item, weight in items:
        running += weight
        if pick <= running:
            return item
    return items[-1][0]


def seasonal_multiplier(day: date, category: str) -> float:
    month = day.month
    multiplier = 1.0
    if month in (10, 11):
        multiplier += 0.28  # festive demand
    if month in (3, 6, 9, 12):
        multiplier += 0.14  # quarter-end procurement
    if category in {"Solar Water Heaters", "Electrical Panels"} and month in (3, 4, 5):
        multiplier += 0.18
    if category in {"Construction", "Industrial Pumps", "Steel Pipes"} and month in (7, 8):
        multiplier -= 0.12
    return max(0.55, multiplier)


def maybe_company(fake: Optional[object], rng: random.Random, idx: int) -> str:
    if fake is not None:
        return fake.company()
    suffix = rng.choice(["Industries", "Traders", "Enterprises", "Impex", "Works"])
    return f"Demo {idx:05d} {suffix}"


def generate_sellers(count: int, rng: random.Random, fake: Optional[object], today: date) -> List[Seller]:
    sellers: List[Seller] = []
    archetypes = [
        ("high_performer", 0.14),
        ("healthy", 0.39),
        ("at_risk", 0.22),
        ("premium_at_risk", 0.09),
        ("dormant", 0.08),
        ("new", 0.08),
    ]
    tiers = [
        ("free", 0.16),
        ("basic", 0.26),
        ("premium", 0.34),
        ("premium_plus", 0.18),
        ("enterprise", 0.06),
    ]
    for i in range(1, count + 1):
        archetype = weighted_choice(rng, archetypes)
        tier = weighted_choice(rng, tiers)
        if archetype == "premium_at_risk":
            tier = weighted_choice(rng, [("premium", 0.60), ("premium_plus", 0.32), ("enterprise", 0.08)])
        city, state, region = rng.choice(CITIES)
        category = rng.choice(CATEGORIES)

        tenure_days = rng.randint(20, 1800) if archetype == "new" else rng.randint(180, 3000)
        onboarding = today - timedelta(days=tenure_days)

        if archetype == "high_performer":
            response_rate = rng.uniform(0.82, 0.98)
            avg_response = rng.uniform(8, 55)
            lead_util = rng.uniform(76, 98)
            catalog_quality = rng.uniform(78, 98)
        elif archetype == "healthy":
            response_rate = rng.uniform(0.62, 0.88)
            avg_response = rng.uniform(35, 180)
            lead_util = rng.uniform(55, 84)
            catalog_quality = rng.uniform(58, 86)
        elif archetype == "dormant":
            response_rate = rng.uniform(0.05, 0.35)
            avg_response = rng.uniform(720, 4800)
            lead_util = rng.uniform(4, 32)
            catalog_quality = rng.uniform(18, 55)
        else:
            response_rate = rng.uniform(0.25, 0.60)
            avg_response = rng.uniform(180, 1400)
            lead_util = rng.uniform(18, 58)
            catalog_quality = rng.uniform(35, 72)

        if archetype == "new":
            response_rate = rng.uniform(0.40, 0.78)
            avg_response = rng.uniform(50, 480)
            lead_util = rng.uniform(35, 75)
            catalog_quality = rng.uniform(42, 82)

        product_count = max(1, int(rng.paretovariate(2.0) * rng.randint(4, 22)))
        gst_verified = rng.random() < (0.84 if tier in {"premium", "premium_plus", "enterprise"} else 0.58)
        trust_score = clamp(
            0.35 * catalog_quality + 0.30 * lead_util + 25 * response_rate + (8 if gst_verified else -4) + rng.gauss(0, 5),
            1,
            99,
        )
        risk_latent = (
            0.30 * (1 - response_rate)
            + 0.22 * (1 - lead_util / 100)
            + 0.16 * (avg_response / 1440)
            + 0.14 * (1 - catalog_quality / 100)
            + (0.15 if archetype in {"at_risk", "premium_at_risk", "dormant"} else 0)
            - (0.12 if archetype == "high_performer" else 0)
            + rng.gauss(0, 0.05)
        )
        risk_score = clamp(100 * logistic((risk_latent - 0.52) * 5.0), 1, 99)
        churn_label = 1 if rng.random() < risk_score / 130 else 0

        sellers.append(
            Seller(
                seller_id=f"S{i:06d}",
                category=category,
                city=city,
                state=state,
                region=region,
                tier=tier,
                archetype=archetype,
                onboarding_date=onboarding,
                response_rate=round(response_rate, 4),
                avg_response_minutes=round(avg_response, 2),
                product_count=product_count,
                catalog_quality_score=round(catalog_quality, 2),
                lead_utilization_score=round(lead_util, 2),
                gst_verified=gst_verified,
                trust_score=round(trust_score, 2),
                churn_label=churn_label,
                churn_risk_score=round(risk_score, 2),
            )
        )
    return sellers


def generate_buyers(count: int, rng: random.Random) -> List[Buyer]:
    buyers: List[Buyer] = []
    levels = [
        ("highly_active", 0.12),
        ("active", 0.42),
        ("seasonal", 0.20),
        ("declining", 0.17),
        ("dormant", 0.09),
    ]
    for i in range(1, count + 1):
        level = weighted_choice(rng, levels)
        industry = rng.choice(INDUSTRIES)
        region = rng.choice(["North", "South", "East", "West"])
        if level == "highly_active":
            freq = rng.uniform(8, 32)
            engagement = rng.uniform(75, 98)
            repeat = rng.uniform(55, 95)
        elif level == "active":
            freq = rng.uniform(2, 12)
            engagement = rng.uniform(45, 82)
            repeat = rng.uniform(25, 72)
        elif level == "seasonal":
            freq = rng.uniform(1, 9)
            engagement = rng.uniform(35, 78)
            repeat = rng.uniform(18, 66)
        elif level == "declining":
            freq = rng.uniform(0.2, 4)
            engagement = rng.uniform(18, 55)
            repeat = rng.uniform(5, 40)
        else:
            freq = rng.uniform(0, 1.2)
            engagement = rng.uniform(1, 25)
            repeat = rng.uniform(0, 20)
        aov = round(rng.paretovariate(1.45) * rng.choice([8000, 15000, 30000, 60000]), 2)
        churn_prob = clamp((55 - engagement) / 80 + (1.5 - freq) / 20 + (0.20 if level == "declining" else 0), 0.02, 0.88)
        buyers.append(
            Buyer(
                buyer_id=f"B{i:07d}",
                industry=industry,
                region=region,
                activity_level=level,
                inquiry_frequency=round(freq, 2),
                average_order_value=aov,
                engagement_score=round(engagement, 2),
                repeat_interaction_score=round(repeat, 2),
                churn_label=1 if rng.random() < churn_prob else 0,
            )
        )
    return buyers


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Dict[str, object]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def sql_literal(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def write_sql_from_csv(csv_path: Path, sql_path: Path, table_name: str, max_rows: int) -> int:
    count = 0
    with csv_path.open("r", newline="", encoding="utf-8") as src, sql_path.open("w", encoding="utf-8") as out:
        reader = csv.DictReader(src)
        cols = reader.fieldnames or []
        out.write(f"-- Sample inserts for {table_name}. Capped for demo portability.\n")
        for row in reader:
            values = ", ".join(sql_literal(row[col]) for col in cols)
            out.write(f"INSERT INTO {table_name} ({', '.join(cols)}) VALUES ({values});\n")
            count += 1
            if count >= max_rows:
                break
    return count


def try_write_parquet(csv_path: Path, parquet_path: Path) -> bool:
    try:
        import pandas as pd  # type: ignore
    except Exception:
        return False
    try:
        df = pd.read_csv(csv_path)
        df.to_parquet(parquet_path, index=False)
        return True
    except Exception:
        return False


def sellers_to_rows(sellers: Sequence[Seller], fake: Optional[object], rng: random.Random) -> Iterable[Dict[str, object]]:
    for idx, seller in enumerate(sellers, start=1):
        yield {
            "seller_id": seller.seller_id,
            "business_name": maybe_company(fake, rng, idx),
            "business_category": seller.category,
            "city": seller.city,
            "state": seller.state,
            "region": seller.region,
            "subscription_tier": seller.tier,
            "archetype": seller.archetype,
            "onboarding_date": seller.onboarding_date.isoformat(),
            "response_rate": seller.response_rate,
            "avg_response_minutes": seller.avg_response_minutes,
            "product_count": seller.product_count,
            "catalog_quality_score": seller.catalog_quality_score,
            "lead_utilization_score": seller.lead_utilization_score,
            "gst_verified": seller.gst_verified,
            "trust_score": seller.trust_score,
            "churn_label": seller.churn_label,
            "churn_risk_score": seller.churn_risk_score,
        }


def buyers_to_rows(buyers: Sequence[Buyer]) -> Iterable[Dict[str, object]]:
    for buyer in buyers:
        yield {
            "buyer_id": buyer.buyer_id,
            "industry": buyer.industry,
            "region": buyer.region,
            "inquiry_frequency": buyer.inquiry_frequency,
            "average_order_value": buyer.average_order_value,
            "engagement_score": buyer.engagement_score,
            "repeat_interaction_score": buyer.repeat_interaction_score,
            "activity_level": buyer.activity_level,
            "churn_label": buyer.churn_label,
        }


def subscription_rows(sellers: Sequence[Seller], rng: random.Random, today: date) -> Iterable[Dict[str, object]]:
    for i, seller in enumerate(sellers, start=1):
        plan_value = PLAN_VALUES[seller.tier]
        if seller.tier == "free":
            continue
        days_to_renewal = rng.randint(-45, 365)
        if seller.archetype == "premium_at_risk":
            days_to_renewal = rng.randint(5, 90)
        renewal_date = today + timedelta(days=days_to_renewal)
        usage_score = clamp(
            0.52 * seller.lead_utilization_score + 0.28 * seller.catalog_quality_score + 20 * seller.response_rate + rng.gauss(0, 6),
            1,
            99,
        )
        adoption = clamp(usage_score + rng.gauss(-5 if seller.archetype in {"at_risk", "premium_at_risk"} else 4, 10), 1, 99)
        login_frequency = clamp(usage_score / 12 + rng.gauss(0, 1.8), 0, 14)
        churn_outcome = 1 if rng.random() < (seller.churn_risk_score / 125) else 0
        yield {
            "subscription_id": f"SUB{i:06d}",
            "seller_id": seller.seller_id,
            "plan_type": seller.tier,
            "renewal_date": renewal_date.isoformat(),
            "renewal_history": max(0, int((today - seller.onboarding_date).days / 365) + rng.choice([-1, 0, 0, 1])),
            "package_value": round(plan_value * rng.uniform(0.82, 1.35), 2),
            "usage_score": round(usage_score, 2),
            "feature_adoption_score": round(adoption, 2),
            "login_frequency": round(login_frequency, 2),
            "churn_outcome": churn_outcome,
        }


def daily_feature_rows(sellers: Sequence[Seller], rng: random.Random, today: date) -> Iterable[Dict[str, object]]:
    for seller in sellers:
        for offset in (90, 60, 30, 7, 0):
            as_of = today - timedelta(days=offset)
            decline_factor = (90 - offset) / 90 if seller.archetype in {"at_risk", "premium_at_risk", "dormant"} else 0
            received = max(0, int(rng.paretovariate(1.8) * (seller.lead_utilization_score / 9) * seasonal_multiplier(as_of, seller.category)))
            response_rate = clamp(seller.response_rate + (0.22 * (1 - decline_factor) if offset == 90 else 0) + rng.gauss(0, 0.04), 0, 1)
            handled = int(received * response_rate)
            yield {
                "seller_id": seller.seller_id,
                "as_of_date": as_of.isoformat(),
                "active_days_30d": max(0, int(seller.lead_utilization_score / 4 + rng.gauss(0, 3))),
                "inquiries_received_30d": received,
                "handled_leads_30d": handled,
                "response_rate_30d": round(response_rate, 4),
                "avg_response_minutes_30d": round(seller.avg_response_minutes * (1 + 0.6 * decline_factor) + rng.gauss(0, 20), 2),
                "conversion_rate_90d": round(clamp(0.04 + seller.trust_score / 260 + rng.gauss(0, 0.04), 0, 0.85), 4),
                "lead_utilization_score": round(clamp(seller.lead_utilization_score * (1 - 0.35 * decline_factor), 0, 100), 2),
                "catalog_quality_score": seller.catalog_quality_score,
                "catalog_staleness_days": max(0, int((100 - seller.catalog_quality_score) * 4 + rng.gauss(0, 20))),
                "buyer_repeat_count_90d": max(0, int(seller.trust_score / 12 + rng.gauss(0, 3))),
                "sentiment_avg_30d": round(clamp(rng.gauss(0.25 - 0.5 * decline_factor, 0.25), -1, 1), 3),
                "graph_degree_90d": max(0, int(received * rng.uniform(0.35, 0.85))),
            }


def contactbook_rows(
    count: int, sellers: Sequence[Seller], buyers: Sequence[Buyer], rng: random.Random, today: date
) -> Iterable[Dict[str, object]]:
    for i in range(1, count + 1):
        seller = rng.choice(sellers)
        buyer = rng.choice(buyers)
        strength = clamp((seller.trust_score + buyer.repeat_interaction_score) / 2 + rng.gauss(0, 14), 0, 100)
        days_since = int(clamp(160 - strength + rng.gauss(0, 35), 0, 730))
        yield {
            "contactbook_id": f"CB{i:08d}",
            "seller_id": seller.seller_id,
            "buyer_id": buyer.buyer_id,
            "interaction_frequency": round(max(0, rng.paretovariate(2.2) * strength / 28), 2),
            "last_contacted_at": (today - timedelta(days=days_since, hours=rng.randint(0, 23))).isoformat(),
            "relationship_strength": round(strength, 2),
            "repeat_business_score": round(clamp(strength + rng.gauss(0, 12), 0, 100), 2),
            "saved_contact_flag": rng.random() < strength / 115,
        }


def write_inquiries_and_messages(
    inquiries_path: Path,
    messages_path: Path,
    inquiry_count: int,
    sellers: Sequence[Seller],
    buyers: Sequence[Buyer],
    rng: random.Random,
    start_date: date,
    months: int,
) -> tuple[int, int]:
    inquiry_fields = [
        "transaction_id",
        "buyer_id",
        "seller_id",
        "transaction_type",
        "inquiry_timestamp",
        "response_timestamp",
        "response_sla",
        "conversion_status",
        "order_value",
        "payment_status",
        "communication_count",
        "negotiation_duration_hours",
        "lead_source",
    ]
    message_fields = [
        "message_id",
        "sender_id",
        "receiver_id",
        "txn_id",
        "message_type",
        "timestamp",
        "read_status",
        "response_latency_minutes",
        "sentiment",
        "escalation_flag",
    ]
    inquiries_path.parent.mkdir(parents=True, exist_ok=True)
    messages_path.parent.mkdir(parents=True, exist_ok=True)
    msg_id = 1
    inquiry_written = 0
    message_written = 0
    with inquiries_path.open("w", newline="", encoding="utf-8") as inquiry_file, messages_path.open("w", newline="", encoding="utf-8") as message_file:
        inquiry_writer = csv.DictWriter(inquiry_file, fieldnames=inquiry_fields)
        message_writer = csv.DictWriter(message_file, fieldnames=message_fields)
        inquiry_writer.writeheader()
        message_writer.writeheader()
        for i in range(1, inquiry_count + 1):
            seller = rng.choice(sellers)
            buyer = rng.choice(buyers)
            day = start_date + timedelta(days=rng.randint(0, months * 30))
            hour = rng.choices(range(24), weights=[1, 1, 1, 1, 1, 2, 4, 5, 7, 8, 8, 7, 6, 7, 8, 8, 7, 5, 4, 3, 2, 1, 1, 1])[0]
            inquiry_ts = datetime.combine(day, datetime.min.time()) + timedelta(hours=hour, minutes=rng.randint(0, 59))
            response_probability = seller.response_rate
            is_spam = rng.random() < 0.018
            responded = rng.random() < response_probability and not is_spam
            if responded:
                latency = max(1, rng.expovariate(1 / max(12, seller.avg_response_minutes)))
                response_ts = inquiry_ts + timedelta(minutes=latency)
                if latency <= 120:
                    sla = "within_2h"
                elif latency <= 1440:
                    sla = "same_day"
                else:
                    sla = "delayed"
            else:
                latency = None
                response_ts = None
                sla = "no_response"

            tx_type = weighted_choice(rng, [("ENQ", 0.66), ("BL", 0.17), ("C2C", 0.10), ("PNS", 0.07)])
            conversion_prob = clamp(0.04 + seller.trust_score / 260 + buyer.engagement_score / 350 - (0.25 if not responded else 0), 0.01, 0.75)
            status = "spam" if is_spam else ("converted" if rng.random() < conversion_prob else rng.choice(["abandoned", "pending"]))
            order_value = 0 if status == "spam" else round(buyer.average_order_value * rng.uniform(0.35, 2.8), 2)
            comm_count = 1 if not responded else max(2, int(rng.paretovariate(2.0) * rng.randint(2, 5)))
            transaction_id = f"T{i:010d}"
            inquiry_writer.writerow(
                {
                    "transaction_id": transaction_id,
                    "buyer_id": buyer.buyer_id,
                    "seller_id": seller.seller_id,
                    "transaction_type": tx_type,
                    "inquiry_timestamp": inquiry_ts.isoformat(sep=" "),
                    "response_timestamp": response_ts.isoformat(sep=" ") if response_ts else "",
                    "response_sla": sla,
                    "conversion_status": status,
                    "order_value": order_value,
                    "payment_status": "paid" if status == "converted" else ("not_applicable" if status == "spam" else rng.choice(["pending", "failed"])),
                    "communication_count": comm_count,
                    "negotiation_duration_hours": round(comm_count * rng.uniform(0.4, 9.5), 2),
                    "lead_source": weighted_choice(rng, [("search", 0.42), ("category", 0.20), ("paid_lead", 0.18), ("repeat_buyer", 0.15), ("whatsapp", 0.05)]),
                }
            )
            inquiry_written += 1

            message_writer.writerow(
                {
                    "message_id": f"M{msg_id:012d}",
                    "sender_id": buyer.buyer_id,
                    "receiver_id": seller.seller_id,
                    "txn_id": transaction_id,
                    "message_type": "inquiry",
                    "timestamp": inquiry_ts.isoformat(sep=" "),
                    "read_status": "read" if responded else rng.choice(["read", "unread"]),
                    "response_latency_minutes": "",
                    "sentiment": round(rng.gauss(0.18, 0.25), 3),
                    "escalation_flag": False,
                }
            )
            msg_id += 1
            message_written += 1

            if responded and response_ts is not None:
                for j in range(1, min(comm_count, 12)):
                    sender_is_seller = j % 2 == 1
                    ts = response_ts + timedelta(minutes=j * rng.randint(15, 240))
                    sentiment_base = 0.24 if status == "converted" else -0.05 if status == "abandoned" else 0.08
                    message_writer.writerow(
                        {
                            "message_id": f"M{msg_id:012d}",
                            "sender_id": seller.seller_id if sender_is_seller else buyer.buyer_id,
                            "receiver_id": buyer.buyer_id if sender_is_seller else seller.seller_id,
                            "txn_id": transaction_id,
                            "message_type": "reply" if sender_is_seller else "followup",
                            "timestamp": ts.isoformat(sep=" "),
                            "read_status": rng.choice(["read", "read", "read", "unread"]),
                            "response_latency_minutes": round(latency if sender_is_seller and j == 1 else rng.uniform(10, 360), 2),
                            "sentiment": round(clamp(rng.gauss(sentiment_base, 0.28), -1, 1), 3),
                            "escalation_flag": rng.random() < (0.06 if status == "abandoned" else 0.01),
                        }
                    )
                    msg_id += 1
                    message_written += 1
    return inquiry_written, message_written


def write_manifest(output_dir: Path, counts: Dict[str, int], args: argparse.Namespace) -> None:
    manifest = {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "seed": args.seed,
        "scale": args.scale,
        "months": args.months,
        "counts": counts,
        "notes": "Synthetic data for churn early-warning demos. No real customer data.",
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic churn intelligence datasets.")
    parser.add_argument("--scale", choices=sorted(SCALE_PRESETS), default="demo")
    parser.add_argument("--sellers", type=int, default=None)
    parser.add_argument("--buyers", type=int, default=None)
    parser.add_argument("--inquiries", type=int, default=None)
    parser.add_argument("--contactbook", type=int, default=None)
    parser.add_argument("--months", type=int, default=24)
    parser.add_argument("--output-dir", default="data/demo")
    parser.add_argument("--formats", nargs="+", choices=["csv", "parquet", "sql"], default=["csv"])
    parser.add_argument("--sql-max-rows", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)
    fake = Faker("en_IN") if Faker is not None else None
    if fake is not None:
        fake.seed_instance(args.seed)

    preset = SCALE_PRESETS[args.scale]
    seller_count = args.sellers or preset["sellers"]
    buyer_count = args.buyers or preset["buyers"]
    inquiry_count = args.inquiries or preset["inquiries"]
    contactbook_count = args.contactbook or preset["contactbook"]

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_dir = output_dir / "csv"
    sql_dir = output_dir / "sql"
    parquet_dir = output_dir / "parquet"

    today = date(2026, 5, 15)
    start_date = today - timedelta(days=args.months * 30)

    sellers = generate_sellers(seller_count, rng, fake, today)
    buyers = generate_buyers(buyer_count, rng)

    tables = {
        "sellers": (
            [
                "seller_id",
                "business_name",
                "business_category",
                "city",
                "state",
                "region",
                "subscription_tier",
                "archetype",
                "onboarding_date",
                "response_rate",
                "avg_response_minutes",
                "product_count",
                "catalog_quality_score",
                "lead_utilization_score",
                "gst_verified",
                "trust_score",
                "churn_label",
                "churn_risk_score",
            ],
            sellers_to_rows(sellers, fake, rng),
        ),
        "buyers": (
            [
                "buyer_id",
                "industry",
                "region",
                "inquiry_frequency",
                "average_order_value",
                "engagement_score",
                "repeat_interaction_score",
                "activity_level",
                "churn_label",
            ],
            buyers_to_rows(buyers),
        ),
        "subscriptions": (
            [
                "subscription_id",
                "seller_id",
                "plan_type",
                "renewal_date",
                "renewal_history",
                "package_value",
                "usage_score",
                "feature_adoption_score",
                "login_frequency",
                "churn_outcome",
            ],
            subscription_rows(sellers, rng, today),
        ),
        "contactbook": (
            [
                "contactbook_id",
                "seller_id",
                "buyer_id",
                "interaction_frequency",
                "last_contacted_at",
                "relationship_strength",
                "repeat_business_score",
                "saved_contact_flag",
            ],
            contactbook_rows(contactbook_count, sellers, buyers, rng, today),
        ),
        "seller_health_daily": (
            [
                "seller_id",
                "as_of_date",
                "active_days_30d",
                "inquiries_received_30d",
                "handled_leads_30d",
                "response_rate_30d",
                "avg_response_minutes_30d",
                "conversion_rate_90d",
                "lead_utilization_score",
                "catalog_quality_score",
                "catalog_staleness_days",
                "buyer_repeat_count_90d",
                "sentiment_avg_30d",
                "graph_degree_90d",
            ],
            daily_feature_rows(sellers, rng, today),
        ),
    }

    counts: Dict[str, int] = {}
    for table_name, (fieldnames, rows) in tables.items():
        csv_path = csv_dir / f"{table_name}.csv"
        counts[table_name] = write_csv(csv_path, fieldnames, rows)

    counts["inquiries"], counts["messages"] = write_inquiries_and_messages(
        csv_dir / "inquiries.csv",
        csv_dir / "messages.csv",
        inquiry_count,
        sellers,
        buyers,
        rng,
        start_date,
        args.months,
    )

    if "sql" in args.formats:
        sql_dir.mkdir(parents=True, exist_ok=True)
        for csv_path in csv_dir.glob("*.csv"):
            write_sql_from_csv(csv_path, sql_dir / f"{csv_path.stem}.sql", csv_path.stem, args.sql_max_rows)

    if "parquet" in args.formats:
        parquet_dir.mkdir(parents=True, exist_ok=True)
        for csv_path in csv_dir.glob("*.csv"):
            ok = try_write_parquet(csv_path, parquet_dir / f"{csv_path.stem}.parquet")
            if not ok:
                print(f"parquet skipped for {csv_path.name}: install pandas and pyarrow")

    write_manifest(output_dir, counts, args)
    print(json.dumps({"output_dir": str(output_dir), "counts": counts}, indent=2))


if __name__ == "__main__":
    main()
