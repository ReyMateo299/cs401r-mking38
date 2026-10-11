# Training command and configuration

## Recorded version

`model/model_metadata.json` reports XGBoost **3.4.1**. Its training date is `20261011T043109` (UTC timestamp in the existing metadata).

## Runs in the MLflow export

`mlflow-search-runs.csv` contains three finished runs in `northstar-churn`:

| Run | `max_depth` | `eta` | `num_round` | `scale_pos_weight` | AUC | Precision@10% | Recall@10% |
|---|---:|---:|---:|---:|---:|---:|---:|
| `d3-eta0.1` | 3 | 0.1 | 300 | 3.5448 | 0.7792 | 0.73 | 0.3318 |
| `d6-eta0.1` | 6 | 0.1 | 300 | 3.5448 | 0.7764 | 0.69 | 0.3136 |
| `d6-eta0.03` | 6 | 0.03 | 600 | 3.5448 | 0.7835 | 0.71 | 0.3227 |

The registered package is version 3 and its metadata names `d6-eta0.03`, matching the third run and the bundled evaluation. The exact shell line, Feature Group name, and whether the script used Athena or `--local-data-path` are not recorded in MLflow. `docs/bedrock-access-verification.txt` also contains an attempted fourth command with `--include-risk-score`, but the checked-in `models/churn/train.py` does not define that option; it is not a valid invocation of the current script.

## Reproduction template for the checked-in script

The following zsh array preserves separate CLI arguments. It shows how to rerun the registered configuration; it is not proof of the historical data-loading path:

```zsh
COMMON=(--feature-group-name "$FG" --artifacts-bucket "$BUCKET" --mlflow-arn "$MLFLOW_APP_ARN")
python models/churn/train.py "${COMMON[@]}" \
  --max-depth 3 --eta 0.1 --num-round 300 --run-name d3-eta0.1
```

The script defaults to `northstar-churn` as the MLflow experiment, a 2026-01-01 through 2027-01-01 Feature Store event-time window, and a derived `scale_pos_weight`. It writes the model under `model/` and evaluation output under `output/` unless overridden.
