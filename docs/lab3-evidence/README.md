# Lab 3 evidence bundle

This folder contains the local artifacts and AWS exports for the final Lab 3
work. The final Athena-backed Track A training run was completed on October 13,
2026 as `lab3-final-20261013`. This TA repository includes both Track B and
the optional Track C extension; their evidence is intentionally kept separate.

## Track A files from the final run

- `train-final.log` — final training output, including Athena query ID
  `48047fdb-beea-407f-9c0b-7d7894fa53d0`
- `evaluation_metrics.json` — held-out metrics, baseline lift and 95% CI
- `slice-evaluation.csv` — results for all four loyalty tiers
- `confusion-matrix.png` and `feature-importance.png` — evaluation visuals
- `model.tar.gz` — registered model artifact
- `mlflow-runs.csv` — collector export containing four `northstar-churn` runs
  with parameters and metrics
- `account.json`, `athena-query.json`, `mlflow-app.json`, and
  `model-registry.json` — AWS-side exports captured before teardown

The evaluation write-up is `docs/lab3-evaluation-report.md`. Do not rerun
training just to regenerate these artifacts: the final AWS exports already
record a successful Athena query, four MLflow runs, and four pending-manual-
approval registry packages.

## Track B evidence

- `rag_eval.csv` — 16 valid RAGAS rows: four supplied cases, two repetitions
  before and after the profile-context change
- `track-b-generated-examples.json` — five actual captured outputs and their
  full retrieved contexts
- `track-b-examples.md` — five policy-reviewed pairs, metric analysis, and
  three documented failures with fixes
- `collect-output.txt` — successful Track B collector report (25 OK, no WARN
  or FAIL)

## Track C evidence (TA extension)

- `agent_eval.csv` — two repetitions of each required scenario, with the one
  observed TC-003 escalation failure retained honestly
- `agent-traces.jsonl` and `agent-cost.csv` — every tool event and session-cost
  estimate from the recorded runs
- `policy-tests.json` — seven direct Gateway tests, including the two denied
  over-cap credits and the documented split-credit limitation
- `agentcore-config.json` — pre-teardown Harness, Gateway, and Cedar-policy
  export
- `track-c-failures.md` — three concrete failure analyses and mitigations
- `collect-output-track-c.txt` — successful Track C collector report (33 OK,
  no WARN or FAIL)

## Collector status and teardown

The collectors have already run successfully. Their AWS API exports are kept
as submission evidence; do not rerun the Track C collector after AgentCore is
destroyed. If a fresh deployment ever needs a collector run, use:

```bash
bash scripts/collect-lab3-evidence.sh --track B
# or, for the AgentCore extension:
bash scripts/collect-lab3-evidence.sh --track C
```

The collector checks the Athena query, MLflow App and runs, registry metadata,
and—on Track C—the AgentCore configuration. The final Lab 3 teardown result is
stored separately at `docs/lab3-teardown-output.txt`.
