#!/usr/bin/env python3
"""
AI Retention Agent — calls LLM API to generate personalized retention summaries.

Reads .env for API credentials, loads prompt templates from prompts/,
gathers seller evidence, and calls the LLM to produce structured output.

Usage:
    python scripts/ai_agent.py --seller-id 10001
    python scripts/ai_agent.py --top-risk 5
    python scripts/ai_agent.py --all-high-risk --output outputs/real/ai_summaries.json
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_prompt(name: str) -> str:
    path = Path("prompts") / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def build_seller_evidence(
    seller_id: str,
    data_dir: Path = Path("data/csv"),
    features_path: Path = Path("outputs/real/seller_features.csv"),
    scores_path: Path = Path("outputs/real/churn_scores.csv"),
) -> Dict[str, Any]:
    """Gather all evidence for a seller from real data + computed features."""

    # Profile
    profiles = read_csv(data_dir / "dataset - seller_profile.csv")
    profile = next((p for p in profiles if p["seller_id"] == seller_id), {})

    # Features
    features = read_csv(features_path)
    feature_row = next((f for f in features if f["seller_id"] == seller_id), {})

    # Score
    scores = read_csv(scores_path)
    score_row = next((s for s in scores if s["seller_id"] == seller_id), {})

    # Recent calls (last 10)
    calls = read_csv(data_dir / "dataset - buyer_seller_calls.csv")
    seller_calls = [c for c in calls if c["seller_id"] == seller_id]
    seller_calls.sort(key=lambda x: x.get("call_date", ""), reverse=True)
    recent_calls = seller_calls[:10]

    # Low-rating reviews (last 10)
    reviews = read_csv(data_dir / "dataset - seller_low_rating_reviews.csv")
    seller_reviews = [r for r in reviews if r["seller_id"] == seller_id]
    seller_reviews.sort(key=lambda x: x.get("review_date", ""), reverse=True)
    recent_reviews = seller_reviews[:10]

    # Tickets
    tickets = read_csv(data_dir / "dataset - seller_tickets.csv")
    seller_tickets = [t for t in tickets if t["seller_id"] == seller_id]

    # Ratings
    ratings = read_csv(data_dir / "dataset - seller_ratings.csv")
    rating_row = next((r for r in ratings if r["seller_id"] == seller_id), {})

    # Parse reason codes
    reason_codes = []
    try:
        reason_codes = json.loads(score_row.get("reason_codes", "[]"))
    except Exception:
        pass

    return {
        "seller_id": seller_id,
        "seller_name": profile.get("seller_name", ""),
        "company_name": profile.get("company_name", ""),
        "city": profile.get("city", ""),
        "state": profile.get("state", ""),
        "package": profile.get("package", ""),
        "member_since_years": profile.get("member_since_years", ""),
        "subscription_end_date": profile.get("subscription_end_date", ""),
        "risk_score": score_row.get("risk_score", ""),
        "risk_band": score_row.get("risk_band", ""),
        "confidence": score_row.get("confidence", ""),
        "reason_codes": reason_codes,
        "recommended_action": score_row.get("recommended_action", ""),
        "key_metrics": {
            "call_pickup_pct_30d": feature_row.get("act_30d_call_pickup_pct", ""),
            "total_enquiries_30d": feature_row.get("act_30d_total_enquiries", ""),
            "callbacks_30d": feature_row.get("act_30d_callbacks", ""),
            "catalogue_score": feature_row.get("act_30d_catalogue_score", ""),
            "negative_intent_pct": feature_row.get("negative_intent_pct", ""),
            "cancellation_rate": feature_row.get("cancellation_rate", ""),
            "overall_rating": feature_row.get("overall_rating", ""),
            "low_review_response_rate": feature_row.get("low_review_response_rate", ""),
            "untouched_pct": feature_row.get("untouched_pct", ""),
            "open_tickets": feature_row.get("open_tickets", ""),
            "buylead_trend": feature_row.get("buylead_trend", ""),
            "days_to_renewal": feature_row.get("days_to_renewal", ""),
            "total_contacts": feature_row.get("total_contacts", ""),
            "contacts_converted": feature_row.get("contacts_converted", ""),
        },
        "rating_profile": {
            "overall_rating": rating_row.get("overall_rating", ""),
            "total_reviews": rating_row.get("total_reviews", ""),
            "response_satisfaction_pct": rating_row.get("response_satisfaction_pct", ""),
            "quality_satisfaction_pct": rating_row.get("quality_satisfaction_pct", ""),
            "delivery_satisfaction_pct": rating_row.get("delivery_satisfaction_pct", ""),
        },
        "recent_calls": [
            {
                "date": c.get("call_date", ""),
                "buyer": c.get("buyer_name", ""),
                "product": c.get("mcat_name", ""),
                "duration_mins": c.get("call_duration_mins", ""),
                "seller_intent": c.get("seller_intent", ""),
                "buyer_intent": c.get("buyer_intent", ""),
            }
            for c in recent_calls[:5]
        ],
        "recent_reviews": [
            {
                "rating": r.get("rating", ""),
                "text": r.get("review_text", "")[:150],
                "date": r.get("review_date", ""),
                "responded": r.get("response_by_seller", ""),
            }
            for r in recent_reviews[:5]
        ],
        "open_tickets": [
            {
                "type": t.get("ticket_type", ""),
                "status": t.get("status", ""),
                "risk_level": t.get("risk_level", ""),
            }
            for t in seller_tickets if t.get("status") in ("Open", "Pending")
        ][:5],
    }


def call_llm(system_prompt: str, user_content: str) -> Optional[str]:
    """Call the LLM API using OpenAI-compatible client."""
    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("BASE_URL", "")
    model = os.getenv("ANTHROPIC_MODEL", "anthropic/claude-opus-4-6")

    if not api_key or not base_url:
        print("Warning: LLM_API_KEY or BASE_URL not set in .env", file=sys.stderr)
        return None

    if OpenAI is None:
        print("Warning: openai package not installed. pip install openai", file=sys.stderr)
        return None

    client = OpenAI(api_key=api_key, base_url=base_url)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            max_tokens=800,
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"LLM API error: {e}", file=sys.stderr)
        return None


def generate_retention_summary(seller_id: str) -> Dict[str, Any]:
    """Generate an AI retention summary for a seller."""
    evidence = build_seller_evidence(seller_id)
    system_prompt = load_prompt("retention_summary")
    user_content = json.dumps(evidence, indent=2, default=str)

    raw = call_llm(system_prompt, user_content)

    if raw:
        # Try to parse JSON from response
        try:
            # Strip markdown code fences if present
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
                cleaned = cleaned.rsplit("```", 1)[0] if "```" in cleaned else cleaned
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {"raw_response": raw, "parse_error": True}
    else:
        # Fallback: deterministic summary from reason codes
        reasons = evidence.get("reason_codes", [])
        evidence_strs = [r.get("evidence", r.get("code", "")) for r in reasons]
        return {
            "risk_explanation": f"Risk is {evidence.get('risk_band', 'unknown')} (score {evidence.get('risk_score', '?')}) due to: {'; '.join(evidence_strs) or 'multiple behavioral signals'}.",
            "reasons_to_stay": [
                f"You have {evidence['key_metrics'].get('total_contacts', '?')} buyer contacts in your network.",
                f"You received {evidence['key_metrics'].get('total_enquiries_30d', '?')} enquiries in the last 30 days.",
                f"Your catalogue score of {evidence['key_metrics'].get('catalogue_score', '?')} shows active product presence.",
            ],
            "next_best_action": evidence.get("recommended_action", "automated_health_nudge").replace("_", " ").title(),
            "sales_opening_line": "I am calling because your account shows strong buyer interest, and we want to help you capitalize on it.",
            "risk_level": evidence.get("risk_band", "unknown"),
            "confidence": float(evidence.get("confidence", 0.6)),
            "fallback": True,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Retention Agent")
    parser.add_argument("--seller-id", help="Score a specific seller")
    parser.add_argument("--top-risk", type=int, help="Generate for top N risk sellers")
    parser.add_argument("--all-high-risk", action="store_true", help="Generate for all high/critical risk")
    parser.add_argument("--output", default="", help="Write results to JSON file")
    args = parser.parse_args()

    results = {}

    if args.seller_id:
        print(f"Generating retention summary for {args.seller_id}...")
        result = generate_retention_summary(args.seller_id)
        results[args.seller_id] = result
        print(json.dumps(result, indent=2))

    elif args.top_risk or args.all_high_risk:
        scores = read_csv(Path("outputs/real/churn_scores.csv"))
        scores.sort(key=lambda x: -float(x.get("risk_score", 0)))

        if args.all_high_risk:
            targets = [s for s in scores if s["risk_band"] in ("high", "critical")]
        else:
            targets = scores[:args.top_risk]

        print(f"Generating summaries for {len(targets)} sellers...")
        for i, s in enumerate(targets):
            sid = s["seller_id"]
            print(f"  [{i+1}/{len(targets)}] {sid} (risk: {s['risk_score']}, band: {s['risk_band']})")
            result = generate_retention_summary(sid)
            results[sid] = result
            time.sleep(1)  # Rate limiting

    else:
        parser.print_help()
        return

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
        print(f"\nSaved {len(results)} summaries to {out_path}")


if __name__ == "__main__":
    main()
