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

## Save the updated Lab 3 evidence bundle before teardown

The updated guide specifies exact paths under `docs/lab3-evidence/`. Run the
graded training command with `--output-data-dir docs/lab3-evidence`, omit
`--local-data-path`, and save all console output to
`docs/lab3-evidence/train-final.log`. Confirm the log includes an
`Athena QueryExecutionId`. Then run
`bash scripts/collect-lab3-evidence.sh --track B` or `--track C` before
teardown; the collector exports the Athena query, MLflow App/runs, and registry
record, and checks the evidence files and matching metrics.

Keep the evaluation report, model-design document, and cleanly executed demo
notebook at the paths in the guide. For Fall 2026, the professor's transition
note says missing new evidence files do not cost points; a TA may request a
short screen-share for evidence that is still only in AWS. The export workflow
is still the easiest way to make the result reviewable after teardown.

## Track B: follow the revised RAGAS evidence requirements

From the repository root, activate the project environment and run:

```zsh
source .venv/bin/activate
python rag/evaluate.py
```

The professor has withdrawn the RAGAS thresholds as grading criteria. Run all four supplied cases at least twice. Report each case's scores, the mean and range, and the judge model. For each metric, explain a limitation using a specific case or claim. Measure one pipeline change before and after; it earns credit even if it does not improve the scores.

The local runner now compares the same offer pipeline before and after adding the customer profile as an extra judge context. It runs two repeats per condition and writes detailed per-case scores to `docs/lab3-evidence/rag_eval.csv`, a mean/range summary to `docs/lab3-ragas-summary.csv`, and answers plus contexts to `docs/lab3-rag-comparison-examples.json`. It names the judge model in both outputs. Before/after is the one measured change; do not combine it with a prompt rewrite if you want to attribute score differences to profile context.

This run calls Bedrock for embeddings, offer generation, and RAGAS scoring, so it may incur AWS charges. If you get `Could not connect to the endpoint URL` or a DNS error, check network access and the AWS profile used by Python. With IAM Identity Center, run `aws sso login --profile YOUR_PROFILE` and set `AWS_PROFILE=YOUR_PROFILE` in the same terminal. Do not paste credentials into the script or commit them.

A `NaN` score means the judge call failed, often from throttling. It is missing evidence, not zero. Rerun until you have valid scores for all four cases in both repeats of each condition. The range is the maximum minus minimum across repeated scores; also show the values per case so the grader can see where the metric varies.

Use the rubric's revised interpretation of the metrics:

- **Faithfulness:** the judge sees retrieved policy context and, in the after condition, the customer profile. Unsupported wording or a claim present only in the profile can shift the score. Avoid filler such as “We've missed you!” and invented terms such as an unprovided redemption deadline.
- **Answer relevancy:** this metric was designed for question answering, so a generated offer may be relevant but still score poorly. Cite a case where the offer answers the request and explain what the judge appears to penalize.
- **Context recall:** the supplied ground truths include claims the policy corpus does not support, so retrieval of the complete corpus still cannot satisfy every expected claim. Identify a specific unsupported ground-truth claim rather than trying to force retrieval to invent evidence.

Adding profile data to judge contexts is a rubric-supported pipeline change because the judge otherwise cannot verify profile facts in an offer. Keep retrieved policy chunks and the profile labeled separately in the saved evidence so a grader can see the provenance of each claim.

If you get `Could not connect to the endpoint URL` or a DNS error, check that your environment has network access to Bedrock and that the AWS profile used by Python is authenticated. If you use AWS IAM Identity Center, run `aws sso login --profile YOUR_PROFILE` in the same terminal and set `AWS_PROFILE=YOUR_PROFILE` before starting the script. Do not paste credentials into the script or commit them.

The handout rubric says “demo notebook,” but the Solution Notes provide a Python entry point. Keep the command you ran and the required Track B examples with your submission; ask the instructor which artifact format they expect if the rubric has not been updated.

## Keep retention-offer expiry separate from return eligibility

POL-LOY-011 §5.1 gives a retention offer a 45-day redemption period. That does not extend the return window: Gold has 30 calendar days from delivery (online) or purchase (in store), under POL-RET-004. State the offer deadline separately, avoid wording that implies a 45-day return period, and give the customer an explicit next step such as “Shop Outdoor or Footwear and redeem this offer by [date].” Also, a standing tier benefit such as Gold free return shipping may be accurate but is not necessarily a new retention incentive; do not label it “exclusive” unless the campaign actually makes it exclusive.

## If RAGAS reports `LLMDidNotFinishException`, check score completeness

