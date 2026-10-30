"""Lab 4 Task 3: log churn_model.train() under several hyperparameter settings
to the Lab 3 MLflow App, then write the full run table as evidence.

Trains locally (no SageMaker job); only the MLflow logging calls AWS.

    .venv/bin/python3.11 scripts/lab4_mlflow_runs.py /tmp/lab4data/features
    -> docs/lab4-mlflow-runs.txt
"""

import os
import sys

import mlflow

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "models", "churn"))
import churn_model  # noqa: E402
# The pipeline's own loader: sorted parts, dedup, sorted by customer_id. Row
# order decides the train/validation split, so anything else gives different numbers.
from train_sagemaker import read_channel  # noqa: E402

MLFLOW_APP_ARN = "arn:aws:sagemaker:us-east-1:480747229391:mlflow-app/app-X2C7AC6JJGBL"
EXPERIMENT = "northstar-churn-lab4"
OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "lab4-mlflow-runs.txt")

# The pipeline's own settings first, then one change at a time from them.
VARIANTS = {
    "d6-eta0.1 (pipeline)": {},
    "d3-eta0.1": {"max_depth": 3},
    "d6-eta0.03": {"eta": 0.03, "num_round": 600},
    "d8-eta0.3": {"max_depth": 8, "eta": 0.3},
}


def main(features_path):
    df = read_channel(features_path)
    base = dict(churn_model.HYPERPARAMETERS)
    mlflow.set_tracking_uri(MLFLOW_APP_ARN)
    mlflow.set_experiment(EXPERIMENT)

    for name, override in VARIANTS.items():
        churn_model.HYPERPARAMETERS = {**base, **override}
        with mlflow.start_run(run_name=name):
            mlflow.log_params(churn_model.HYPERPARAMETERS)
            mlflow.set_tags({"monotone_constraint": "days_since_last_purchase=+1",
                             "xgboost_version": churn_model.xgb.__version__,
                             "source": "churn_model.train(df, seed=42)"})
            try:
                _, metrics = churn_model.train(df, seed=42)
            except ValueError as e:
                # train() raises on a failed promotion gate. Record it, don't crash.
                mlflow.set_tag("gate", "FAILED")
                mlflow.set_tag("gate_failure", str(e)[:500])
                print(f"[{name}] gate FAILED: {e}")
                continue
            mlflow.set_tag("gate", "PASSED")
            mlflow.log_metrics({k: v for k, v in metrics.items()
                                if isinstance(v, (int, float)) and not isinstance(v, bool)})
    churn_model.HYPERPARAMETERS = base

    # Write the whole table: printing the DataFrame truncates params.* to "...".
    runs = mlflow.search_runs(experiment_names=[EXPERIMENT])
    cols = ["run_id", "tags.mlflow.runName", "tags.gate", "start_time"] + \
           [c for c in runs.columns if c.startswith(("params.", "metrics."))]
    with open(OUT, "w") as f:
        f.write(f"tracking_uri: {mlflow.get_tracking_uri()}\n\n{runs[cols].to_string()}\n")
    print(f"wrote {OUT} ({len(runs)} runs)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/lab4data/features")
