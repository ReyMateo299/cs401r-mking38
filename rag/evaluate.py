"""Run Track B retrieval and prompt ablations using the provided RAGAS harness.

Run from the repository root after configuring Bedrock credentials:
    python rag/evaluate.py

The script does not modify the supplied evaluation harness. It adds one local
fifth test case, compares retrieval Options A/B/C with the final two-pass
retriever, and compares raw numeric signals with the interpreted prompt.
"""

import json
from copy import deepcopy
from pathlib import Path

import pandas as pd

from evaluation_harness import OFFER_TEST_CASES, RAGEvaluator, RAGTestCase
from rag.index import build_index
from rag.offer import generate_offer


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
STRATEGIES = ("option_a", "option_b", "option_c", "two_pass")


def fifth_test_case():
    """A fifth, local case; keep the instructor-provided harness unchanged."""
    return RAGTestCase(
        customer_id="LOCAL-TRACKB-005",
        customer_context={
            "churn_probability": 0.77,
            "loyalty_tier": "Bronze",
            "days_since_last_purchase": 73,
            "total_lifetime_value": 428.50,
            "avg_order_value": 58.20,
            "category_diversity_score": 0.25,
            "online_to_store_ratio": 0.18,
            "top_categories": ["Grocery", "Apparel"],
        },
        question=(
            "Generate a retention offer for this at-risk Bronze member who shops in "
            "store and mainly buys Grocery and Apparel."
        ),
        ground_truth=(
            "The offer should acknowledge Bronze status, recommend Grocery or Apparel, "
            "and use only supported Bronze entitlements: 1x points, free standard "
            "shipping at $75+, a $5 birthday reward, and a 30-day return window. "
            "It must not promise free return shipping, early access, gear repair, or "
            "free expedited shipping. A modest incentive is appropriate for this profile."
        ),
    )


def _evaluate(index, chunks, cases, strategy, signal_mode):
    outputs = {}

    def rag_fn(customer_context, question):
        # Match each invocation back to its built-in case using the complete
        # stable profile/question pair; the harness callback omits customer_id.
        tc = next(
            item for item in cases
            if item.customer_context is customer_context and item.question == question
        )
        result = generate_offer(
            index, chunks, customer_context, question,
            strategy=strategy, signal_mode=signal_mode,
        )
        outputs[tc.customer_id] = {
            "customer_id": tc.customer_id,
            "question": question,
            "ground_truth": tc.ground_truth,
            "answer": result["answer"],
            "contexts": result["contexts"],
            "usage": result["usage"],
        }
        return {"answer": result["answer"], "contexts": result["contexts"]}

    scores = RAGEvaluator(rag_invoke_fn=rag_fn).run(cases)
    scored_cases = []
    for position, (_, row) in enumerate(scores.iterrows()):
        case_output = outputs[cases[position].customer_id]
        case_output.update({key: _json_value(value) for key, value in row.to_dict().items()})
        scored_cases.append(case_output)

    summary = {
        "strategy": strategy,
        "signal_mode": signal_mode,
        "faithfulness": _mean(scores, "faithfulness"),
        "answer_relevancy": _mean(scores, "answer_relevancy"),
        "context_recall": _mean(scores, "context_recall"),
        "case_count": len(cases),
    }
    return summary, scored_cases


def _mean(frame, column):
    return float(frame[column].mean()) if column in frame.columns else None


def _json_value(value):
    if hasattr(value, "item"):
        return value.item()
    return value


def main():
    DOCS.mkdir(exist_ok=True)
    print("Building the FAISS index from northstar-policy-docs/...")
    index, chunks = build_index(str(ROOT / "northstar-policy-docs"))
    print(f"Indexed {len(chunks)} policy chunks.")

    cases = deepcopy(OFFER_TEST_CASES) + [fifth_test_case()]
    all_summaries = []
    final_examples = []

    for strategy in STRATEGIES:
        summary, case_outputs = _evaluate(
            index, chunks, deepcopy(cases), strategy, "interpreted"
        )
        all_summaries.append(summary)
        if strategy == "two_pass":
            final_examples = case_outputs

    raw_summary, _ = _evaluate(
        index, chunks, deepcopy(cases), "two_pass", "raw"
    )
    raw_summary["strategy"] = "two_pass"
    all_summaries.append(raw_summary)

    comparison = pd.DataFrame(all_summaries)
    comparison.to_csv(DOCS / "lab3-ragas-comparison.csv", index=False)

    chosen = comparison[
        (comparison["strategy"] == "two_pass")
        & (comparison["signal_mode"] == "interpreted")
    ]
    chosen.to_csv(DOCS / "lab3-ragas-results.csv", index=False)
    (DOCS / "lab3-rag-examples.json").write_text(
        json.dumps(final_examples, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("\nSaved:")
    print(f"  {DOCS / 'lab3-ragas-comparison.csv'}")
    print(f"  {DOCS / 'lab3-ragas-results.csv'}")
    print(f"  {DOCS / 'lab3-rag-examples.json'}")
    print("\nStrategy summary:")
    print(comparison.to_string(index=False))


if __name__ == "__main__":
    main()
