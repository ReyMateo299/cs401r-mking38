# Lab 3 instruction suggestions

## Track C teardown handout promises an AgentCore destroy that the script does not perform

**Finding (2026-10-13, verified from the supplied script):** The Track C
teardown guidance says `scripts/teardown-lab3.sh` destroys the AgentCore
Terraform stack. The current script only deletes SageMaker endpoints/configs,
stops in-flight SageMaker jobs, checks MLflow Tracking Servers, and writes the
teardown log. It contains no `terraform` command and no AgentCore Gateway,
Harness, policy-engine, Lambda, IAM-role, or CloudWatch-log cleanup.

**Why this can cost students money:** A student who follows the handout can
receive a successful general teardown message while the AgentCore Harness and
related resources still exist. The Harness has no traffic after evaluation,
but leaving the live stack behind is contrary to the lab's cost-control and
cleanup requirement.

**Belongs in:** Both instructor notes and student tips.

**Suggested revision:** Either add the AgentCore destroy to
`teardown-lab3.sh`, or change the handout to require it explicitly before the
script:

```bash
terraform -chdir=infrastructure/environments/agent destroy
bash scripts/teardown-lab3.sh
```

State that the evidence collector must run first, because it exports the
Harness, Gateway, and Cedar policies that no longer exist after destroy.

## Track C escalation schema conflicts with required scenarios that omit an account ID

**Finding (2026-10-13, verified from the supplied scenarios and tool schema):**
TC-003 and TC-005 require an `escalate_to_human` call, but neither customer
message contains an order or customer ID. The supplied escalation tool schema
requires `customer_id`. A model can therefore correctly recognize that it
should escalate yet decline to call the tool because it lacks a required
argument. The first Harness evaluation also showed the related ambiguity that
a return-policy question without an order ID may be answered with a request for
details before the required `query_policy` call.

**Why this can block students:** The grader records missing required tool calls
as failures. Students can be charged for repeated Harness runs while trying to
infer that a placeholder identifier is permitted, even though the handout does
not state one.

**Belongs in:** Both instructor notes and student tips. The working schema now
makes `customer_id` optional and documents `UNKNOWN` as the value when no
identity is available; the system prompt requires policy lookup before asking
for a missing order ID.

**Suggested revision:** Make `customer_id` optional in the supplied
`escalate_to_human` definition and handler, and add this instruction to Track
C: “For required escalation scenarios without an account identifier, call
`escalate_to_human` with `customer_id: "UNKNOWN"`; do not skip the tool call.
For a return question with a stated tier or elapsed time but no order ID, call
`query_policy` first, then request the missing order information.”

## Track C collector checks a different trace-latency field than the handout requires

**Finding (2026-10-13, verified from the supplied files):** The Track C handout
and `agent/harness_client.py` specify `latency_ms` in each
`docs/lab3-evidence/agent-traces.jsonl` record. However,
`scripts/collect_lab3_evidence.py` validates that at least one record instead
contains a field named `latency`. A trace produced exactly as the starter
client documents can therefore be reported as incomplete by the collector.

**Why this can block students:** Students have no reason to invent a second
field when both the handout and starter client name `latency_ms`. The final
evidence step may then fail after paid Harness runs, creating needless
confusion and a potentially expensive rerun.

**Belongs in:** Both instructor notes and student tips. The working Track C
client records both names as a temporary compatibility measure; `latency_ms`
remains the authoritative documented value.

**Suggested revision:** In `collect_lab3_evidence.py`, change the required key
from `latency` to `latency_ms` (or accept either during the transition):

```python
lacking = [key for key in ("tool", "input", "output", "latency_ms")
           if not any(key in record for record in records)]
```

Then keep the handout and starter client on the single explicit field name
`latency_ms`.

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

## The updated Track A evidence instructions resolve the Athena provenance ambiguity

