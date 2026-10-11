# Lab 3 Task 1 evidence bundle

This folder collects evidence for grading without starting AWS resources. It includes local evaluation artifacts plus AWS-side MLflow and Model Registry exports.

## Available local evidence

- `evaluation_metrics.json` is copied from `output/evaluation_metrics.json`.
- `slice_results.json` is extracted from `model/model_metadata.json`.
- `mlflow-search-runs.csv` contains three finished runs with distinct hyperparameter settings, metrics, and XGBoost version.
- `model-package.json` is the SageMaker `describe-model-package` response for package version 3.
- `training-command.md` maps the exported MLflow runs to the recorded experiment commands and notes what remains unverified.

The bundled evaluation reports AUC 0.7835, precision@10% 0.7100, recall@10% 0.3227, and a lift interval of [0.0407, 0.0798] on 3,000 held-out rows. Per-tier counts and metrics are in `slice_results.json`. The registered package is `PendingManualApproval` and its metadata matches these metrics. The training version is XGBoost 3.4.1; the serving image is XGBoost 1.7-1.

## Remaining evidence gap

The saved code has both the required Athena path and an optional local CSV path. The exported run metadata does not show which path produced the bundled metrics. Preserve a training log or source-data note confirming the Athena table and loaded row count if you need to demonstrate that provenance. The separate `docs/lab3-model-design.md` is also not present yet; Task 1 asks for metric interpretation, slice discussion, confusion matrix, and feature-importance plot there.
