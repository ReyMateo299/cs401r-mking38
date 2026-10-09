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