**Finding (updated 2026-10-13):** The earlier handout said there should be “no CSV path in the data-loading code,” which conflicted with the development-only `--local-data-path` branch in `models/churn/train.py`. The revised Lab 3 guide (added Oct 12) now says CSV is acceptable during development but the graded run must use Athena. It names the required proof: `docs/lab3-evidence/train-final.log` must include an Athena `QueryExecutionId`, and `athena-query.json` must show the actual SQL, `SUCCEEDED`, and bytes scanned. It also explicitly says missing new evidence files do not cost students points in Fall 2026; when repository evidence is absent, the TA should request a short screen-share instead. This supersedes the earlier source-code-only grading decision.

**TA grading procedure:** Check the final-run log and Athena export when present. If they are missing, follow the current guide's Fall 2026 exception and ask the student to screen-share Athena query history rather than retroactively deducting points. Do not mistake an earlier metrics file or an available Athena code path for proof of which loader the graded run used.

**Resolution:** The handout now distinguishes the development CSV path from the graded Athena run, specifies the evidence filenames, and provides a transition policy for this term.

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

## Solution snippets and starter functions need clearer replacement boundaries

**Finding (2026-10-10):** The starter's `evaluate_model(model, X_val, y_val, baseline_proba)` already implements aggregate evaluation and matches the official starter kit. Solution Notes Step 2.4 instead supplies a replacement implementation for the separate `evaluate_slices` stub. Its signature changes from the starter's `evaluate_slices(model, X_val, y_val, slice_column)` to `evaluate_slices(model, X_val, y_val, tiers, min_class_count=20, n_boot=1000, seed=42)`, and its `main()` call uses `tier_val`.

The nearby wording—“Call it from `main()` after `evaluate_model`”—can be read as an instruction to change `evaluate_model` or its call. It means: keep the aggregate evaluation, then add the slice-evaluation call after it.

**Suggested revision:** Label each code block as either **Replace the entire starter function** or **Add immediately after the existing call**. For Step 2.4, explicitly state: “Replace the starter's `evaluate_slices` function, including its signature; leave `evaluate_model` unchanged. Then add `slice_results = evaluate_slices(model, X_val, y_val, tier_val)` immediately after the existing `evaluate_model(...)` call.”

## Reusable command string is bash-specific and fails in zsh

**Finding (2026-10-10):** The Solution Notes define `COMMON="--feature-group-name $FG --artifacts-bucket $BUCKET --mlflow-arn $MLFLOW_APP_ARN"` and later invoke `python models/churn/train.py $COMMON ...`. That is word-split by default in bash, but not in zsh. In zsh, `$COMMON` is passed as one argument, so `argparse` treats all of its text as the value for `--feature-group-name` and then reports the required `--artifacts-bucket` flag as missing.

**Suggested revision:** Mark the command sequence as bash-only, or provide a zsh-safe array form:

```zsh
COMMON=(--feature-group-name "$FG" --artifacts-bucket "$BUCKET" --mlflow-arn "$MLFLOW_APP_ARN")
python models/churn/train.py "${COMMON[@]}" --max-depth 3 --eta 0.1 --num-round 300 --run-name d3-eta0.1
```

Avoid recommending `setopt SH_WORD_SPLIT`; an array preserves argument boundaries without changing shell-wide behavior.

## Older Lab 3 starter defaults exclude current-semester Feature Store records

**Finding (2026-10-10):** An older `churn_training_skeleton.py` sets `--training-start-date 2025-02-01` and `--training-end-date 2026-06-01`. Feature Store `event_time` is when the Lab 2 feature job ran, not the historical feature cutoff. Consequently, a Lab 2 job run in Fall 2026 returns zero Athena rows, even when the Feature Group is correctly populated.

The current starter kit fixes this with defaults of `2026-01-01` through `2027-01-01` and comments explaining why. The Solution Notes describe the new range, but students who downloaded an older kit—or copied only portions of it—do not receive the correction.

