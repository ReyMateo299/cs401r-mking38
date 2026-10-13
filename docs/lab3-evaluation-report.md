# Lab 3 Task 1 — Churn model evaluation

## Final run

The final local XGBoost training run was `lab3-final-20261013`, using XGBoost
3.4.1. It queried the Feature Store offline table
`northstar_dev_customer_features_1791905178` through Athena (query ID
`48047fdb-beea-407f-9c0b-7d7894fa53d0`) and loaded 9,999 customers. The
stratified split used 6,999 training rows and 3,000 validation rows. The model
used `max_depth=6`, `eta=0.03`, `num_round=600`, and a training-split-derived
`scale_pos_weight=3.5448`. Its registered Model Registry package is version 4,
with `PendingManualApproval` status. See
[`train-final.log`](lab3-evidence/train-final.log) and the exported Athena and
Registry evidence after running the collector.

## Held-out evaluation

| Metric | Result | Requirement |
|---|---:|---:|
| Validation rows | 3,000 | Held-out split |
| AUC-ROC | 0.7835 | Report; no fixed threshold |
| Precision @ top 10% | 0.7100 | ≥ 0.50 |
| Recall @ top 10% | 0.3227 | ≥ 0.25 |
| Recency-only baseline AUC | 0.7232 | Report comparison |
| AUC lift over baseline | 0.0603 | Positive lift |
| Paired bootstrap 95% CI for lift | [0.0407, 0.0798] | Must exclude zero |

The model clears both precision and recall gates. The paired confidence
interval is entirely above zero, so this validation split supports the
conclusion that the full model outperformed the recency-only baseline. The
confusion matrix uses a probability threshold of 0.50; it records 1,726 true
negatives, 614 false positives, 231 false negatives, and 429 true positives.
Precision and recall at the top 10% use a ranking cutoff and are separate from
that thresholded confusion matrix.

The gain-based feature-importance plot shows `days_since_last_purchase` as the
largest contributor, followed by 180-day and 30-day purchase frequency.
Average order value and average basket size are the next strongest features;
customer tenure, online-to-store ratio, and category diversity have less gain
in this fitted model. These importance values describe this model and do not
establish causal effects.

Artifacts: [`confusion-matrix.png`](lab3-evidence/confusion-matrix.png),
[`feature-importance.png`](lab3-evidence/feature-importance.png), and
[`evaluation_metrics.json`](lab3-evidence/evaluation_metrics.json).

## Loyalty-tier slices

The model selects the top 10% of all customers globally. Slice recall therefore
measures the share of that tier's churners that fall in the global contact
group; it is not a separate top-10% allocation within every tier.

| Tier | Test n | Churn positives | AUC (95% CI) | Recall @ top 10% | Too small to conclude? |
|---|---:|---:|---:|---:|---|
| Bronze | 1,071 | 361 | 0.7536 [0.7206, 0.7849] | 0.4377 | No |
| Silver | 1,139 | 226 | 0.7204 [0.6830, 0.7590] | 0.2035 | No |
| Gold | 483 | 52 | 0.7433 [0.6685, 0.8121] | 0.1346 | No |
| Platinum | 307 | 21 | 0.8856 [0.8112, 0.9435] | 0.0952 | No; borderline |

Silver is the weakest reliable tier by AUC and is also the largest slice. Its
recall is more than ten percentage points below aggregate recall, so the
training script flags it as a weak-recall slice. Gold and Platinum are also
flagged for weak recall under that rule. Platinum has the highest point AUC,
but only 21 churn positives—one above the script's minimum of 20—so treat that
result as borderline rather than as strong evidence of superior performance.

The per-tier counts, positives, AUC, confidence intervals, recall, and size
flags are in [`slice-evaluation.csv`](lab3-evidence/slice-evaluation.csv).
After running `scripts/collect-lab3-evidence.sh`, confirm that
`evaluation_metrics.json`, one MLflow run, and a PendingManualApproval package
all contain the same final-run metrics.