The RAGAS judge can run out of output tokens while scoring long answers and policy contexts. A `NaN` score is missing evidence, not a zero. The local `rag/evaluate.py` configures a larger judge output limit and reports valid counts; rerun if any case is missing a metric. The withdrawn thresholds are not pass/fail criteria. Inspect individual offers and contexts to support your analysis; an offer's 45-day redemption deadline does not extend a Gold member's 30-day return window.

When offers invent “bonus points,” a new minimum purchase, an available birthday reward, or an unused gear-credit balance, that is a prompt-grounding failure. The customer profile does not contain those facts. Use a stated tier benefit as an existing benefit; don’t turn it into a new promotion or call it exclusive. Lifetime value is also not the trailing-12-month spend used to determine a policy tier, so do not claim a customer is a specific amount from the next tier.

## A policy duration is not an individualized expiry date

POL-LOY-011 §5.1 says a retention offer is valid for 45 days **from issue**. You may use that exact policy wording only when the retention-offer chunk was retrieved. Do not turn it into a calendar deadline—or “within the next 45 days”—unless the profile supplies the issue date. Likewise, “400 locations” is supported by the shipping/FAQ corpus, but it is not useful offer personalization; include it only when a customer actually asks about pickup or locations and you retrieved its source.

## Track C: verify the AgentCore prerequisites before deployment

The current Track C handout requires boto3 1.43.57 or later, AWS CLI **v2**
2.36 or later, and Terraform 1.7.5 or later. `aws --version` beginning with
`aws-cli/1.` is AWS CLI v1 and does not satisfy the CLI prerequisite; install
or select an AWS CLI v2 binary before following the handout's AgentCore
workflow. `terraform version` and this no-network Python check make the other
requirements visible:

```zsh
terraform version
python -c "import boto3; print(boto3.__version__)"
```

This is a verified compatibility requirement from the current handout. Whether
an older CLI happens to work with a particular Terraform run is not a supported
assumption.

## Track C: produce and review the AgentCore evidence

After the AgentCore Terraform stack is applied, run the direct Gateway/Cedar
probe first, then the Harness evaluation:

```zsh
source .venv/bin/activate
python agent/policy_tests.py
python -m agent.evaluate
```

The policy probe must report all seven expected outcomes and writes
`docs/lab3-evidence/policy-tests.json`. The evaluator runs the five required
scenarios twice and writes `agent_eval.csv`; its Harness client appends each
tool call to `agent-traces.jsonl` and each runtime session's estimated cost to
`agent-cost.csv`. These commands invoke deployed AWS services. They do not
write or replace Track B's `rag_eval.csv` or `track-b-examples.md`.

The supplied collector currently looks for a legacy `latency` key even though
the documented trace field is `latency_ms`. The working client records both
with the same millisecond value for compatibility. If you use an unmodified
starter client and the collector says that only `latency` is missing, retain
the correct `latency_ms` field and report the collector mismatch rather than
rerunning paid Harness evaluations solely for that message.

Review both repetitions, especially TC-002 through TC-005. TC-002's 30-day
rule is in POL-RET-004 §1, not the loyalty document; the Silver return-shipping
fee is in §6.2. TC-004 should ask for clarification without promising a refund.
For TC-005, verify the final reply cites POL-RET-004 §4, plainly declines the
final-sale return, does not imply an exception is possible, and calls
`escalate_to_human`. A tool-check PASS alone does not prove those response
details.

The required TC-003 and TC-005 prompts do not provide a customer ID, but they
still require a recorded escalation. Make the escalation tool accept an absent
ID and pass `customer_id: "UNKNOWN"`; do not omit the call because the customer
did not provide an account number. Similarly, a return request that supplies a
tier and elapsed time is already a policy question: call `query_policy` before
asking for a missing order ID.

Finally, write `track-c-failures.md` using actual trace `session_id` values.
One required failure case is the two allowed $40 credits: a per-call Cedar
policy sees each call separately, not their $80 total. Explain that a
stateful/temporal control with durable customer and session identity would be
needed to enforce a cumulative cap, and state whether the deployed Harness can
supply that state. Run the Track C evidence collector before teardown so it
exports `agentcore-config.json` while the stack still exists.

## Track C: destroy the AgentCore Terraform root explicitly

The current `scripts/teardown-lab3.sh` cleans up SageMaker endpoints and jobs,
but it does **not** run a Terraform destroy for the separate AgentCore root.
After `collect-lab3-evidence.sh --track C` has successfully written
`agentcore-config.json`, run:

```zsh
terraform -chdir=infrastructure/environments/agent destroy
bash scripts/teardown-lab3.sh
```

Do not reverse this order: AgentCore configuration must be captured while the
Harness, Gateway, and Cedar policy engine still exist. Allow the Terraform
destroy to finish; it is the command that removes the Track C stack.