**Suggested revision:** Publish the corrected starter kit prominently and add an explicit upgrade callout to the handout:

```bash
python models/churn/train.py ... \
  --training-start-date 2026-01-01 \
  --training-end-date 2027-01-01
```

Also explain that zero rows in the old date window does not by itself mean that a student must rerun Lab 2.

## Pandas 3 string arrays require `to_numpy()` before `train_test_split`

**Finding (2026-10-10):** The starter/solution split example passes `df[SLICE_COLUMN].values` as the third item to `train_test_split`. With pandas 3, a string column's `.values` is an `ArrowStringArray`, not a NumPy array. scikit-learn then attempts to index it with a NumPy index array and raises `TypeError: only integer scalar arrays can be converted to a scalar index`.

**Suggested revision:** Use an explicit NumPy conversion in the starter and solution code:

```python
tiers = df[SLICE_COLUMN].to_numpy(dtype=str)
X_train, X_val, y_train, y_val, tier_train, tier_val = train_test_split(
    X, y, tiers, test_size=0.30, random_state=42, stratify=y,
)
```

This preserves row alignment while working with both older pandas/NumPy-backed strings and pandas 3 Arrow-backed strings.

## Task 1 does not specify durable grading evidence for AWS results

**Finding (2026-10-10):** Task 1 awards points for MLflow runs retrievable with `mlflow.search_runs` and a Model Registry package visible with `PendingManualApproval`, but it does not tell students to save evidence from those AWS services. A TA who grades after teardown or without access to each student's AWS account cannot verify those rubric items from the repository alone. Requiring students to keep infrastructure running during grading would add cost and make grading depend on live account access.

**Suggested revision:** Add a submission checklist asking students to commit a compact `docs/lab3-task1-evidence/` folder containing:

- `evaluation_metrics.json` and `slice_results.json` from the held-out evaluation;
- `mlflow-search-runs.csv` exported by `mlflow.search_runs` (at least three distinct, meaningful runs with parameters and metrics);
- `model-package.json` from `aws sagemaker describe-model-package`, showing `PendingManualApproval` and evaluation metadata;
- the exact training command/configuration and the XGBoost version.

State that these files are grading evidence and that the grader does not need students' infrastructure to remain running. Keep the normal requirements to actually use Athena, the MLflow App, and Model Registry; saved evidence supplements the code and results rather than replacing them.

## Task 1's 5–10 minute grading path should be explicit

**Finding (2026-10-10):** Task 1 has six rubric rows totaling 35 points, but no suggested order or evidence location. A grader can spend time re-reading a long training script or trying to access live AWS resources, even though most criteria can be checked from a few committed files.

**Suggested revision:** Add a short grader-facing evidence map (or publish one with the rubric): inspect the Athena query in the training script; compare the held-out metrics and paired-bootstrap interval in the design document and evaluation JSON; use the exported MLflow search-results CSV for the three-run criterion; use the saved model-package description for approval status and metadata; and use the tier table in the design document or slice-results JSON for per-tier AUC, recall, sample counts, and discussion. Clarify that graders should not require an active Feature Store, MLflow App, or Registry session when the submitted evidence and source code are present.

## Track B solution notes add experiments that the student handout does not specify

**Finding (2026-10-10):** The student handout asks students to implement and evaluate a Track B RAG offer generator against three RAGAS targets. The Solution Notes add two explicit comparisons that the handout does not mention: measure retrieval Options A, B, and C separately against the final two-pass retriever, and compare interpreted shopping signals with a raw-number prompt. The prompt-template file also presents these comparisons as reportable requirements. Students following only the handout can therefore meet its stated evaluation directions while missing expectations described elsewhere.

**Suggested revision:** In the Track B evaluation section of the handout, either list these two comparisons as required deliverables (including that the final two-pass design is compared with A/B/C), or label them as optional experiments in both the Solution Notes and prompt-template checklist. State that the retrieval comparison should report context recall for each strategy and the prompt ablation should report the same metrics for both signal modes.

