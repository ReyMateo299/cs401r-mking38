"""Capture the five Track B example offers without invoking the RAGAS judge.

This intentionally makes paid Bedrock embedding and generation calls. It does
not score or overwrite ``rag_eval.csv``. Review each saved answer against the
policy before promoting it into ``track-b-examples.md``.

Run from the repository root after configuring AWS credentials:
    python rag/capture_examples.py
"""

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.evaluation_harness import OFFER_TEST_CASES
from rag.index import build_index
from rag.offer import GEN_MODEL, generate_offer


LOCAL_CASE = {
    "customer_id": "LOCAL-TRACKB-005",
    "customer_context": {
        "churn_probability": 0.78,
        "loyalty_tier": "Bronze",
        "days_since_last_purchase": 61,
        "total_lifetime_value": 418.50,
        "avg_order_value": 52.30,
        "category_diversity_score": 0.25,
        "online_to_store_ratio": 0.25,
        "top_categories": ["Grocery", "Apparel"],
    },
    "question": (
        "Generate a retention offer for this at-risk Bronze member who shops "
        "in store and mainly buys Grocery and Apparel."
    ),
}


# This is a conservative screen, not a substitute for the policy review in
# track-b-examples.md. It flags recurrent unsafe wording before an answer is
# promoted into the submitted examples.
REVIEW_PATTERNS = {
    "warm-up or inferred-intent language": r"\b(we miss|we've missed|we.ve noticed|we.d love)\b",
    "invented points or reward claim": r"\b(extra points|bonus points|reward balance|\$5 (?:off|reward))\b",
    "invented campaign framing": r"\b(exclusive|coupon|promo code|discount code|special offer)\b",
    "unanchored deadline": r"\b(within|next) 45 days\b|\b(before the year ends|expires soon)\b",
    "unsupported tier-up claim": r"\b(close to Gold|Gold-tier benefits|toward Gold)\b",
    "assumed available Platinum credit": r"\b(gear credit waiting|unused gear credit|\$100 gear credit)\b",
    "invented sale claim": r"\b(upcoming .*sale|new arrivals)\b",
}


def review_flags(answer):
    """Return visible risk patterns for a human policy review."""
    return [
        label for label, pattern in REVIEW_PATTERNS.items()
        if re.search(pattern, answer, flags=re.IGNORECASE)
    ]


def record(case, index, chunks):
    result = generate_offer(
        index,
        chunks,
        case["customer_context"],
        case["question"],
        strategy="two_pass",
        signal_mode="interpreted",
    )
    flags = review_flags(result["answer"])
    return {
        "customer_id": case["customer_id"],
        "generation_model": GEN_MODEL,
        "question": case["question"],
        "customer_profile": case["customer_context"],
        "answer": result["answer"],
        "retrieved_policy_contexts": result["contexts"],
        "usage": result["usage"],
        "automated_review": {
            "status": "manual_review_required",
            "flags": flags,
        },
    }


def main():
    print("Building the local FAISS index (paid Bedrock embeddings)...")
    index, chunks = build_index(ROOT / "northstar-policy-docs")
    cases = [
        {
            "customer_id": item.customer_id,
            "customer_context": item.customer_context,
            "question": item.question,
        }
        for item in OFFER_TEST_CASES
    ]
    cases.append(LOCAL_CASE)

    outputs = []
    for case in cases:
        print(f"Generating {case['customer_id']} (paid Bedrock call)...")
        output = record(case, index, chunks)
        outputs.append(output)
        flags = output["automated_review"]["flags"]
        if flags:
            print(f"  Review flags: {', '.join(flags)}")
        else:
            print("  No automatic flags; manual policy review is still required.")

    path = ROOT / "docs" / "lab3-evidence" / "track-b-generated-examples.json"
    path.write_text(json.dumps(outputs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Saved {len(outputs)} generated examples to {path}")
    print("Review each answer; do not treat it as policy-correct solely because it was generated.")


if __name__ == "__main__":
    main()
