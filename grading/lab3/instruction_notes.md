# Lab 3 instruction suggestions

## MLflow App prerequisites are missing from the main instructions

**Finding (2026-10-09):** The main Lab 3 instructions jump directly to `aws sagemaker create-mlflow-app` without stating that the Lab 1–2 Terraform stack must still be deployed. For the course's intended configuration, the command depends on two resources from that stack:

- the account-specific data bucket, used as the MLflow artifact store;
- the `northstar-dev-MLEngineer` IAM role, which trusts SageMaker and can write under `s3://<bucket>/artifacts/`.

The solution notes do state this in Phase 0 and retrieve both values using `terraform output`, but students reading the main lab first can reasonably try the command before the required resources exist.

**Suggested revision:** Add a prerequisite immediately before the “Experiment tracking” / MLflow App setup section:

> **Prerequisite — keep your Lab 1–2 Terraform stack deployed.** Before creating the MLflow App, confirm that your `infrastructure/environments/dev` stack is applied and that the Lab 2 Feature Group is populated. The App uses the Terraform-created data bucket for its artifact store and the `MLEngineer` role as its SageMaker execution role. Retrieve the exact values rather than typing names:
>
> ```bash
> cd infrastructure/environments/dev
> export BUCKET=$(terraform output -raw s3_bucket_name)
> export ROLE_ARN=$(terraform output -raw ml_engineer_role_arn)
> cd -
> ```
>
> If you previously destroyed the stack, re-apply it (and re-run the Lab 2 feature pipeline if necessary) before continuing.

Then have the MLflow command use `--artifact-store-uri "s3://${BUCKET}/artifacts/mlflow/"` and `--role-arn "$ROLE_ARN"`. This also aligns the main instructions with the solution notes and with the least-privilege permissions of the Terraform-created role.

## Task 1 does not clearly say that students must write Python

**Finding (2026-10-09):** Task 1 reads like a list of cloud-resource outcomes (“Train a churn model,” use MLflow, register a model), so a student could reasonably ask whether this is console work. It is not. The rubric requires a **training script** that issues an Athena query, and the solution notes direct students to complete five TODOs in the supplied churn-training skeleton:

1. load Feature Store data through Athena;
2. keep loyalty-tier labels aligned in the train/test split;
3. evaluate slices by loyalty tier;
4. log parameters and metrics to MLflow; and
5. package/upload/register the model with `PendingManualApproval`.

The model can be trained locally; a SageMaker Training Job is optional. AWS CLI/console work is used to provision or inspect resources, but it cannot by itself satisfy the code-based rubric items.

**Suggested revision:** Add this short orientation paragraph directly after Task 1's opening sentence:

> **This is primarily a Python implementation task.** Copy the supplied starter kit into your repository and complete the TODOs in `models/churn/churn_training_skeleton.py` (you may rename it to `train.py`). You will run that script locally for the required experiments; a SageMaker Training Job is optional. Use the AWS CLI or console only to create/inspect the MLflow App and Model Registry resources. Your submission must include the completed training code and its results.

Also link to the starter-kit location at that point, rather than leaving its discovery to the solution notes.

## The main handout names the starter kit but not its destination layout

**Finding (2026-10-09):** The `Starter Kit (Canvas: Lab 3)` section correctly tells students to download the kit from Canvas (or the public `cs401r-lab3-template` repository) and add it to their existing Lab 1 repository. However, it does not say where each file belongs. The exact layout appears only in Solution Notes Phase 0.5.

**Suggested revision:** Add the following mapping below the download instruction in the main handout:

```text
churn_training_skeleton.py                 → models/churn/churn_training_skeleton.py
                                             (or models/churn/train.py)
evaluation_harness.py                       → evaluation/evaluation_harness.py
prompt_templates/offer_generation_prompts.md → prompt_templates/offer_generation_prompts.md
northstar-policy-docs/                      → northstar-policy-docs/
scripts/teardown-lab3.sh                    → scripts/teardown-lab3.sh
```

