"""Run Track C scenarios and save a score table plus detailed JSONL traces.

Run from the repository root:
    python -m agent.evaluate

This makes Amazon Bedrock Converse calls and policy-index embedding calls.
"""

import logging
from pathlib import Path

import pandas as pd

from agent.agent import TURN_SUMMARIES, chat
from evaluation.evaluation_harness import AGENT_TEST_CASES, LocalAgentEvaluator


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def main():
    DOCS.mkdir(exist_ok=True)
    trace_path = DOCS / "lab3-agent-traces.jsonl"
    score_path = DOCS / "lab3-agent-eval.csv"

    # A fresh run gets a fresh trace file; every line is one structured event.
    logging.basicConfig(
        filename=trace_path,
        filemode="w",
        level=logging.INFO,
        format="%(message)s",
        force=True,
    )
    TURN_SUMMARIES.clear()

    evaluator = LocalAgentEvaluator(invoke_fn=chat)
    results = evaluator.run(AGENT_TEST_CASES)

    # The harness invokes scenarios sequentially, matching these per-turn summaries.
    summaries = list(TURN_SUMMARIES)
    results["tokens_in"] = [item["tokens_in"] for item in summaries]
    results["tokens_out"] = [item["tokens_out"] for item in summaries]
    results["estimated_haiku_cost_usd"] = [
        item["estimated_haiku_cost_usd"] for item in summaries
    ]
    results["duration_ms"] = [item["duration_ms"] for item in summaries]
    # The shared harness checks tool routing and escalation, not semantic correctness.
    results["manual_response_review_required"] = True
    results.to_csv(score_path, index=False)

    total_haiku_cost = sum(item["estimated_haiku_cost_usd"] for item in summaries)
    print(f"\nSaved scenario results: {score_path}")
    print(f"Saved detailed traces:  {trace_path}")
    print(f"Estimated Haiku token cost for this run: ${total_haiku_cost:.5f}")
    print("(Titan embedding calls used by query_policy are not included in this estimate.)")


if __name__ == "__main__":
    main()
