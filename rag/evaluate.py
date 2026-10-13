"""Run the revised Track B RAGAS comparison.

The revised assignment treats RAGAS values as diagnostic evidence, not pass
thresholds. This runner scores all four instructor-provided cases twice before
and twice after one change: adding the customer profile as a judge context.
It writes detailed scores and a per-case/overall mean-and-range summary.

Run from the repository root after configuring Bedrock credentials:
    python rag/evaluate.py
"""

import json
import math
import sys
from pathlib import Path

import pandas as pd
from datasets import Dataset
from langchain_aws import BedrockEmbeddings, ChatBedrock
from ragas import evaluate as ragas_evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import answer_relevancy, context_recall, faithfulness

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if (ROOT / "evaluation" / "evaluation_harness.py").is_file():
    from evaluation.evaluation_harness import OFFER_TEST_CASES
elif (ROOT / "evalutation" / "evaluation_harness.py").is_file():
    from evalutation.evaluation_harness import OFFER_TEST_CASES
elif (ROOT / "evaluation_harness.py").is_file():
    from evaluation_harness import OFFER_TEST_CASES
else:
    raise FileNotFoundError(
        "Could not locate evaluation_harness.py in evaluation/, evalutation/, or the repository root"
    )

from rag.index import build_index
from rag.offer import generate_offer


EVIDENCE = ROOT / "docs" / "lab3-evidence"
REPEATS = 2
JUDGE_MODEL = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
REGION = "us-east-1"
METRICS = ("faithfulness", "answer_relevancy", "context_recall")


def build_judge():
    """Build the Bedrock RAGAS judge with an explicit output budget."""
    llm = LangchainLLMWrapper(ChatBedrock(
        model_id=JUDGE_MODEL,
        region_name=REGION,
        model_kwargs={"temperature": 0, "max_tokens": 4096},
    ))
    embeddings = LangchainEmbeddingsWrapper(BedrockEmbeddings(
        model_id="amazon.titan-embed-text-v2:0",
        region_name=REGION,
    ))
    return llm, embeddings


def profile_context(customer):
    """Format the supplied profile as an explicit source visible to the judge."""
    return "[Customer profile supplied with the test case]\n" + json.dumps(
        customer, sort_keys=True, ensure_ascii=False,
    )


def as_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def score_run(index, chunks, cases, condition, repeat, judge_llm, judge_embeddings):
    include_profile = condition == "after_profile_context"
    dataset_dict = {"question": [], "answer": [], "contexts": [], "ground_truth": []}
    outputs = []

    for tc in cases:
        print(f"  [{condition} repeat {repeat}] Generating {tc.customer_id}...")
        result = generate_offer(
            index, chunks, tc.customer_context, tc.question,
            strategy="two_pass", signal_mode="interpreted",
        )
        judge_contexts = list(result["contexts"])
        if include_profile:
            judge_contexts.append(profile_context(tc.customer_context))

        dataset_dict["question"].append(tc.question)
        dataset_dict["answer"].append(result["answer"])
        dataset_dict["contexts"].append(judge_contexts)
        dataset_dict["ground_truth"].append(tc.ground_truth)
        outputs.append({
            "condition": condition,
            "repeat": repeat,
            "customer_id": tc.customer_id,
            "judge_model": JUDGE_MODEL,
            "question": tc.question,
            "ground_truth": tc.ground_truth,
            "answer": result["answer"],
            "retrieved_policy_contexts": result["contexts"],
            "judge_contexts": judge_contexts,
            "usage": result["usage"],
        })

    print(f"  Scoring all {len(cases)} cases with judge {JUDGE_MODEL}...")
    scores = ragas_evaluate(
        Dataset.from_dict(dataset_dict),
        metrics=[faithfulness, answer_relevancy, context_recall],
        llm=judge_llm,
        embeddings=judge_embeddings,
    ).to_pandas()

    rows = []
    for position, (_, score_row) in enumerate(scores.iterrows()):
        output = outputs[position]
        row = {
            "condition": condition,
            "repeat": repeat,
            "customer_id": output["customer_id"],
            "judge_model": JUDGE_MODEL,
        }
        for metric in METRICS:
            row[metric] = as_number(score_row.get(metric))
        output["scores"] = {metric: row[metric] for metric in METRICS}
        rows.append(row)
    return rows, outputs


def summarize(rows):
    frame = pd.DataFrame(rows)
    summary_rows = []
    group_fields = (("condition", "customer_id"), ("condition",))
    for fields in group_fields:
        grouper = list(fields) if len(fields) > 1 else fields[0]
        for key, group in frame.groupby(grouper, dropna=False):
            key_values = key if isinstance(key, tuple) else (key,)
            base = dict(zip(fields, key_values))
            for metric in METRICS:
                values = pd.to_numeric(group[metric], errors="coerce").dropna()
                low = float(values.min()) if not values.empty else None
                high = float(values.max()) if not values.empty else None
                summary_rows.append({
                    **base,
                    "metric": metric,
                    "mean": float(values.mean()) if not values.empty else None,
                    "min": low,
                    "max": high,
                    "range": high - low if low is not None else None,
                    "valid_n": int(values.count()),
                    "expected_n": int(group.shape[0]),
                    "judge_model": JUDGE_MODEL,
                })
    return pd.DataFrame(summary_rows)


def main():
    if len(OFFER_TEST_CASES) != 4:
        raise ValueError(
            f"The revised Track B comparison expects the four supplied cases; found {len(OFFER_TEST_CASES)}."
        )
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    print("Building the FAISS index from northstar-policy-docs/...")
    index, chunks = build_index(str(ROOT / "northstar-policy-docs"))
    print(f"Indexed {len(chunks)} policy chunks.")
    judge_llm, judge_embeddings = build_judge()

    all_rows = []
    all_outputs = []
    conditions = ("before_profile_context", "after_profile_context")
    for condition in conditions:
        for repeat in range(1, REPEATS + 1):
            rows, outputs = score_run(
                index, chunks, OFFER_TEST_CASES, condition, repeat,
                judge_llm, judge_embeddings,
            )
            all_rows.extend(rows)
            all_outputs.extend(outputs)

    detailed = pd.DataFrame(all_rows)
    summaries = summarize(all_rows)
    detailed_path = EVIDENCE / "rag_eval.csv"
    summary_path = ROOT / "docs" / "lab3-ragas-summary.csv"
    examples_path = ROOT / "docs" / "lab3-rag-comparison-examples.json"
    detailed.to_csv(detailed_path, index=False)
    summaries.to_csv(summary_path, index=False)
    examples_path.write_text(
        json.dumps(all_outputs, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    print("\nPer-case and overall metric summary (means and ranges):")
    print(summaries.to_string(index=False))
    print("\nSaved:")
    print(f"  {detailed_path}")
    print(f"  {summary_path}")
    print(f"  {examples_path}")
    for condition in conditions:
        valid = detailed.loc[detailed["condition"] == condition, list(METRICS)].notna().sum()
        if any(int(valid[metric]) < len(OFFER_TEST_CASES) * REPEATS for metric in METRICS):
            print(
                f"\nWARNING: {condition} has failed judge calls. NaN is missing, not zero; "
                "rerun until each metric has 8 valid scores."
            )


if __name__ == "__main__":
    main()