State explicitly that students should create missing directories, preserve existing files, and commit the added starter files to their existing repository.

## Package pins are explained in the solution notes, not in the main setup path

**Finding (2026-10-09):** The main handout explicitly documents only the Track B pin `langchain-community<0.4`, including its RAGAS import failure. It does not give a complete Python-environment setup command or explain the Task 1 constraint `sagemaker>=2.200.0,<3.0.0`. The solution notes do both.

`sagemaker<3.0.0` is required because SDK 3.x removed `sagemaker.feature_store`; imports of the base package can succeed while the Feature Store import used by Task 1 fails. `sagemaker-mlflow` is also required: it supplies the SigV4 authentication plugin for an MLflow App ARN. The main handout separately warns that old AWS CLI and boto3/botocore versions may not recognize `create-mlflow-app`, but does not offer a consolidated preflight.

**Suggested revision:** Add a “Python environment and version pins” prerequisite before Task 1 with the tested install command, an import smoke test, and one-line explanations for the two pins:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install "sagemaker>=2.200.0,<3.0.0" xgboost scikit-learn pandas numpy boto3 \
            mlflow sagemaker-mlflow matplotlib
# Track B only:
pip install faiss-cpu ragas datasets "langchain-community<0.4" langchain-aws
python -c "from sagemaker.feature_store.feature_group import FeatureGroup; import mlflow, sagemaker_mlflow; print('imports OK')"
```

Students should preserve these constraints in a committed requirements file so their lab is reproducible.

## Main Lab 3 instructions should warn that a Lab 2 teardown destroys its training data

**Finding (2026-10-10):** `scripts/teardown-lab2.sh` deliberately deletes all versions and delete markers in the data bucket before it runs `terraform destroy`. Terraform then deletes the bucket (its `force_destroy` setting permits this) and the Feature Group. Reapplying Terraform recreates empty infrastructure; it does not recreate the Feature Store records or its offline-store Parquet data.

The Lab 3 solution notes correctly say that, if the Feature Group is gone, students must re-apply Lab 2 and re-run the feature pipeline. The main Lab 3 handout does not make this consequence clear, which can lead students to expect that restoring `processed/` Parquet alone solves Task 1.

**Suggested revision:** Add this warning alongside the Lab 3 infrastructure prerequisite:

> Do not run the Lab 2 teardown between Lab 3 work sessions unless you intend to rebuild the data. It deletes the data bucket and Feature Group. After a teardown, `terraform apply` restores only empty resources; re-run the feature-engineering job to repopulate the Feature Group and its Athena-queryable offline store. Restoring a saved `processed/` snapshot can avoid rerunning the transform job, but it still does **not** restore Feature Store records—you must rerun feature engineering.

## Lab 2 teardown preserves MLflow run metadata but deletes its artifacts

**Finding (2026-10-10):** The MLflow App itself is not managed by the Terraform stack, and its backend metadata (run IDs, parameters, metrics, and timestamps) is held by SageMaker. Therefore, a Lab 2 `terraform destroy` does not delete the MLflow App or its run listings. However, the app's artifact store is under the Lab 2 data bucket (`artifacts/mlflow/`), and `teardown-lab2.sh` empties and deletes that bucket. Logged plots, model files, and other MLflow artifacts are permanently lost; Model Registry packages will retain metadata but their referenced S3 model artifacts no longer exist.

**Suggested revision:** Amend the Lab 3 teardown guidance to distinguish the two scopes:

> `teardown-lab3.sh` is safe after Task 1: it removes billable endpoints and active jobs while retaining the MLflow App, run history, and registry records. Do not run `teardown-lab2.sh` until you are prepared to lose the Feature Store data and S3-backed artifacts. If you do tear it down, re-apply Terraform, repopulate the Feature Store, and rerun/re-register any model whose artifacts you will need later. Reuse the existing MLflow App ARN after the bucket and role are recreated; do not create a second App.