## Track B rubric names a demo notebook but the solution demonstrates a Python script

**Finding (2026-10-10):** The student handout's System runs end-to-end rubric row says the TA executes the “demo notebook.” The Solution Notes' Track B implementation and evaluation path instead uses `rag/offer.py` and `rag/evaluate.py`; it does not identify or provide a Track B demo notebook. This leaves students unsure which runnable artifact the TA expects and may cause graders to apply a notebook requirement that the solution does not satisfy.

**Suggested revision:** Change the rubric wording to “TA can run the documented Track B entry point (notebook or Python script) and generate a valid offer,” and name the expected command and required output. If a notebook is truly required, add its path and instructions to the Solution Notes and starter kit.

## Clarify the fifth offer example and the shape of each output

**Finding (2026-10-10):** The handout requires five input/output pairs, while its supplied harness contains four built-in Track B cases. The Solution Notes correctly call out the need to add a fifth case, but students may mistake the four-row harness output for the complete deliverable. There is also a small output-shape ambiguity: the handout calls for a 2–3 sentence offer, while the revised prompt asks for a subject, a 2–3 sentence body, and a rationale.

**Suggested revision:** State directly in the handout that students must add one local test case without editing the shared harness and submit five customer inputs with their generated offers. Define that the *body* must be 2–3 sentences; a subject line and one-sentence rationale may be included outside the body.

## Solution Notes ask students to report token counts without making that a handout criterion

**Finding (2026-10-10):** Step 4B.5 asks students to include generation-model token counts when justifying their choice. The student handout asks students to justify the generation model but does not request token counts in Task 2 or its rubric. This is an additional documentation expectation that may be graded inconsistently.

**Suggested revision:** Either add input/output token counts to the Track B design-document checklist, or mark them as an optional cost-analysis detail in the Solution Notes. Specify whether the counts should cover one offer or the full evaluation run.

## The output requirements should separate offer expiry from the return window

**Finding (2026-10-10):** The policy allows a retention offer to be redeemed within 45 days of issue, but Gold members still have only 30 calendar days to return eligible merchandise. An offer that says “use anytime in the next 45 days” immediately before inviting the customer to ship items back can sound like a 45-day return window. The prompt template also requires a call to action, while the student handout does not state that requirement explicitly.

**Suggested revision:** Add a direct constraint to the student-facing Track B instructions and prompt: “The retention offer's 45-day validity is only the deadline to redeem the offer; it does not change the customer's return window. State return eligibility and deadlines separately, and include a clear call to action.” Example wording: “Redeem this offer within 45 days of issue. Eligible Gold returns remain subject to the standard 30-day return window.”

## The starter prompt leaves room for invented campaign terms

**Finding (2026-10-10):** In a completed five-case run, the generator invented a 10-point bonus, a `$50` purchase threshold, and a `$5 off apparel` birthday promotion. The prompt says not to invent promotions, but also asks for a “specific incentive” and does not explicitly forbid unprovided bonus points, minimum spends, customer reward balances, or unused credits. The generated rationale then repeated unsupported claims such as an accumulated rewards balance. A borderline Silver case also implied the customer was `$15` from Gold based on lifetime value, although policy uses trailing-12-month spend.

**Suggested revision:** Expand the prompt checklist with explicit examples: do not invent bonus points, coupons, purchase minimums, reward balances, birthdays, unused credits, or offer dates; do not call an existing tier benefit exclusive; and do not infer distance to a tier threshold from lifetime value. Require the system to use only a supplied campaign incentive or describe an existing tier benefit as an existing benefit. Keep internal rationale out of the customer-facing output or require every rationale claim to be grounded in supplied profile data and policy.

## The RAGAS judge can truncate outputs and produce incomplete means

