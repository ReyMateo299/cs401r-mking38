# Lab 3 student tips

## Before creating the MLflow App, check that your infrastructure is still up

The MLflow App is not self-contained: it needs an S3 artifact location and a SageMaker execution role. In this course, both come from the Terraform stack you built in Labs 1–2. If you destroyed that stack, re-apply it before running the MLflow command (and make sure the Lab 2 Feature Group has been populated).

Use Terraform outputs rather than guessing your bucket or role names:

```bash
cd infrastructure/environments/dev
export BUCKET=$(terraform output -raw s3_bucket_name)
export ROLE_ARN=$(terraform output -raw ml_engineer_role_arn)
cd -
```

Create the app with an artifact path the course role can write to:

```bash
aws sagemaker create-mlflow-app \
  --name northstar-mlflow \
  --artifact-store-uri "s3://${BUCKET}/artifacts/mlflow/" \
  --role-arn "$ROLE_ARN"
```

The `MLEngineer` role is intentionally limited to `artifacts/` and `features/`; a bucket-root or `mlflow/` path can create an app but later fail when MLflow writes an artifact. The free MLflow App does not require a SageMaker Studio domain, but the S3 bucket and role do need to exist.

## Task 1 is code first; the console supports it

You are expected to complete Python code in the supplied churn-training skeleton (usually copied to `models/churn/train.py`). The required work includes querying the offline Feature Store through Athena, splitting the loyalty-tier labels with the model data, evaluating tiers, logging each run to MLflow, and packaging/registering the model.

Run the completed script locally for your three or more experiments. A SageMaker Training Job is optional, so do not wait for training quota approval to start. Use the AWS CLI or console to create/check the MLflow App and inspect the Model Registry—not as a replacement for the training script.

## Where the Lab 3 starter files go

Download the Lab 3 starter kit from Canvas (or the public `cs401r-lab3-template` repository) and add it to the repository you started in Lab 1—do not create a separate Lab 3 repository or overwrite your existing work.

```text
churn_training_skeleton.py                  → models/churn/train.py (or keep its original name)
evaluation_harness.py                        → evaluation/evaluation_harness.py
prompt_templates/offer_generation_prompts.md → prompt_templates/offer_generation_prompts.md
northstar-policy-docs/                       → northstar-policy-docs/
scripts/teardown-lab3.sh                     → scripts/teardown-lab3.sh
```

Create any missing folders, then add and commit the files. The first mapping is the one Task 1 uses.

## Use the compatibility pins before beginning Task 1 or Track B

Create a virtual environment and install the tested dependencies rather than accepting the newest package versions:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install "sagemaker>=2.200.0,<3.0.0" xgboost scikit-learn pandas numpy boto3 \
            mlflow sagemaker-mlflow matplotlib
# Track B only:
pip install faiss-cpu ragas datasets "langchain-community<0.4" langchain-aws
python -c "from sagemaker.feature_store.feature_group import FeatureGroup; import mlflow, sagemaker_mlflow; print('imports OK')"
```

Why the constraints matter: SageMaker SDK 3.x removed the Feature Store module Task 1 imports, `sagemaker-mlflow` authenticates MLflow to the SageMaker App, and newer `langchain-community` releases break RAGAS imports. Put the resulting constraints in a committed `requirements.txt` so a fresh environment can reproduce your work.

## macOS: install OpenMP once when XGBoost cannot load

If `import xgboost` fails with `Library not loaded: @rpath/libomp.dylib`, install the missing OpenMP runtime with Homebrew:

```bash
brew install libomp
```

Install `libomp` at the system level, not in your Python virtual environment. It is a native shared library that XGBoost loads; the virtual environment only isolates Python packages. After installation, activate your virtual environment and verify the Python package can now load it:

```bash
source .venv/bin/activate
python -c "import xgboost; print(xgboost.__version__)"
```

## Do not tear down Lab 2 between Lab 3 work sessions

`scripts/teardown-lab2.sh` intentionally empties every version of the data bucket and then destroys the bucket and Feature Group. A later `terraform apply` recreates the bucket, Glue resources, and Feature Group, but all are empty—Terraform recreates infrastructure, not data.

If you tore down Lab 2, re-apply it and repopulate the Feature Store before Task 1. The standard recovery is to re-run the Lab 2 pipeline. If you saved the `processed/customers/` Parquet files locally, you may upload that snapshot after the bucket is recreated and then run the **feature-engineering** Glue job; it writes Feature Store records and restores the offline store that Task 1 queries. Uploading processed files alone is not enough.

For a multi-session Lab 3 workflow, keep the Lab 2 stack up and stop only resources that bill while idle (for example, Studio kernels and test endpoints). Run the full Lab 2 teardown only when you are ready to rebuild its data or are finished with the infrastructure.

### What happens to MLflow if you tear down Lab 2?

The MLflow App and its run history remain: parameters, metrics, timestamps, and run IDs are stored by SageMaker rather than Terraform. But the App's logged artifacts are in the Lab 2 S3 bucket. Because the Lab 2 teardown empties and deletes that bucket, it permanently removes MLflow plots, model files, and other artifacts. Model Registry records can remain but will point at deleted model files.

`scripts/teardown-lab3.sh` is safe after Task 1 because it leaves the MLflow App and Registry alone while it removes billable endpoints and active jobs. If you later run the Lab 2 teardown, rebuild the data/Feature Store and rerun any model you need for later labs; once Terraform recreates the bucket and role, keep using the same MLflow App ARN rather than creating a second App.

### Check whether the Feature Store must be repopulated

You do not need the Studio Feature Store page for this check. From the repository root, first confirm that the Feature Group and its offline store exist:

```bash
cd infrastructure/environments/dev
export FG=$(terraform output -raw feature_group_name)
aws sagemaker describe-feature-group --feature-group-name "$FG" \
  --query '{featureGroup:FeatureGroupStatus, offlineStore:OfflineStoreStatus.Status, database:OfflineStoreConfig.DataCatalogConfig.Database, table:OfflineStoreConfig.DataCatalogConfig.TableName}' \
  --output table
