"""Run Track C scenarios twice through the deployed AgentCore Harness."""

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from agent.harness_client import HarnessAgent
from evaluation.evaluation_harness import AGENT_TEST_CASES, LocalAgentEvaluator

EVIDENCE = Path("docs/lab3-evidence")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenario",
        action="append",
        choices=[case.scenario_id for case in AGENT_TEST_CASES[:5]],
        help="Re-evaluate only this scenario (may be repeated). Existing rows for it are replaced.",
    )
    args = parser.parse_args()
    selected_ids = args.scenario or [case.scenario_id for case in AGENT_TEST_CASES[:5]]
    selected_cases = [case for case in AGENT_TEST_CASES[:5] if case.scenario_id in selected_ids]

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    score_path = EVIDENCE / "agent_eval.csv"
    prior_results = None
    if score_path.exists():
        # Keep earlier measured behavior available for the failure analysis
        # instead of silently overwriting it when a corrected configuration is
        # measured again.
        archive = EVIDENCE / f"agent_eval-attempt-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
        prior_results = pd.read_csv(score_path)
        score_path.replace(archive)
        print(f"Archived prior scenario results to {archive}")
    runs = []
    for repetition in (1, 2):
        label = "remediation" if args.scenario else "evaluation"
        agent = HarnessAgent(run_label=f"{label}-{repetition}")
        evaluator = LocalAgentEvaluator(invoke_fn=agent.invoke)
        frame = evaluator.run(selected_cases)
        frame.insert(0, "repetition", repetition)
        runs.append(frame)
    results = pd.concat(runs, ignore_index=True)
    if prior_results is not None:
        prior_results = prior_results[~prior_results["scenario_id"].isin(selected_ids)]
        results = pd.concat([prior_results, results], ignore_index=True)
        results["scenario_order"] = results["scenario_id"].str.extract(r"(\d+)").astype(int)
        results = results.sort_values(["repetition", "scenario_order"]).drop(columns="scenario_order")
    results.to_csv(score_path, index=False)
    print(f"Saved {len(results)} scenario results to {score_path}")


if __name__ == "__main__":
    main()