**Finding (2026-10-10):** The supplied five-case comparison emitted multiple `LLMDidNotFinishException` warnings. The final two-pass faithfulness results had valid scores for only two of five cases; the displayed mean of `0.080` silently excluded three `NaN` values. This makes a metric average look complete when the judge actually failed on most examples.

**Suggested revision:** Configure the Bedrock judge with an explicit adequate output-token limit, and have the evaluator report the number of valid scores per metric (for example, `2/5`). Treat any metric with missing scores as incomplete and rerun it before using the mean. Keep offer generation and judge token limits separate, since the exception comes from the RAGAS judge.

## The two-pass query should explicitly retrieve standard return-window rules

**Finding (2026-10-10):** The retrieved two-pass contexts included the tier-benefit table, retention-offer validity, and final-sale exclusions, but the observed context set did not include POL-RET-004 §1, which defines the standard 30-day return window. The constraint query named final sale and offer validity but omitted the exact return-window terms. The five-case context-recall mean was `0.62`, below the `0.70` target.

**Suggested revision:** Include terms for “30 calendar days from delivery or purchase,” “Platinum 60 days,” and the fact that offer validity does not extend the return window in the constraint query. Ask students to inspect the retrieved source sections when context recall misses the rubric's tier/window facts, then retune `k` or the query before concluding that re-ranking is unnecessary.

## Track C harness passes scenarios without checking the reply's policy correctness

**Finding (2026-10-11):** The student handout says that conceding or even hinting at an exception for the final-sale item in TC-005 is a failure. The shared `LocalAgentEvaluator`, however, uses `expected_behavior` only as descriptive text: it checks required/forbidden tool names and whether escalation was detected. `detect_escalation()` treats `escalate_to_human` or certain phrases as sufficient, but does not check whether the response cites POL-RET-004 §4, clearly declines the return, or implies that an exception may be granted. A real run passed TC-005 even though its reply omitted the policy citation and told the customer a human could “explore other options.” A subsequent run after adding a stricter prompt still ended with the final post-tool reply saying a human could “discuss what options may be available.” This shows that the final customer-facing turn needs a check of its own; an earlier compliant message before a tool call is not enough. Conversely, the same broad phrase detector marked TC-006 as escalated when the reply only listed escalation as a general capability and made no escalation tool call. The local evaluator now bases escalation on the actual tool call; its previous CSV result was corrected offline, without rerunning the model.

**Suggested revision:** Extend the Track C evaluation criteria with explicit response checks for TC-003 through TC-005, or label those rows as requiring TA review. For TC-005, inspect the final reply after all tool results and require a citation to POL-RET-004 §4, an unambiguous statement that final-sale merchandise is not returnable at any tier, a call to `escalate_to_human`, and no promise or implication that the return will be approved. For the local ReAct evaluator, count escalation only when the handoff tool is called; a generic mention in the reply is not an executed handoff. Keep `expected_behavior` as grader guidance only if the harness does not actually evaluate it; make that limitation visible in the output and rubric.

## Track C tool list does not identify escalation as a tool

**Finding (2026-10-11):** The main handout lists `lookup_order` and `query_policy` as required tools and `initiate_return` / `apply_loyalty_credit` as optional, while separately requiring an explicit escalation path. The Solution Notes implement `escalate_to_human` as a tool and explain why a sentence promising escalation is not an operational handoff. Students can satisfy the literal tool list without implementing the solution's explicit handoff behavior, and the harness's prose-based fallback makes this ambiguity harder to notice.

**Suggested revision:** List `escalate_to_human(reason, summary)` as a required tool alongside the minimum tool count, and state that an escalation must be recorded as a tool call in scenarios requiring handoff. If prose-only escalation is intentionally acceptable, document how the student must demonstrate that the handoff actually occurs.

## Professor withdrew the Track B RAGAS score thresholds for Fall 2026