cd -
```

You want the Feature Group to be `Created`, the offline store to be `Active`, and a database/table name. If it is missing, failed, or has no table, re-apply Lab 2 and rerun the feature-engineering pipeline.

To confirm that it has actual records—not merely an empty Feature Group—open the Athena console in `us-east-1`, choose the database/table shown above, and run:

```sql
SELECT COUNT(*) AS feature_rows
FROM "sagemaker_featurestore"."YOUR_OFFLINE_STORE_TABLE";
```

If the count is zero, rerun the Lab 2 feature-engineering Glue job. If the table itself is missing after a teardown, re-apply the stack first, then repopulate it.

## Keep aggregate evaluation separate from slice evaluation

Do not replace `evaluate_model(model, X_val, y_val, baseline_proba)`: the starter already uses it for the overall metrics and the recency-baseline confidence interval.

The Solution Notes code in Step 2.4 replaces the separate `evaluate_slices` stub. Its updated signature accepts `tiers` (the `tier_val` array that travels through `train_test_split`) and optional reliability/bootstrapping arguments. After the existing aggregate-evaluation line, add:

```python
slice_results = evaluate_slices(model, X_val, y_val, tier_val)
```

Then pass `slice_results` to the updated tracking and registration functions described in the later solution steps.

## macOS zsh: make reusable command arguments an array

The Solution Notes use a bash-style reusable string:

```bash
COMMON="--feature-group-name $FG --artifacts-bucket $BUCKET --mlflow-arn $MLFLOW_APP_ARN"
python models/churn/train.py $COMMON ...
```

In zsh (the default macOS shell), `$COMMON` is passed as one argument instead of being split into flags. `argparse` then reports that `--artifacts-bucket` is missing even though `echo $COMMON` looks correct.

Use a zsh array instead:

```zsh
COMMON=(--feature-group-name "$FG" --artifacts-bucket "$BUCKET" --mlflow-arn "$MLFLOW_APP_ARN")
python models/churn/train.py "${COMMON[@]}" --max-depth 3 --eta 0.1 --num-round 300 --run-name d3-eta0.1
```

Or put each flag directly in the `python` command. The SDK v2 deprecation warning in the output is expected for this lab and is unrelated to the argument error.

## Athena returns zero rows: check the Feature Store ingest-date window first

`event_time` in this lab is when the Lab 2 feature-engineering job ran, not the historical cutoff date used to calculate features. If your script defaults to a window ending on `2026-06-01`, it will exclude a Fall 2026 Lab 2 run even when the Feature Store has data.

Run with the semester-wide window:

```zsh
python models/churn/train.py "${COMMON[@]}" \
  --training-start-date 2026-01-01 --training-end-date 2027-01-01 \
  --max-depth 3 --eta 0.1 --num-round 300 --run-name d3-eta0.1
```

The current starter kit uses those defaults. If your copied script instead defaults to `2025-02-01` through `2026-06-01`, update those defaults or keep supplying the two flags. Only rerun the Lab 2 feature pipeline after confirming the Feature Group/offline store is missing or the wider date window still returns zero rows.

## Which infrastructure each Lab 3 track needs

Track A is required for everyone and needs the Lab 2 Feature Group/offline store, the Lab 2 data bucket, and the MLflow App/Model Registry resources it creates or uses.

Track B also depends on Task 1: it generates offers for high-risk customers and uses their churn score and Feature Store profile. Keep Lab 2 data available for Track B.

Track C's customer-service agent does not itself need the Feature Store, MLflow, Model Registry, a SageMaker endpoint, or a Studio kernel. Its required order lookup is simulated and its policy tool reads the local starter-kit corpus. It does require Bedrock access. Remember that Track A remains required even if you choose Track C.

## Pandas 3: fix the `train_test_split` slice-label error

If `train.py` fails at `train_test_split` with:

```text
TypeError: only integer scalar arrays can be converted to a scalar index
```

the `loyalty_tier` column is probably a pandas 3 Arrow-backed string array. Do not pass `.values` directly to scikit-learn. Convert the tiers to a regular NumPy array first:

```python
tiers = df[SLICE_COLUMN].to_numpy(dtype=str)
X_train, X_val, y_train, y_val, tier_train, tier_val = train_test_split(
    X, y, tiers, test_size=0.30, random_state=42, stratify=y,
)
```

Keep the tiers in the same `train_test_split` call as `X` and `y`; this is what preserves their row-by-row alignment for slice evaluation.

## Save Task 1 grading evidence before tearing down AWS resources

Your grader should be able to review Task 1 without starting your infrastructure. Before cleanup, save these files in your repository under `docs/lab3-task1-evidence/`:

- the held-out evaluation metrics and per-tier slice results;
- an MLflow `search_runs` export showing at least three meaningful runs with parameters and metrics;
- the Model Registry package description showing `PendingManualApproval` and its evaluation metadata;
- your training command/configuration and XGBoost version.

Keep the training script and design document with them. The saved evidence makes the AWS results reviewable after teardown; it does not replace using Athena, MLflow, or Model Registry for the lab.
