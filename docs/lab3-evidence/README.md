# Lab 3 evidence bundle

This folder contains the local artifacts for the final Track A run and the AWS
exports required by the Lab 3 guide. The final Athena-backed training run was
completed on October 13, 2026 as `lab3-final-20261013`.

## Track A files from the final run

- `train-final.log` — final training output, including Athena query ID
  `48047fdb-beea-407f-9c0b-7d7894fa53d0`
- `evaluation_metrics.json` — held-out metrics, baseline lift and 95% CI
- `slice-evaluation.csv` — results for all four loyalty tiers
- `confusion-matrix.png` and `feature-importance.png` — evaluation visuals
- `model.tar.gz` — registered model artifact
- `mlflow-runs.csv` — current copy is a snapshot from October 11 and predates
  the final October 13 run; refresh it from AWS with the evidence collector

The evaluation write-up is `docs/lab3-evaluation-report.md`. Do not rerun
training just to regenerate the existing local artifacts. Refresh the AWS
exports after the Track B evidence is ready, before tearing down infrastructure.

## AWS evidence still to export

From the repository root, run:

```bash
bash scripts/collect-lab3-evidence.sh --track B
```

The collector should write `account.json`, `athena-query.json`,
`mlflow-app.json`, a refreshed `mlflow-runs.csv`, `model-registry.json`, and
`collect-output.txt`. It also checks that the Athena query succeeded, at least
three experiment runs are available, and the final run's metrics match the
evaluation file and a `PendingManualApproval` registry package. Resolve any
`FAIL` before teardown. This command makes AWS API calls; run it in the
environment with the credentials used for the lab.

The other lab deliverables are separate: `docs/lab3-model-design.md`,
`notebooks/lab3-demo.ipynb`, and the required Track B files
`docs/lab3-evidence/rag_eval.csv` and
`docs/lab3-evidence/track-b-examples.md`.
