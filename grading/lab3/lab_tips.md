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

## Which infrastructure each Lab 3 track needs

Track A is required for everyone and needs the Lab 2 Feature Group/offline store, the Lab 2 data bucket, and the MLflow App/Model Registry resources it creates or uses.

Track B also depends on Task 1: it generates offers for high-risk customers and uses their churn score and Feature Store profile. Keep Lab 2 data available for Track B.

Track C's customer-service agent does not itself need the Feature Store, MLflow, Model Registry, a SageMaker endpoint, or a Studio kernel. Its required order lookup is simulated and its policy tool reads the local starter-kit corpus. It does require Bedrock access. Remember that Track A remains required even if you choose Track C.
