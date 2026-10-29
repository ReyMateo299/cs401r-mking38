# Lab 3 student tips and troubleshooting guide

This is a practical companion to the Lab 3 handout and starter kit. Start with
the question that matches where you are stuck, then read the linked section.
The current Lab 3 handout is the grading authority; these tips explain common
setup, evidence, and platform issues without replacing it.

## Quick route: where should I start?

| If your question is… | Go to… |
|---|---|
| “What am I building, and which track should I choose?” | [Lab map and prerequisites](#lab-map-and-prerequisites) |
| “Where do the starter-kit files belong?” | [Place the starter kit correctly](#place-the-starter-kit-correctly) |
| “Can I start if I tore down Lab 2?” | [Check the Labs 1–2 platform first](#check-the-labs-12-platform-first) |
| “Which packages or tools do I need?” | [Set up a compatible local environment](#set-up-a-compatible-local-environment) |
| “Athena returned zero rows / Feature Store is empty.” | [Fix Task A data-access problems](#fix-task-a-data-access-problems) |
| “`train_test_split` throws a pandas 3 error.” | [Fix Task A data-access problems](#fix-task-a-data-access-problems) |
| “How do aggregate metrics and tier slices fit together?” | [Complete Task A correctly](#complete-task-a-correctly) |
| “How do I run and interpret Track B RAGAS?” | [Complete Track B: offer-generation RAG](#complete-track-b-offer-generation-rag) |
| “RAGAS returned `NaN` or `LLMDidNotFinishException`.” | [Complete Track B: offer-generation RAG](#complete-track-b-offer-generation-rag) |
| “What does Track C need, and why is AgentCore involved?” | [Complete Track C: customer-service agent](#complete-track-c-customer-service-agent) |
| “Which files must I save before teardown?” | [Capture evidence and prepare submission](#capture-evidence-and-prepare-submission) |
| “The collector cannot find an Athena query ID on Windows.” | [PowerShell and UTF-8 evidence logs](#powershell-and-utf-8-evidence-logs) |
| “What can I safely delete, and in what order?” | [Teardown without losing needed evidence](#teardown-without-losing-needed-evidence) |

## Lab map and prerequisites

Lab 3 has four parts:

1. **Task A (required):** train and evaluate a churn model using the Lab 2
   Feature Store offline store through Athena.
2. **Task B or Task C (choose one for the graded track):** build either the
   offer-generation RAG system or the customer-service agent.
3. **Task 3:** write `docs/lab3-model-design.md` with your design reasoning.
4. **Task 4:** preserve evidence, update the README, verify Bedrock access,
   and tear down billable resources.

Track B uses churn risk and customer-profile data, so it depends on Task A and
the Lab 2 data platform. Track C's agent does not itself need the Feature
Store, MLflow, Model Registry, a SageMaker endpoint, or Studio, but Task A is
still required for everyone.

Before beginning Bedrock work, make sure the Pre-Lab 3 verification file
exists at `docs/bedrock-access-verification.txt` and contains its two `PASS`
lines. If your first Claude call reports a zero daily-token quota or persistent
`ThrottlingException`, open an AWS Support case early; Task A can continue
while Bedrock access is resolved. Do not put credentials in that file, your
shell history, or the repo.

## Place the starter kit correctly

Add the Lab 3 starter kit to the repository you started in Lab 1. Do not make a
separate Lab 3 repository and do not overwrite your existing Labs 1–2 work.

```text
churn_training_skeleton.py                  → models/churn/train.py (or retain its name)
evaluation_harness.py                        → evaluation/evaluation_harness.py
prompt_templates/offer_generation_prompts.md → prompt_templates/offer_generation_prompts.md
northstar-policy-docs/                       → northstar-policy-docs/
scripts/collect-lab3-evidence.sh             → scripts/collect-lab3-evidence.sh
scripts/teardown-lab3.sh                     → scripts/teardown-lab3.sh
```

Create missing folders as needed and commit the starter files with your work.
Task A uses the churn-training script; the AWS console and CLI support that
work but do not replace the required Python implementation.

If you choose Track C, also copy its `agent/` directory and the separate
`infrastructure/environments/agent/` Terraform root. Do not modify the Labs
1–2 Terraform root to add AgentCore resources: it uses an older AWS-provider
major version that does not contain them.

## Check the Labs 1–2 platform first

The MLflow App needs an S3 artifact location and a SageMaker execution role.
For this course, both come from the Labs 1–2 Terraform stack. Use Terraform
outputs rather than guessing resource names:

```bash
cd infrastructure/environments/dev
export BUCKET=$(terraform output -raw s3_bucket_name)
export ROLE_ARN=$(terraform output -raw ml_engineer_role_arn)
cd -
```

Create the free MLflow App with an artifact path the course role can write:

```bash
aws sagemaker create-mlflow-app \
  --name northstar-mlflow \
  --artifact-store-uri "s3://${BUCKET}/artifacts/mlflow/" \
  --role-arn "$ROLE_ARN"
```

The `MLEngineer` role is intentionally scoped to `artifacts/` and `features/`.
A bucket-root or `mlflow/` artifact path may create an app but fail later when
MLflow writes an artifact. An MLflow App does not require a Studio domain, but
the bucket and role must exist.

### I already tore down Lab 2. Can I still do Lab 3?

Yes, but reapply Lab 2 and repopulate its data first. `teardown-lab2.sh` empties
every object version in the data bucket and destroys the Feature Group;
Terraform can recreate infrastructure, but not the deleted data.

The normal recovery is to re-run the Lab 2 pipeline. If you retained the
processed Parquet snapshot, upload it after reapplying Terraform and rerun the
**feature-engineering** Glue job. Uploading processed data alone does not
restore Feature Store records or the Athena-queryable offline store.

Check that the Feature Group and its offline store exist:

```bash
cd infrastructure/environments/dev
export FG=$(terraform output -raw feature_group_name)
aws sagemaker describe-feature-group --feature-group-name "$FG" \
  --query '{featureGroup:FeatureGroupStatus, offlineStore:OfflineStoreStatus.Status, database:OfflineStoreConfig.DataCatalogConfig.Database, table:OfflineStoreConfig.DataCatalogConfig.TableName}' \
  --output table
cd -
```

You want `Created`, `Active`, and a database/table name. Then use Athena to
check for actual records:

```sql
SELECT COUNT(*) AS feature_rows
FROM "sagemaker_featurestore"."YOUR_OFFLINE_STORE_TABLE";
```

If the count is zero, rerun the Lab 2 feature-engineering job. If the table is
missing, reapply the stack first and then repopulate it.

### What survives a Lab 2 teardown?

The MLflow App and its run metadata can remain, but its artifacts live in the
Lab 2 data bucket. A Lab 2 teardown permanently removes those S3 artifacts and
can leave registry metadata pointing at deleted model files. Keep the Lab 2
stack until you have captured Lab 3 evidence and no longer need its data.

## Set up a compatible local environment

Create a project virtual environment and use the tested dependency bounds:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install "sagemaker>=2.200.0,<3.0.0" xgboost scikit-learn pandas numpy boto3 \
            mlflow sagemaker-mlflow matplotlib
# Track B only:
pip install faiss-cpu ragas datasets "langchain-community<0.4" langchain-aws
python -c "from sagemaker.feature_store.feature_group import FeatureGroup; import mlflow, sagemaker_mlflow; print('imports OK')"
```

SageMaker SDK 3.x removed the Feature Store module Task A imports.
`sagemaker-mlflow` provides the SageMaker MLflow authentication integration,
and newer `langchain-community` releases can break the RAGAS imports. Commit
your resulting dependency constraints so a fresh environment can reproduce
your work.

On macOS, if `import xgboost` reports a missing `libomp.dylib`, install OpenMP
once at the system level:

```bash
brew install libomp
source .venv/bin/activate
python -c "import xgboost; print(xgboost.__version__)"
```

Track C additionally requires boto3 1.43.57+, AWS CLI **v2** 2.36+, and
Terraform 1.7.5+. `aws-cli/1...` is not sufficient.

For Track C cost control, keep the starter Harness setting
`idle_session_timeout_seconds = 60`. A reference Harness session costs roughly
$0.003 at that setting but roughly $0.018 at the AWS default 900-second idle
timeout. A deployed stack with no active sessions does not itself bill.

## Complete Task A correctly

The required training path is Python code that queries the Feature Store
offline table through Athena. A local CSV or direct Parquet read can help while
developing, but it is not the graded run. Your final run should:

- pass hyperparameters and paths as arguments rather than hardcoding them;
- log at least three varied MLflow runs with parameters and metrics;
- register the selected model as `PendingManualApproval`, never `Approved`;
- report held-out precision and recall at the global top 10%, the recency-only
  baseline, lift, and a 95% confidence interval; and
- report tier slices with each tier's `n`, positives, AUC, recall, and any
  reliability limitation.

### How do aggregate metrics and tier slices fit together?

Keep the aggregate `evaluate_model(...)` call. It produces the overall metrics
and the recency-baseline confidence interval. Add slice evaluation separately
after that call:

```python
slice_results = evaluate_slices(model, X_val, y_val, tier_val)
```

Carry `tier_val` through the same `train_test_split` as `X` and `y`; this
preserves row alignment. Then pass `slice_results` to tracking and model
registration if your starter functions accept it.

## Fix Task A data-access problems

### `train_test_split` fails after upgrading pandas

If you see `TypeError: only integer scalar arrays can be converted to a scalar
index`, the loyalty-tier series may be a pandas 3 Arrow-backed string array.
Convert it before splitting:

```python
tiers = df[SLICE_COLUMN].to_numpy(dtype=str)
X_train, X_val, y_train, y_val, tier_train, tier_val = train_test_split(
    X, y, tiers, test_size=0.30, random_state=42, stratify=y,
)
```

### Athena returns zero rows

`event_time` is the feature-engineering run time, not the historical cutoff
date used to create features. A narrow or stale date window can exclude valid
current-semester records. Use the semester-wide dates when needed:

```bash
python models/churn/train.py "${COMMON[@]}" \
  --training-start-date 2026-01-01 --training-end-date 2027-01-01 \
  --max-depth 3 --eta 0.1 --num-round 300 --run-name d3-eta0.1
```

Confirm the Feature Store has data before rerunning the Lab 2 pipeline.

### macOS zsh says an argument is missing even though it is in `COMMON`

In zsh, a reusable command string is passed as one argument. Use an array:

```zsh
COMMON=(--feature-group-name "$FG" --artifacts-bucket "$BUCKET" --mlflow-arn "$MLFLOW_APP_ARN")
python models/churn/train.py "${COMMON[@]}" --max-depth 3 --eta 0.1 --num-round 300 --run-name d3-eta0.1
```

Or put every flag directly in the command. The SageMaker SDK v2 deprecation
warning is expected and unrelated to an `argparse` error.

## Complete Track B: offer-generation RAG

Run the supplied four cases at least twice and save the raw output:

```bash
source .venv/bin/activate
python rag/evaluate.py
```

The Fall 2026 RAGAS target numbers are **not** graded. Credit comes from a
complete, honest evaluation:

- report per-case scores, means, ranges, and the judge model;
- explain a specific limitation of faithfulness, answer relevancy, and context
  recall; and
- measure one pipeline change before and after, even if it did not help every
  metric.

The provided local runner compares the same pipeline before and after adding
the customer profile as an explicit judge context. It writes detailed scores to
`docs/lab3-evidence/rag_eval.csv`, summaries to
`docs/lab3-ragas-summary.csv`, and generated answers plus contexts to
`docs/lab3-rag-comparison-examples.json`.

Before you use Template 3's tier block, compare every threshold and shipping
benefit with the policy corpus. It contains three deliberate factual errors.
The point is to catch policy drift in marketing-style copy, not to inject the
block unchanged and hope retrieval corrects it.

This run calls Bedrock for embeddings, generation, and judging, so it can cost
money. Verify the AWS profile and network before running it. With IAM Identity
Center, authenticate in the same terminal, for example:

```bash
aws sso login --profile YOUR_PROFILE
export AWS_PROFILE=YOUR_PROFILE
```

If you write your own RAGAS call, pass the Bedrock `llm=` and `embeddings=`
objects explicitly. Otherwise RAGAS defaults to OpenAI, and the course does
not provide an OpenAI key. For Claude 4.5+, use the cross-region `us.`
inference-profile ID, such as
`us.anthropic.claude-haiku-4-5-20251001-v1:0`; the bare model ID is rejected.
Set `temperature` **or** `topP`, never both.

### How should I interpret weak RAGAS scores?

- **Faithfulness:** the judge cannot support profile facts unless the profile
  is included as a labeled context. Filler, invented deadlines, and invented
  account state also hurt this metric.
- **Answer relevancy:** the input is an instruction to write an offer, not a
  normal customer question. A relevant marketing offer can therefore score
  poorly on a question-answering metric.
- **Context recall:** supplied ground truths include claims absent from the
  policy corpus. Retrieval cannot produce supporting evidence that does not
  exist in the corpus.

Also submit five input/output pairs and at least two documented failure cases
with concrete fixes in `docs/lab3-evidence/track-b-examples.md`. The fifth
example is your own case; the harness only supplies four. Preserve each
retrieved context identifier with the example.

### RAGAS reports `NaN` or `LLMDidNotFinishException`

A `NaN` is missing evidence, not a score of zero. The RAGAS judge can run out
of output tokens while scoring long contexts. The local `rag/evaluate.py`
already configures its judge with an explicit 4096-token output budget. Check
that your local version retains that setting, then rerun only incomplete cases
and do not average a metric until every required value is valid.

### What claims are unsafe in a generated offer?

Do not invent coupons, bonus points, purchase minimums, birthday rewards,
available balances, unused credits, or calendar deadlines. A 45-day retention
offer is valid **from issue**; it does not change the return window and is not
an individualized date unless an issue date is known. Do not call a standing
tier benefit “exclusive” unless the campaign establishes that it is exclusive.

The feature-store tier is based on lifetime value, while policy eligibility is
based on trailing-12-month spend. Do not infer that a customer is a stated
amount away from the next tier. Use the system of record in production; until
then, phrase near-threshold tier information conditionally.

## Complete Track C: customer-service agent

The current handout's Track C path uses **Amazon Bedrock AgentCore**: a
Harness, IAM-authenticated Gateway, Lambda tools, and Cedar policy enforcement.
Use the current handout and supplied AgentCore starter files. If an older
document tells you to use managed Bedrock Agents or only a local ReAct loop,
ask course staff which dated path applies before deploying anything.

After applying the AgentCore Terraform root, run the direct policy probe first,
then the Harness evaluator:

```bash
source .venv/bin/activate
python agent/policy_tests.py
python -m agent.evaluate
```

The seven policy tests must show the expected allow/deny decisions. The agent
evaluator runs the five required scenarios twice. It writes:

- `docs/lab3-evidence/policy-tests.json`
- `docs/lab3-evidence/agent_eval.csv`
- `docs/lab3-evidence/agent-traces.jsonl`
- `docs/lab3-evidence/agent-cost.csv`

These calls use deployed AWS services and can incur charges. They do not
replace Track B evidence files.

The expected AgentCore path was announced on October 14. If you began Track C
from an older local-ReAct starter before that announcement, stop and contact
course staff for grading direction rather than trying to combine the two
architectures.

If an AgentCore apply or first call returns `AccessDenied` immediately after
you added the named permission, wait about a minute for IAM propagation before
changing Terraform or the prompt. The current kit already uses the required
`us.` Claude 4.5 inference profile; do not replace it with the bare model ID
or legacy Claude 3 Haiku.

### What should I inspect beyond an automated PASS?

Review both repetitions, especially these scenarios:

- **TC-002:** retrieve the actual 30-day return rule and the applicable
  shipping fee before asserting eligibility.
- **TC-003:** an out-of-window request requires a policy lookup and a recorded
  escalation; text saying “I will escalate” is not a tool call.
- **TC-004:** ask for needed clarification without promising a refund.
- **TC-005:** cite `POL-RET-004 §4`, plainly decline the final-sale return,
  avoid implying an exception is possible, and call `escalate_to_human`.

The TC-003 and TC-005 prompts do not provide a customer ID but still require a
recorded escalation. Make the escalation tool accept an absent ID and pass
`customer_id: "UNKNOWN"`; do not omit the tool call.

One required failure analysis is the split-credit hole: two individually
allowed $40 credits can exceed a $50 cumulative limit. A per-call Cedar rule
does not remember earlier calls. Explain in `track-c-failures.md` that a
durable ledger or session-aware/temporal control with customer identity is
needed for a cumulative limit.

## Capture evidence and prepare submission

Keep evidence in the exact required locations. At minimum, preserve:

- Task A training log, metrics JSON, slice CSV, plots, and evaluation report;
- the demo notebook saved after one clean Restart and Run All;
- Track B **or** Track C required evidence files;
- `docs/lab3-model-design.md` and `docs/bedrock-access-verification.txt`; and
- the collector report and final teardown output.

For Fall 2026, a missing newly introduced evidence export does not by itself
lose points: a TA may confirm the item in a short screen-share. Still run the
collector and commit its output whenever possible; it is the fastest way to
make a post-teardown submission easy to grade.

For a final Athena-backed Task A run, omit `--local-data-path`, use
`--output-data-dir docs/lab3-evidence`, and save console output to
`docs/lab3-evidence/train-final.log`. The log must contain the exact line:

```text
Athena QueryExecutionId: <36-character UUID>
```

Before teardown, run the collector for your graded track:

```bash
bash scripts/collect-lab3-evidence.sh --track B
# or
bash scripts/collect-lab3-evidence.sh --track C
```

It exports AWS-side proof such as the Athena query, MLflow runs, registry
versions, and—on Track C—the AgentCore configuration. Fix a `FAIL` before
teardown. A `WARN` needs review, but is not automatically blocking. Keep the
collector output in the repository so a TA can grade after your AWS resources
are gone.

After teardown, commit the intended work and tag that commit:

```bash
git tag lab3-submit
git push origin lab3-submit
```

The TA grades the `lab3-submit` tag, not later commits on your default branch.

## PowerShell and UTF-8 evidence logs

The handout's Bash command using `2>&1 | tee ...` is not reliably portable to
Windows PowerShell. In Windows PowerShell 5.1, `tee` maps to `Tee-Object` and
can write a UTF-16 log. The log can look correct in an editor while the
collector cannot match the ASCII text `Athena QueryExecutionId: ...` because
UTF-16 inserts null bytes between characters.

Use a UTF-8 terminal/output setting (PowerShell 7 is a practical option) or
save/convert `docs/lab3-evidence/train-final.log` as UTF-8 before running the
collector. Do not hardcode a query ID: the collector also looks that UUID up
in Athena and verifies the query. If the line is visibly present but the
collector says it is missing, report your PowerShell version and capture
command to course staff; this is an encoding issue, not evidence that the
Athena query failed.

## Teardown without losing needed evidence

Do not tear down resources until the collector has completed successfully and
all local evidence files are saved. `teardown-lab3.sh` removes billable
SageMaker endpoints/configurations and stops active jobs while retaining the
free MLflow App and Model Registry records.

For Track C, capture AgentCore evidence first. The **current** starter-kit
version of `scripts/teardown-lab3.sh` then destroys the separate AgentCore
Terraform root, deletes the Harness runtime log group, and verifies that no
Harnesses, Gateways, policy engines, or runtimes remain:

```bash
bash scripts/teardown-lab3.sh
```

If your local script does not include a Track C destruction step, it is an
older copy. Refresh it from the current starter kit rather than assuming the
generic SageMaker cleanup also removes AgentCore resources. The AgentCore
destroy can take about five minutes; let it finish.

Do not run the Lab 2 teardown until you are ready to delete the Feature Store,
data bucket, and S3-backed MLflow artifacts. When all evidence is committed,
create the required submission tag from the commit you intend to submit.
