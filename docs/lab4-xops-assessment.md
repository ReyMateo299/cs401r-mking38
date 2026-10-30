# Lab 4 — XOps Assessment (NorthStar churn platform)

## Pipeline Stage Mapping

Implementation: AWS CodePipeline + CodeBuild (`pipeline.yaml`, `buildspec.yml`).
All five phases run in order, in three CodePipeline stages:

| Phase | CodePipeline stage | Where it runs |
|---|---|---|
| Source | `Source` | CodeConnections (GitHub App) on `main`, `DetectChanges: true` |
| Test | `Build` | `buildspec.yml` `pre_build`: `tests/test_data.py` (28) and `tests/test_features.py` (24); any failure stops the build before training |
| Build | `Build` | `build`: `models/churn/pipeline_definition.py` upserts and starts the SageMaker Pipeline; `TrainChurnModel` runs `churn_model.train()` on managed spot `ml.m5.large` |
| Evaluate | `Build` | Inside training, `evaluate_model()` raises on a failed gate, so the model never registers. Then CodeBuild runs `tests/test_model.py` (gates + champion regression) and `tests/test_fairness.py` against the emitted metrics |
| Register | `Build` → `ManualApproval` | `RegisterChurnModel` registers the package as `PendingManualApproval`; a human approves it in the SNS-notified `ManualApproval` stage. If a CodeBuild-only test fails after registration, `post_build` sets that package to `Rejected` |

Why three stages, not five: a CodePipeline stage is a hand-off and approval
boundary. Splitting Test, Build and Evaluate into separate stages would mean
passing the model artifact between stages and a CodeBuild project per stage,
for no gain. The order is still enforced: CodeBuild phases run in sequence and
a failed phase halts the build. `docs/lab4-failure-demo.txt` shows a
`PRE_BUILD` failure with no `BUILD` phase and no new package.

Why CodePipeline over GitHub Actions: no AWS credentials stored in GitHub (the
GitHub App connection and IAM roles do it), a native manual-approval action
wired to SNS, and every step runs in the same account under IAM roles that
Terraform and CloudFormation define.

Note on triggering: pushes did not start the pipeline until the "AWS Connector
for GitHub" app was installed on the repository, not just authorized. The
failure-demo runs were started with `start-pipeline-execution`. After the
install, the revert push (`8a3c5bc`) triggered the final green run as a
`Webhook` execution (`docs/lab4-pipeline-runs.txt`).

## Champion-Challenger

A challenger replaces the champion if and only if all three hold:

1. It passes the promotion gates: P@10 ≥ 0.50, R@10 ≥ 0.25, and the 95% CI on
   (AUC − recency-baseline AUC) has a lower bound > 0. Enforced in
   `models/churn/churn_model.py`: `evaluate_model()` raises, so a failing
   model is never registered.
2. AUC_challenger ≥ AUC_champion − 0.02, where the champion is the newest
   Approved package. Enforced in CI by `regresses()` in `tests/test_model.py`.
   The final green run logged `champion v5 auc=0.7855; candidate
   auc=0.7855`.
3. No reliable loyalty tier (≥ 20 positives and ≥ 20 negatives) loses more
   than 0.05 AUC against the champion's same tier. The human approver checks
   this at the ManualApproval stage, from `slice_results` in the metrics file
   the package's ModelMetrics points to in S3.

Why −0.02 and not "any improvement": AUC moves with the train/validation split
alone. In the handout's 200-split sweep, the same model fell below a fixed 0.72
bar on 58% of splits. My own model scored 0.7777 locally (xgboost 3.2) and
0.7855 in the container (xgboost 1.7) on identical data. A "+0.005 better" rule
would be decided by noise. Weekly retraining on fresh data also has to be able
to replace a champion measured on older data; −0.02 allows that while refusing
a material regression.

## Retraining Triggers

Both triggers start the same CodePipeline, `northstar-pipeline`, so every
retrain passes the same tests, gates and champion check as a code push. Both
are designed, not deployed.

**(a) Scheduled: weekly, chained to fresh features.**

- An AWS Glue trigger (`SCHEDULED`, `cron(0 6 ? * MON *)`, Mondays 06:00 UTC)
  runs `northstar-dev-feature-engineer`.
- An Amazon EventBridge rule matches `source: aws.glue`, `detail-type: Glue Job
  State Change`, `jobName: northstar-dev-feature-engineer`, `state: SUCCEEDED`.
  Its target is CodePipeline `northstar-pipeline`, using an IAM role allowed to
  call `codepipeline:StartPipelineExecution`.