**Finding (2026-10-13, based on the professor's update):** The earlier handout and local harness present faithfulness 0.80, answer relevancy 0.75, and context recall 0.70 as targets, and the harness prints PASS/FAIL against them. The professor says these targets are no longer graded because the harness ground truths include claims absent from the corpus and answer relevancy does not fit offer generation. The revised 15-point evidence is: five points for all four cases at least twice with per-case scores, mean, range, and judge model; six points for explaining each metric's limits with case/claim examples; four points for one measured before/after pipeline change. The supplied two-pass five-case comparison has valid scores but fell well below the old thresholds; that is not a grading failure under the revision.

**Suggested revision:** Replace every student-facing pass threshold and below-target failure warning with the revised three-part rubric. Clarify whether the existing five-example deliverable remains separate from the four supplied evaluation cases. Update the harness to stop printing graded PASS/FAIL labels, save per-case scores across at least two runs, report means/ranges and judge model, and allow the customer profile to be included as a distinct judge context. Keep failed judge calls (`NaN`) marked as missing and rerun them; do not coerce them to zero. The working-repository tips and prompt checklist now reflect this change; instructor files remain untouched.

## Track B needs a precise rule for policy-duration language versus a concrete offer deadline

**Finding (2026-10-13; verified against POL-LOY-011 §5.1 and the saved local examples):** The policy says a retention offer is valid for 45 days *from issue*, while the template correctly says not to invent expiration dates. The distinction is not made explicit. Saved raw offers consequently use language such as “within the next 45 days” even though the supplied profile has no issue timestamp, and an older capture adds “any of our 400 locations” even when that operational fact does not personalize the offer. The 45-day rule and 400-location fact exist in the corpus, but neither is automatically an individualized claim.

**Why it confuses or blocks students:** A student can reasonably read “no expiration dates” as forbidding the documented 45-day policy, or can use the policy as license to invent a calendar deadline. This makes it hard to distinguish a supported policy statement from an unsupported assertion about this customer's offer.

**Belongs in:** Both instructor notes and student tips.

**Suggested revision:** Add this explicit guardrail to the handout and starter prompt: “You may state the policy duration only as ‘valid for 45 days from issue’ when the retention-offer policy chunk is retrieved. Do not state a calendar expiry or ‘next 45 days’ unless an offer issue date is supplied. Do not use general operational facts, such as store count, as personalization unless the request needs them and the supporting chunk was retrieved.” Include one compliant and one noncompliant example.

## Track C handout and solution notes prescribe incompatible architectures

**Finding (2026-10-13; verified from the current handout, current starter kit, and solution notes):** The current handout requires Amazon Bedrock AgentCore—an AgentCore Harness, Gateway, Lambda target, Cedar policy engine, and a separate Terraform root—and explicitly says to use AgentCore only. The Solution Notes instead say AgentCore's predecessor, managed Bedrock Agents, is unavailable and direct students to build a client-side ReAct loop over `bedrock-runtime`; the local evaluation harness follows that older route. The working repository consequently contained only the local loop and lacked the handout's Track C starter files (`infrastructure/environments/agent/`, `harness_client.py`, and `policy_tests.py`).

**Why it confuses or blocks students:** These are materially different systems, IAM permissions, costs, deployment commands, evidence files, and teardown procedures. A student following the solution notes can build a working local agent yet fail the current handout's AgentCore deployment and Cedar-cap evidence requirements. A student following the handout cannot use the provided local runner as their end-to-end agent without an AgentCore adapter.

**Belongs in:** Instructor notes; student tips only after the professor names the intended path.

**Suggested revision:** Publish one dated Track C path and archive or relabel the other. If AgentCore is the current requirement, replace the local-ReAct instructions in the Solution Notes and evaluator with the Harness client path, include the complete AgentCore starter files in every student repository, and list the exact evidence commands. If local ReAct remains acceptable, remove the mandatory AgentCore/Terraform/Cedar requirements and make the failure/evidence rubric match it. Until clarified, state that the dated handout is authoritative and that the local loop is optional preparation rather than the graded architecture.
