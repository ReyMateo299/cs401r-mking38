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