- It is chained to the job, not to the clock: a bare weekly cron on the
  pipeline would trip the 48-hour freshness test in `tests/test_data.py`
  whenever the feature job ran late or failed.

**(b) Performance-based: a lagging and a leading signal.** Churn labels arrive
90 days after the cutoff (the holdout window is 2026-04-01 to 2026-06-30), so
production AUC can only be measured late. One signal measures that late
outcome directly; the other gives early warning from the inputs.

- **Lagging (measured performance).** An Amazon EventBridge Scheduler schedule
  (`rate(30 days)`) invokes an AWS Lambda function. It scores customers whose
  90-day outcome window has closed, computes AUC against their actual churn,
  and publishes the CloudWatch metric `NorthStar/Model ProductionAUC`. A
  CloudWatch alarm fires when `ProductionAUC < 0.72` for 1 datapoint. 0.72 is
  the recency-only baseline (0.7233 on my validation split): below it, the
  model is worse than the free rule it was promoted to beat.
- **Leading (input drift).** Lab 6's drift job publishes the Population
  Stability Index of `days_since_last_purchase` against the training
  distribution. A CloudWatch alarm fires at `PSI > 0.2`, the conventional
  "significant shift" level.
- Either alarm entering `ALARM` matches an Amazon EventBridge rule on
  `CloudWatch Alarm State Change` (`state.value = ALARM`), which starts
  `northstar-pipeline`. The same alarms notify the existing SNS topic
  `northstar-model-approvals`, so a human sees why the retrain happened.

## DataOps Maturity

Current level: 2

Evidence: The data pipeline is code. `infrastructure/modules/glue/main.tf`
defines the crawler and both Glue jobs. `glue-scripts/transform.py` and
`glue-scripts/feature_engineer.py` assert producer-side quality gates (no null
IDs or dates, no duplicate transactions, churn rate 5–50%, all four tiers
present) and fail the job instead of shipping bad features. The contract is
written down in `docs/lab2-data-contract.md`. Lab 4 adds consumer-side gates:
`tests/test_data.py` runs 28 checks in CodeBuild `pre_build` on every push,
including a 48-hour freshness gate and a leakage test that recomputes
recency, tenure and frequency from purchases on or before the cutoff and
requires an exact match. Feature logic is unit-testable through the pandas
port `data/feature_engineering.py`, and `docs/lab4-feature-equivalence.txt`
shows it agrees with Glue on all 9,999 customers to within 0.0001.

Gap to Level 3: Nothing orchestrates or schedules the data pipeline. The Glue
jobs are started by hand (`aws glue start-job-run`), and
`infrastructure/modules/glue/main.tf` has no trigger or workflow. The
freshness gate detects stale features but can't prevent them: the build just
fails. Data quality is checked only when a model build happens to run, and a
change to a Glue script is never tested before it is deployed.

Top priority investment: An AWS Step Functions state machine on an
EventBridge Scheduler rule (weekly) that runs transform, then a Glue Data
Quality ruleset, then the feature job, and publishes failures to the existing
SNS topic. All of it would be defined in Terraform beside the jobs.

## MLOps Maturity

Current level: 2 (most of the way to 3)

Evidence: A push to `main` runs `pipeline.yaml`'s CodePipeline end to end with
no manual step until approval: `buildspec.yml` tests, trains on managed spot,
evaluates and registers. Promotion is gated statistically:
`models/churn/churn_model.py` raises unless P@10 ≥ 0.50, R@10 ≥ 0.25 and the
lift CI over the recency baseline excludes zero. A monotone constraint on
recency makes the model's direction a property, not a hope. The first green
run (v5) measured AUC 0.7855, lift CI [0.0455, 0.0839] and P@10 0.7167.
`tests/test_model.py` compares each candidate with the Approved champion read
from the registry. `tests/test_fairness.py` flags a 35.1-point tier recall gap
(Bronze vs Platinum), and the final green run's log records
`champion v5 auc=0.7855; candidate auc=0.7855` with the regression test PASSED
(`docs/lab4-build-green.log`). `docs/lab4-failure-demo.txt` shows a failing test halting the
build and the alarm notifying.

Gap to Level 3: Retraining fires only on a code push. There is no scheduled,
new-data or performance trigger, no automated deployment (Lab 5), and no
production performance or drift monitoring (Lab 6), so model decay goes
undetected.

Top priority investment: An Amazon EventBridge rule on `Glue Job State Change`
= `SUCCEEDED` for `northstar-dev-feature-engineer` that starts
`northstar-pipeline`. Every fresh feature set would then retrain, gate and
register a challenger without a human push.
