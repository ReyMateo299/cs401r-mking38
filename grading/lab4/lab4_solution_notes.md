---
tags: [CS401R, lab-solution, lab-4, cicd, codepipeline, codebuild, sagemaker-pipelines, testing, mlops, student-guide]
course: CS 401R
lab: 4
audience: students
status: draft
companion_to: "[[Lab_4--XOps & CICD]]"
verified: 2026-10-19
updated: 2026-10-28 (Matt King, TA) for the handout's evidence structure (commit 45a2677)
---

# Lab 4 — XOps + CI/CD + Testing: Step-by-Step Solution Notes

> **About this copy.** It is the 2026-10-19 walkthrough with the requirements the handout added on
> Oct 23/27 worked into each phase: the Evidence column of every rubric table, *Evidence You Submit*,
> four new files (`lab4-build-green.log`, `lab4-build-failed.log`, `lab4-model-registry.json`,
> `lab4-alarm-email.png`), the `BEFORE` snapshot, the five required headings in
> `docs/lab4-xops-assessment.md`, and the recommended evidence order. Commands and reference numbers
> from the 2026-10-19 run are unchanged. Additions marked **(unverified)** have not been run on AWS yet.
> The handout remains the authority; where they differ, follow the handout.

> **Who this is for.** This is a student walkthrough of [[Lab_4--XOps & CICD]], in the order you should do the work. For each step it gives the code, the reasoning behind each choice, and what you should see when it works. Do not distribute before the Lab 4 deadline (Sat Oct 31).
>
> **Where the numbers come from.** Everything here was run end to end on 2026-10-19 from a repository laid out exactly like yours (`cs401r-<netid>` with kits 1–4 overlaid): Lab 2 rebuilt from Terraform, the Glue pipeline run, the CodePipeline stack deployed from the kit's `pipeline.yaml`, and pipeline runs pushed from GitHub. The first runs exposed defects in the kit and handout (no `requirements.txt`, a missing `iam:PassRole`, a monotonicity test that failed good models, a model left in the registry by a failed build). The kit and handout were corrected the same day and re-run; these notes describe the **corrected** kit. If your kit has no `requirements.txt` or `pytest.ini`, you have the old one: download it again.

**Time budget.** Plan on 9–11 hours. Task 1 (tests) takes about 3, `churn_model.py` about 1, the pipeline and the failure demonstration 2–3, the written Tasks 3–4 about 2, and capturing and reading the evidence about 1. A pipeline run takes about 6 minutes from push to green, so budget for waiting.

**Cost.** About $0.02 per pipeline run: CodeBuild `BUILD_GENERAL1_MEDIUM` for ~5 minutes, plus a training job on `ml.m5.large` **spot** that bills about 60 of its 155 seconds. The real cost is the Lab 2 NAT Gateway at ~$0.045/hour while the stack is up. See Phase 8.

| Phase | What | Rubric | Why it comes here |
|---|---|---|---|
| 0 | Pre-flight: Lab 2 up and fresh, Python env, kit copied in | — | Every build reads Lab 2's data, and the freshness test fails a stale feature set |
| 1 | `data/feature_engineering.py`: Lab 2's feature logic in pandas | T1 (10) | `test_features.py` cannot import anything until it exists |
| 2 | Finish the test suites and write `test_fairness.py` | T1 (30) | The tests are the gate; everything after depends on them |
| 3 | `models/churn/churn_model.py`: your Lab 3 model behind `train()` | T2 | The unmodified template cannot reach Register |
| 4 | One IAM statement: MLEngineer may pass itself to SageMaker | T2 | The SageMaker Pipeline fails in 30 s without it |
| 5 | Deploy the pipeline and get one green run | T2 (10, 6) | |
| 6 | Demonstrate a failing run and the recovery | T2 (8, 6) | The rubric grades the failure, not just the success |
| 7 | MLOps configuration: champion–challenger, triggers, MLflow, lineage | T3 (20) | Needs a registered model and real numbers |
| 8 | Maturity assessment, evidence, teardown, tag | T4 (20) | Written last, from evidence you have |

### Evidence map: what you submit, and the phase that produces it

The TA grades your `lab4-submit` tag **after your AWS stack is gone** and has no access to your account. If
the evidence is not committed, the task was not done. File names are exact. Nothing in the `docs/` rows can
be regenerated once the CI stack and the CodeBuild log group are deleted.

| File | Task | Produced in | What it must show |
|---|---|---|---|
| `tests/test_data.py`, `test_features.py`, `test_model.py`, `test_fairness.py` | 1 | Phases 1–2 | The tests themselves |
| `models/churn/churn_model.py` | 2 | Phase 3 | Your Lab 3 training logic behind `train()` |
| `buildspec.yml`, `pipeline.yaml` | 2 | kit | The five phases |
| `docs/lab4-build-green.log` | 1, 2 | 8.3 (capture block) | Full log of the **final** green build: every test file's `-v` output with ≥2 `PASSED` each (≥5 for `test_features.py`), the `champion vN auc=...` and fairness warnings, SageMaker Pipeline `Succeeded`, package registered |
| `docs/lab4-build-failed.log` | 2 | 6.3 | Full log of the deliberate-failure build: the failing assertion, `PRE_BUILD` failed |
| `docs/lab4-pipeline-runs.txt` | 2 | 8.3 | Every run: commit, status, phases, pytest summary, SageMaker Pipeline executions |
| `docs/lab4-failure-demo.txt` | 2 | Phase 6 (`snap`) | `BEFORE`, `AFTER FAILED RUN` and `AFTER REVERT` snapshots |
| `docs/lab4-alarm-email.png` | 2 | 6.3 | The `ALARM` email as received, with its time |
| `docs/lab4-model-registry.json` | 1, 2 | 8.3 | Every package version and status, including your `Approved` champion |
| `docs/lab4-model-package.json` | 3 | 7.4 | Lineage in `CustomerMetadataProperties` on the final green run's package |
| `docs/lab4-mlflow-runs.txt` | 3 | 7.3 | MLflow App tracking URI; ≥3 runs with params and metrics |
| `docs/lab4-xops-assessment.md` | 2, 3, 4 | 7.1, 7.2, 8.1, 8.2 | `## Pipeline Stage Mapping`, `## Champion-Challenger`, `## Retraining Triggers`, `## DataOps Maturity`, `## MLOps Maturity` |
| Git history on `main` | 2 | 6.2, 6.4 | The deliberate-failure commit and its revert |

Optional extras: `docs/lab4-mlflow-compare.png` (supports, never replaces, the MLflow text file) and
`docs/lab4-feature-equivalence.txt` (Phase 1). The handout doesn't require the equivalence file, but it
answers "how do you know your port matches Glue?"

**Evidence order** (the handout's *Recommended order*). Phases 5–8 follow it:

1. Green run, then **approve it**. That package becomes the champion (5.7).
2. Failure demo: `snap "BEFORE"`, failing push, `snap "AFTER FAILED RUN"`, revert, `snap "AFTER REVERT"`. The revert's green run is your **final green run**, and its regression test runs against the champion from step 1 (Phase 6).
3. Lineage onto the final green run's package, then save `lab4-model-package.json` (7.4).
4. Save `lab4-mlflow-runs.txt` (7.3).
5. Run the capture block while the stack is still up (8.3).
6. Delete the CI stack, *then* commit `docs/`, tag and push (8.4–8.5).
7. Finish the teardown.

---

## Part 1 — Concepts You Need Before You Start

### 1.1 What the pipeline actually is

Four AWS services, each doing one job:

```
git push main
   │
   ▼
CodePipeline  northstar-pipeline ─────────────────────────────────────────────┐
   │ Source: CodeConnections pulls your repo                                  │
   │ Build:  CodeBuild northstar-ci runs buildspec.yml                        │
   │   install    pip install -r requirements.txt                             │
   │   pre_build  pytest test_data.py, test_features.py   ← Test phase        │
   │   build      upsert + start SageMaker Pipeline       ← Build phase       │
   │                 TrainChurnModel  (spot ml.m5.large)                       │
   │                    train_sagemaker.py → churn_model.train()               │
   │                    evaluate_model() raises on a failed gate ← Evaluate   │
   │                 RegisterChurnModel → PendingManualApproval ← Register    │
   │              pytest test_model.py on the real artifact  ← Evaluate again │
   │ ManualApproval: SNS email, a human approves                              │
   └──────────────────────────────────────────────────────────────────────────┘
CloudWatch alarm northstar-ci-build-failure  (AWS/CodeBuild FailedBuilds ≥ 1)
   └─► SNS northstar-model-approvals ─► your inbox
```

**CodePipeline** orchestrates stages and holds the approval. **CodeBuild** is a disposable Linux container that runs `buildspec.yml`. **SageMaker Pipelines** runs the training job and the registration as tracked steps. **The Model Registry** holds every candidate with an approval status. Docs: [CodePipeline concepts](https://docs.aws.amazon.com/codepipeline/latest/userguide/concepts.html), [buildspec reference](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html), [SageMaker Pipelines](https://docs.aws.amazon.com/sagemaker/latest/dg/pipelines.html), [Model Registry](https://docs.aws.amazon.com/sagemaker/latest/dg/model-registry.html).

### 1.2 Phases are not stages

The rubric grades five **phases** (Source, Test, Build, Evaluate, Register). A CodePipeline **stage** is a deployment boundary: artifacts hand off there, and a human can be inserted there. Putting one phase in each stage would mean passing the model between stages and running five CodeBuild projects, which gains nothing. The kit uses three stages. Your job is to say which stage performs which phase (Phase 8 has the table).

### 1.3 Why a CI gate must fail, not skip

`pytest` has three outcomes: pass, fail, skip. A skipped test is green in CI. If a data test skips because the data is missing, `pytest tests/` passes having validated nothing, and the pipeline trains anyway. That is why the kit's `test_data.py` *fails* on missing data unless you set `ALLOW_MISSING_DATA=1`, and why `test_features.py` fails at import if your module is missing. Keep it that way. A gate that cannot fail is decoration.

### 1.4 The promotion gate is statistical

You already met it in Lab 3: precision@10% ≥ 0.50, recall@10% ≥ 0.25, and the 95% paired-bootstrap confidence interval on (model AUC − recency-only baseline AUC) must lie above zero. There is no absolute AUC bar. A fixed 0.72 bar was retired because the reference model fell below it on 58% of random splits. It was grading the split, not the model.

In Lab 4 this gate runs **twice**: inside the training job (your `evaluate_model()` raises, so the training step fails and nothing registers), and again in CodeBuild (`tests/test_model.py` reads the metrics the job wrote).

### 1.5 Managed spot training

On a new AWS account the **on-demand** training quota is 0 for every instance type, so an on-demand training job fails with `ResourceLimitExceeded`. Spot capacity for `ml.m5.large` defaults to 4. `pipeline_definition.py` sets `use_spot_instances=True`, `max_run=1800`, `max_wait=3600`. If AWS reclaims the instance, SageMaker waits and restarts the job. Our job trains in about two minutes, so restarting from scratch costs nothing and needs no checkpoints. A job that trains for hours would need [checkpointing](https://docs.aws.amazon.com/sagemaker/latest/dg/model-checkpoints.html). Measured: 155 s of training, **60 s billable**.

### 1.6 Champion versus candidate

Every run registers a **candidate** as `PendingManualApproval`. The **champion** is the newest `Approved` package. The regression test compares the candidate's AUC with the champion's. It must not compare with the newest package, because by the time CodeBuild runs the test, the newest package *is* the candidate.

### 1.7 Alarms notify on transitions, not on events

A CloudWatch alarm publishes to SNS when its *state changes*: OK → ALARM, or ALARM → OK. If the alarm is already in ALARM from an earlier failure in the same 5-minute window, a second failure produces no new notification. Plan the failure demonstration (Phase 6) around this.

---

## Phase 0 — Pre-flight (30 min)

**0.1 Lab 2 is up, and its feature job ran in the last 48 hours.** The CI pipeline reads `raw/`, `processed/` and `features/` from your data bucket on every run, and `test_features_are_fresh` (Phase 2) fails if the feature set is older than 48 hours. If you tore Lab 2 down, re-apply it and re-run the pipeline. Wait for `terraform apply` to finish before starting the Glue jobs. A job started while the NAT route is still being created fails with `Could not find S3 endpoint or NAT gateway for subnetId`.

```bash
cd infrastructure/environments/dev && terraform apply && cd -
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
aws s3 cp northstar-raw-sample.csv s3://northstar-dev-data-$ACCOUNT/raw/customers/northstar-raw-sample.csv
aws glue start-crawler --name northstar-dev-raw-crawler          # wait for READY
aws glue start-job-run --job-name northstar-dev-transform         # ~145 s
aws glue start-job-run --job-name northstar-dev-feature-engineer  # ~92 s
```

**0.2 Copy the Lab 4 kit in.** `buildspec.yml`, `pipeline.yaml`, `requirements.txt` and `pytest.ini` at the repo root, `tests/` and `models/churn/` as shipped. Add to the repo; don't replace anything. If you unzipped or cloned the template *inside* your repo, delete that folder afterwards, or the `git add` in 8.5 commits a second copy of the kit.

**0.3 `requirements.txt`.** CodeBuild's first phase runs `pip install -r requirements.txt`. The kit's file lists boto3, pandas, pyarrow, numpy, scikit-learn, xgboost, `sagemaker>=2.200.0,<3.0.0` (`pipeline_definition.py` needs the v2 workflow API, which 3.x removed) and pytest. If your own tests import anything else, add it; a missing package fails the build in INSTALL or PRE_BUILD.

**0.4 `pytest.ini`.** `test_features.py` imports `from data.feature_engineering import ...`. Plain `pytest tests/` does not put the repo root on `sys.path`; the kit's `pytest.ini` (`pythonpath = .`) does. Keep it at the repo root. If the import still fails, the error now shows the real exception: usually an error inside your module, not a missing file.

**0.5 Python environment.** CodeBuild runs Python 3.11, so match it:

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt mlflow sagemaker-mlflow
python -c "import sagemaker, xgboost, pandas; print(sagemaker.__version__, xgboost.__version__, pandas.__version__)"
```

You will probably get **pandas 3.x**. Two consequences show up in Phase 3.

**0.6 Keep the data out of git.** The tests read data from paths in `NORTHSTAR_RAW`, `NORTHSTAR_PROCESSED` and `NORTHSTAR_FEATURES`. Download it outside the repo, or add `data/processed/`, `data/features/`, `data/*.csv` and `reports/` to `.gitignore`. The kit's `.gitignore` excludes none of them, and `test_data.py`'s own docstring stages data under `./data/`. Don't ignore all of `data/`: `data/feature_engineering.py` must be committed.

```bash
D=/tmp/lab4data; mkdir -p $D/processed $D/features
B=s3://northstar-dev-data-$ACCOUNT
aws s3 cp $B/raw/customers/northstar-raw-sample.csv $D/
aws s3 cp $B/processed/customers/ $D/processed/ --recursive --exclude "*_glue_temp*"
aws s3 cp $B/features/customers/  $D/features/  --recursive
export NORTHSTAR_RAW=$D/northstar-raw-sample.csv NORTHSTAR_PROCESSED=$D/processed NORTHSTAR_FEATURES=$D/features
```

**0.7 Spot quota.** Any value ≥ 1 works:

```bash
aws service-quotas get-service-quota --service-code sagemaker --quota-code L-29688C85 --query Quota.Value
```

---

## Phase 1 — `data/feature_engineering.py` (1–1.5 hours)

Lab 2's feature logic is PySpark, and PySpark needs a JVM and the Glue runtime, so you can't unit test it in CI. The assignment is to extract the same computations into pandas functions that `test_features.py` can call on a ten-row DataFrame. **The pandas version must agree with Glue, definition for definition.** If it doesn't, you have two definitions of every feature, and the tests prove something about neither.

The functions the tests import, and their signatures:

```python
compute_recency_features(transactions, as_of, customer_ids=None, sentinel=999.0)
compute_frequency_features(transactions, as_of, customer_ids=None)
compute_monetary_features(transactions, as_of, customer_ids=None)
compute_behavioral_features(transactions, as_of=FEATURE_CUTOFF, customer_ids=None)
build_churn_feature_set(customers, transactions, snapshot_date)
```

The core of it, copied from `glue-scripts/feature_engineer.py`:

```python
FEATURE_CUTOFF = pd.Timestamp("2026-04-01")
N_CATEGORIES = 8.0

def _history(transactions, as_of):
    df = transactions.copy()
    df["purchase_date"] = pd.to_datetime(df["purchase_date"], format="mixed").dt.normalize()
    return df[df["purchase_date"] <= pd.Timestamp(as_of).normalize()]   # Glue: purchase_date <= T

def _in_window(df, as_of, days):
    # Glue: purchase_date > date_sub(T, days). Strictly after.
    return df["purchase_date"] > pd.Timestamp(as_of).normalize() - pd.Timedelta(days=days)

def compute_monetary_features(transactions, as_of, customer_ids=None):
    df = _history(transactions, as_of)
    idx = _ids(df, customer_ids)
    g = df.groupby("customer_id")
    w90 = df[_in_window(df, as_of, 90)].groupby("customer_id")
    w180 = df[_in_window(df, as_of, 180)].groupby("customer_id")
    items_180 = w180["num_items"].sum().reindex(idx).fillna(0)
    orders_180 = w180.size().reindex(idx).fillna(0)
    out = pd.DataFrame(index=idx)
    out["avg_order_value"] = g["order_value"].mean().reindex(idx).fillna(0.0)
    out["total_spend_90d"] = w90["order_value"].sum().reindex(idx).fillna(0.0)
    out["total_lifetime_value"] = g["order_value"].sum().reindex(idx).fillna(0.0)
    out["avg_basket_size_6m"] = (items_180 / np.maximum(orders_180, 1.0)).astype(float)
    return out.reset_index()

def compute_behavioral_features(transactions, as_of=FEATURE_CUTOFF, customer_ids=None):
    df = _history(transactions, as_of)
    idx = _ids(df, customer_ids)
    real = df[df["product_category"] != "unknown"]          # 'unknown' is imputed, not a category
    out = pd.DataFrame(index=idx)
    out["category_diversity_score"] = (real.groupby("customer_id")["product_category"]
                                       .nunique() / N_CATEGORIES).reindex(idx).fillna(0.0)
    out["online_to_store_ratio"] = ((df["channel"] == "online").astype(float)
                                    .groupby(df["customer_id"]).mean()).reindex(idx).fillna(0.0)
    return out.reset_index()
```

Recency (`(T − max date).days`, tenure `(T − min date).days`) and frequency (row counts in each window) follow the same pattern. `build_churn_feature_set` merges the four, then adds `loyalty_tier` (LTV thresholds 500 / 2,000 / 5,000) and `churn_risk_score`, copied from the Glue job.

Design decisions and why:

- **Every function filters to purchases on or before T itself.** Passing the whole processed table, holdout included, then cannot leak the label window into a feature. The Phase 2 leakage test relies on this.
- **A customer with no history gets a sentinel, not NaN.** Recency is 999, tenure is 0, and every count and spend is 0. Glue never produces such a row (it groups only customers who bought), but a scoring path can be asked about one, and NaN would reach the model.
- **`avg_basket_size_6m` is items per order.** The Lab 2 schema says "Mean items per order, last 180 days", and the Glue job computes `sum(num_items) / max(count, 1)` over 180 days. Remember this in Phase 2.

**Prove the equivalence.** Run your port on the processed data and compare it with what Glue wrote:

```python
proc = pd.concat(pd.read_parquet(f) for f in glob.glob(f"{D}/processed/*.parquet"))
glue = pd.concat(pd.read_parquet(f) for f in glob.glob(f"{D}/features/*.parquet")).set_index("customer_id")
mine = build_churn_feature_set(None, proc).set_index("customer_id").reindex(glue.index)
for c in FEATURE_COLUMNS:
    print(c, (glue[c] - mine[c]).abs().max())
```

Reference result on all 9,999 customers: every feature, label and tier matches exactly, except a last-digit 0.0001 difference on 192 rows of `avg_order_value` and 2 of `online_to_store_ratio`. That is rounding: Spark's `round()` is HALF_UP and pandas rounds half to even. Save the output as `docs/lab4-feature-equivalence.txt`. It isn't on the handout's required list, but it is your only evidence that the port agrees with Glue.

**Two input shapes for `customer_ids`.** The kit's sentinel test passes a one-column DataFrame (`pd.DataFrame({"customer_id": [...]})`); the leakage test in 2.2 passes a Series (`features_df["customer_id"]`). Make `_ids()` accept both.

---

## Phase 2 — Finish the Test Suites (2–3 hours)

### 2.1 `test_features.py`

**The definitions are Lab 2's, exactly.** `test_avg_basket_size_correct` expects **5.0** for customer 3: four orders of five items each. If your port returns 365, it computes dollars per order, which is `avg_order_value`, and it disagrees with your Glue job.

**Fill the TODOs.** Implement the sentinel test, which is the boundary case of a customer with zero purchases:

```python
features = compute_recency_features(empty_txns, SNAPSHOT_DATE, customer_ids)
assert features.iloc[0]["days_since_last_purchase"] == 999
assert features.iloc[0]["customer_tenure_days"] == 0
```

In `test_no_null_features_for_known_customers`, assert `null_counts.sum() == 0`, and state the null strategy: there is nothing to fill for a customer with history, so any null is a bug.

**Add the cases the rubric names.** The rubric asks for normal, boundary and edge cases. The shipped tests are almost all normal cases. The ones worth adding:

| Test | Case | What it pins down |
|---|---|---|
| `test_single_transaction_customer` | edge | one order 200 days ago: AOV = LTV = 42, spend_90d = 0, basket_6m = 0 (0 / max(0, 1)), tenure = recency = 200 |
| `test_purchase_on_cutoff_day_is_zero_recency` | boundary | a purchase *on* T is in the window and gives recency 0 |
| `test_window_edge_is_exclusive` | boundary | a purchase exactly 90 days before T is outside the 90-day window; one at 89 days is inside |
| `test_purchases_after_cutoff_are_ignored` | leakage | adding a holdout purchase does not move recency |
| `test_unknown_category_not_counted` | edge | `unknown` does not raise diversity |
| `test_customer_with_no_purchases_gets_one_complete_row` | boundary | a rostered customer with no purchases gets one row with no NaN |

Reference: **24 passed** in `test_features.py`.

**What the grader reads.** The TA reads the test names and bodies, and counts `test_features.py ... PASSED` lines (≥5) in `docs/lab4-build-green.log`. The kit's two TODO tests *pass while asserting nothing*, so an unfilled TODO still prints `PASSED`. Fill them in anyway: the named boundary case (zero purchases) is one of them.

### 2.2 `test_data.py`: the two TODOs

**The leakage test.** The obvious version, "every customer's `max(purchase_date)` is ≤ the cutoff", fails on correct data: `processed/` contains the holdout purchases, because the label is built from them, so most customers *do* have purchases after T. What leakage changes is the **features**, so test the features. Recompute the time-sensitive ones from history ≤ T and require them to equal what Glue shipped:

```python
def test_no_feature_uses_post_cutoff_data(self, processed_df, features_df):
    from data.feature_engineering import compute_frequency_features, compute_recency_features
    hist = processed_df[processed_df["purchase_date"] <= FEATURE_CUTOFF]
    ids = features_df["customer_id"]
    rec = compute_recency_features(hist, FEATURE_CUTOFF, ids).set_index("customer_id")
    frq = compute_frequency_features(hist, FEATURE_CUTOFF, ids).set_index("customer_id")
    shipped = features_df.set_index("customer_id")
    for col, ref in [("days_since_last_purchase", rec), ("customer_tenure_days", rec),
                     ("purchase_frequency_30d", frq), ("purchase_frequency_90d", frq),
                     ("purchase_frequency_180d", frq)]:
        bad = int(((shipped[col] - ref[col].reindex(shipped.index)).abs() > 1e-6).sum())
        assert bad == 0, f"{col} differs from the value recomputed from purchases <= T for {bad} customers"
```

If recency had been computed over the full range, it would disagree with the history-only value for every customer who bought after T. Those are exactly the customers the label calls active.

**The freshness test.** `event_time` is the wall-clock time the Lab 2 job ran, in epoch seconds. It is not the cutoff T.

```python
MAX_FEATURE_AGE_HOURS = float(os.environ.get("MAX_FEATURE_AGE_HOURS", "48"))

def test_features_are_fresh(self, features_df):
    latest = pd.to_datetime(float(features_df["event_time"].max()), unit="s", utc=True)
    age_h = (pd.Timestamp.now(tz="UTC") - latest).total_seconds() / 3600
    assert age_h < MAX_FEATURE_AGE_HOURS, (
        f"Feature set is {age_h:.1f} h old; re-run northstar-dev-feature-engineer")
```

**Know what this test costs you.** It is the requirement, and it is correct, but it means a push made more than 48 hours after your last feature-job run fails in `pre_build`. Re-run the feature job (about 90 seconds) before any session in which you will push.

Reference: **28 passed** in `test_data.py`.

### 2.3 `test_model.py`

**Read the monotonicity test before you trust or change it.** It allows ties and dips of up to 0.02 between neighbouring recency values, and requires the score to rise at least 0.20 from 5 to 200 days dormant. Why tolerant: a gradient-boosted model is piecewise constant, so neighbouring recency values in the same leaf interval score identically. An earlier strict version ("4 of 5 pairs strictly increasing") failed a model scoring `0.230, 0.317, 0.307, 0.307, 0.633, 0.765`, an obvious upward trend, trained in the XGBoost 1.7 container, while the same code trained locally on 3.2 passed it.

**The champion regression test (8 pts, and a hardcoded champion AUC earns 3 of them).** Read the champion from the registry:

```python
def champion_from_registry(sm=None, s3=None, group="northstar-churn-models"):
    sm = sm or boto3.client("sagemaker"); s3 = s3 or boto3.client("s3")
    resp = sm.list_model_packages(ModelPackageGroupName=group, ModelApprovalStatus="Approved",
                                  SortBy="CreationTime", SortOrder="Descending", MaxResults=1)
    if not resp["ModelPackageSummaryList"]:
        return None
    arn = resp["ModelPackageSummaryList"][0]["ModelPackageArn"]
    pkg = sm.describe_model_package(ModelPackageName=arn)
    meta = pkg.get("CustomerMetadataProperties") or {}
    if "auc_roc" in meta:
        return arn, float(meta["auc_roc"])
    for section in (pkg.get("ModelMetrics") or {}).values():          # pipeline-registered packages
        for src in section.values():
            if isinstance(src, dict) and src.get("S3Uri", "").endswith("evaluation_metrics.json"):
                b, _, k = src["S3Uri"][5:].partition("/")
                return arn, float(json.loads(s3.get_object(Bucket=b, Key=k)["Body"].read())["auc_roc"])
    raise AssertionError(f"Champion {arn} carries no auc_roc")
```

The kit ships no stub for any of this; you add it to `tests/test_model.py`. The champion's AUC is not in a pipeline-registered package's `CustomerMetadataProperties` (the `RegisterModel` step sets only `ModelMetrics`), which is why the function follows the `evaluation_metrics.json` URI. Your metrics dict must contain `auc_roc` for this to work, on both the candidate and the champion.

Then three tests: the rule `candidate < champion − 0.02` checked offline at the boundary; the lookup checked against a stub that records it asked for `Approved` (so the logic is tested even with no AWS); and the live comparison.

**The live comparison must leave a record.** A passing test prints nothing under `-v`, so the log can't show which champion it used. Warn before asserting. The buildspec runs `test_model.py` with `-rw`, so the line lands in the build log's warnings summary:

```python
# in tests/test_model.py: add `import warnings` and `import boto3` at the top, and put this
# method inside class TestStoredMetricsGate, which owns the eval_metrics fixture
    def test_candidate_not_worse_than_champion(self, eval_metrics):
        champ = champion_from_registry()
        if champ is None:
            pytest.skip("no Approved package yet: the first approved model becomes the champion")
        arn, champ_auc = champ
        version = arn.rsplit("/", 1)[-1]
        new_auc = float(eval_metrics["auc_roc"])
        warnings.warn(f"champion v{version} auc={champ_auc:.4f}; candidate auc={new_auc:.4f}")
        assert new_auc >= champ_auc - 0.02, (
            f"candidate {new_auc:.4f} regresses vs champion v{version} {champ_auc:.4f}")
```

(This sketch is mine, not the gold repo's; the gold version splits the logic into the three tests above.)

**Evidence for this item (8 pts):** the test code; `docs/lab4-build-green.log` showing it `PASSED` (**not** `SKIPPED`) with your `champion vN auc=...` warning; `docs/lab4-model-registry.json` showing version N as `Approved`. A skip is fine on your first green run, but not on your **final** one. That is why you approve a package (5.7) before the failure demo.

Two design points:

- **`Approved` only.** The pipeline registers before CodeBuild runs this test, so the newest package is the candidate itself. Comparing with it always passes.
- **A registry you can't read is a failure, not a skip.** An empty registry is a legitimate skip: the first approved model becomes the champion. A credentials error is not.

The CodeBuild role in `pipeline.yaml` can already list and describe model packages. Verified in run 5: the live comparison ran in CodeBuild against the approved champion and passed.

Reference: **21 tests** in `test_model.py` (20 passed + 1 skipped before any model is approved).

### 2.4 `test_fairness.py` (you write this one)

"Flag (do not block) if the recall gap between highest and lowest loyalty tier exceeds 10 percentage points."

Use a **manual slice evaluation**, not SageMaker Clarify. Clarify is a Processing job, and on a new account only `ml.t3.medium/large/xlarge` have a non-zero processing quota. It would add an instance and minutes to every build to compute four recalls your training job already computed on the held-out split. Have `churn_model.train()` put the per-tier results into the metrics (Phase 3), and have the test read them:

```python
MAX_RECALL_GAP = 0.10

def recall_gap(slices):
    usable = {t: r["recall_top10"] for t, r in slices.items()
              if isinstance(r, dict) and r.get("reliable")}
    if len(usable) < 2:
        return None, None, None
    best, worst = max(usable, key=usable.get), min(usable, key=usable.get)
    return usable[best] - usable[worst], best, worst

def flag_if_unfair(slices, max_gap=MAX_RECALL_GAP):
    gap, best, worst = recall_gap(slices)
    if gap is not None and gap > max_gap:
        warnings.warn(f"FAIRNESS FLAG: recall@top10% gap {gap:.1%} between {best} and {worst}",
                      FairnessWarning)
        return True
    return False
```

- **Flag = a named warning plus a line in the log; the test passes.** Run with `-rw` to see it.
- **Recall at the global top-10% cutoff**, because the retention team calls the top 10% of *all* customers.
- **Reliable tiers only** (≥ 20 positives and ≥ 20 negatives). Platinum has about 21 positives in the 3,000-row validation set. Below 20, its recall is noise.
- **Metrics present without `slice_results` is a failure.** The check was asked for and couldn't be done, and that must not read as "fair".
- Add unit tests of the logic on synthetic data (a large gap warns, a small gap doesn't, an unreliable tier is excluded), so the category has passing tests even before a model exists.

What you will see on this data: the gap is about **32–35 points** (Bronze 0.41–0.44 versus Gold or Platinum 0.10–0.15). That is expected and explainable. High-value tiers churn rarely, so few of them reach the global top 10%. It is a flag for the approver to read, not a defect to fix. The buildspec runs `tests/test_fairness.py` in the build phase, with `-rw`, as soon as the file exists, so the flag appears in the build log next to the model gate.

**Evidence:** `docs/lab4-build-green.log` must show `test_fairness.py` with ≥2 `PASSED` lines (the synthetic-data unit tests count) and the `FAIRNESS FLAG` line in the warnings summary. This applies to every test file: `SKIPPED` does not count as passing.

---

## Phase 3 — `models/churn/churn_model.py` (1 hour)

The training job runs `train_sagemaker.py` (don't edit it), which imports your `churn_model.py` and calls `train(df, seed=42)`. The contract is three names: `FEATURE_COLUMNS`, `LABEL = "churn_label"`, and `train()` returning `(xgboost.Booster, metrics_dict)`.

**Copy, don't import.** Paste in your Lab 3 `preprocess_features`, `train_model`, `train_recency_baseline`, `bootstrap_lift_ci`, `evaluate_model` and `evaluate_slices`. Only `models/churn/` is uploaded to the container.

```python
from __future__ import annotations       # see below

HYPERPARAMETERS = {"max_depth": 6, "eta": 0.1, "num_round": 200, "min_child_weight": 5,
                   "subsample": 0.8, "colsample_bytree": 0.8, "early_stopping_rounds": 20}

def train(df, seed=42):
    hp = dict(HYPERPARAMETERS)
    X, y = preprocess_features(df)
    tiers = df.dropna(subset=[LABEL])["loyalty_tier"].to_numpy(dtype=object)

    X_train, X_val, y_train, y_val, _, tier_val = train_test_split(
        X, y, tiers, test_size=0.30, random_state=seed, stratify=y)

    model = train_model(X_train, y_train, X_val, y_val, hp, seed=seed)
    baseline_proba = train_recency_baseline(X_train, y_train, X_val)
    metrics = evaluate_model(model, X_val, y_val, baseline_proba)   # RAISES on a failed gate

    slices = evaluate_slices(model, X_val, y_val, tier_val)
    metrics["slice_results"] = {k: v for k, v in slices.items() if not k.startswith("_")}
    metrics["slice_worst_tier"] = slices.get("_worst_tier")
    metrics["best_iteration"] = int(model.best_iteration)
    metrics["hyperparameters"] = hp
    metrics["xgboost_version"] = xgb.__version__
    return model, metrics
```

Why each line is the way it is:

- **Keep `evaluate_model()` raising**, as it did in Lab 3. Inside the pipeline that fails `TrainChurnModel`, so `RegisterChurnModel` never runs and a model that can't beat recency never reaches the registry. Run 6 proved it: with shuffled labels the job failed (P@10 0.2367, R@10 0.1076, lift CI [−0.0306, 0.0351]) and the registry gained nothing.
- **Tier goes through the same `train_test_split` call**, so it lines up row for row with `X_val`.
- **`.to_numpy(dtype=object)`, not `.values`.** Under pandas 3 a string column's `.values` is an Arrow array, and `train_test_split` crashes on it with `TypeError: only integer scalar arrays can be converted to a scalar index`.
- **`from __future__ import annotations`.** Your Lab 3 functions have `tuple[np.ndarray, np.ndarray]` annotations; this import means the container's Python never evaluates them.
- **No `mlflow`, `sagemaker` or `boto3` at the top.** The XGBoost 1.7-1 container doesn't ship the first two.

**Test it locally before you push.** A broken contract fails here in seconds; in the pipeline it takes six minutes to tell you the same thing:

```bash
python models/churn/train_sagemaker.py --train-channel $NORTHSTAR_FEATURES \
    --model-dir /tmp/model --output-data-dir /tmp/out
cp /tmp/out/model_metadata.json /tmp/model/
EVAL_METRICS_PATH=/tmp/out/evaluation_metrics.json \
    pytest tests/test_model.py tests/test_fairness.py --model-path /tmp/model/xgboost-model -rw
```

Expected (XGBoost 3.2, local): AUC 0.7796, baseline 0.7233, lift CI [0.0366, 0.0749], P@10 0.7067, R@10 0.3212, then 26 passed and 1 skipped. You will see a `Pandas4Warning` about `Timestamp.utcnow` from `train_sagemaker.py`; it is harmless.

**The container is not your laptop.** The same code in the pipeline (XGBoost **1.7.4**) gave AUC 0.7823, baseline 0.7208, lift CI [0.0415, 0.0812], P@10 0.7167, R@10 0.3258, and early-stopped at iteration 5 instead of 36. Both pass. Don't expect identical numbers across XGBoost versions, and don't write tests that assume them (2.3).

---

## Phase 4 — One IAM Statement (10 min)

This is prerequisite 4 in the handout. Without it, the first run that gets past the tests fails 30 seconds into the SageMaker Pipeline:

```
ClientError: Failed to invoke sagemaker:CreateTrainingJob. Error Details: User:
arn:aws:sts::<acct>:assumed-role/northstar-dev-MLEngineer/sagemaker-pipeline-...-TrainChurnModel
is not authorized to perform: iam:PassRole on resource: arn:aws:iam::<acct>:role/northstar-dev-MLEngineer
```

The SageMaker Pipeline executes *as* MLEngineer, and it creates a training job that is handed the *same* role. Handing a role to a service is `iam:PassRole`. Labs 1–3 never needed it because there you started training as yourself. Add it to `modules/iam/main.tf`, scoped to the role itself and to SageMaker only, and `terraform apply`:

```hcl
{
  Sid       = "PassSelfToSageMaker"
  Effect    = "Allow"
  Action    = ["iam:PassRole"]
  Resource  = aws_iam_role.ml_engineer.arn
  Condition = { StringEquals = { "iam:PassedToService" = "sagemaker.amazonaws.com" } }
},
```

Your MLEngineer policy needs `sagemaker:AddTags` and `ListTags` too: pipelines tag every job they create. Lab 1's policy already has them; check that yours does.

---

## Phase 5 — Deploy the Pipeline (1 hour, mostly waiting)

**5.1 Artifacts bucket.** Use CodePipeline's own versioned bucket, not your data bucket:

```bash
AB=northstar-dev-cicd-artifacts-$ACCOUNT
aws s3api create-bucket --bucket "$AB"      # us-east-1; elsewhere add --create-bucket-configuration
aws s3api put-bucket-versioning --bucket "$AB" --versioning-configuration Status=Enabled
```

**5.2 GitHub connection.** Create it, then authorize it in the console (Developer Tools → Settings → Connections → Update pending connection). It must read `AVAILABLE`. When GitHub asks which repositories the AWS app may see, include `cs401r-<netid>`.

**5.3 Deploy the stack.** `GitHubRepo` is your repository, `cs401r-<netid>`; the template has no default for it, so you can't forget it, but a typo deploys fine and then fails at the Source stage.

**zsh trap (the macOS default shell).** Write `${ACCOUNT}`, not `$ACCOUNT`, when a colon follows the variable. zsh reads `$A:r` as "variable A with the `:r` modifier", so `arn:aws:iam::$A:role/...` silently becomes `arn:aws:iam::<acct>ole/...`. CloudFormation then fails creating the CodeBuild role with the unhelpful `The policy failed legacy parsing`. This cost an hour on 2026-10-19. Using `$(terraform ... output -raw ml_engineer_role_arn)`, as below, avoids it.

```bash
aws cloudformation deploy --template-file pipeline.yaml --stack-name northstar-cicd \
  --parameter-overrides ProjectName=northstar Environment=dev \
    GitHubOwner=<your-github-user> GitHubRepo=cs401r-<netid> GitHubBranch=main \
    ArtifactsBucket="$AB" GitHubConnectionArn=<arn from 5.2> \
    SageMakerRoleArn=$(terraform -chdir=infrastructure/environments/dev output -raw ml_engineer_role_arn) \
  --capabilities CAPABILITY_NAMED_IAM
```

About 70 seconds. **Creating the pipeline starts a run immediately** on whatever is on `main`, so push your Phase 0–4 work first.

**5.4 Subscribe, and confirm.**

```bash
TOPIC=$(aws cloudformation describe-stacks --stack-name northstar-cicd \
  --query "Stacks[0].Outputs[?OutputKey=='ModelApprovalTopicArn'].OutputValue" --output text)
aws sns subscribe --topic-arn $TOPIC --protocol email --notification-endpoint you@byu.edu
```

The subscription stays `pending confirmation` until you click the link in the email. Until then, the alarm still logs *Successfully executed action* (SNS accepted the message) and nothing reaches you. Confirm it now: the failure-demo snapshots must show a subscription **ARN**, not `PendingConfirmation`, and Task 2's notification item (6 pts) scores 0 without a confirmed subscriber.

```bash
aws sns list-subscriptions-by-topic --topic-arn "$TOPIC" --query 'Subscriptions[].[Protocol,SubscriptionArn]' --output text
```

**5.5 Watch a run.** Every push to `main` triggers one, including a commit that only changes `docs/`.

```bash
aws codepipeline get-pipeline-state --name northstar-pipeline \
  --query 'stageStates[].[stageName,latestExecution.status]' --output text
aws logs tail /aws/codebuild/northstar-ci --follow
```

Reference timings: install 36–72 s, pre_build 5–6 s (28 + 24 tests), SageMaker Pipeline about 210 s, model gate 21 tests in 1.4 s, about 6 minutes in total. `get-pipeline-state` shows the *latest* execution of each stage separately. After a failed Build, ManualApproval can still read `Succeeded` from an earlier run, so don't read it as the current run's status.

**5.6 When TrainChurnModel fails, CodeBuild won't tell you why.** It prints only `AlgorithmError: ExecuteUserScriptError`. The reason is in the training job's log:

```bash
J=$(aws sagemaker list-training-jobs --sort-by CreationTime --sort-order Descending \
      --max-results 1 --query 'TrainingJobSummaries[0].TrainingJobName' --output text)
aws logs filter-log-events --log-group-name /aws/sagemaker/TrainingJobs \
    --log-stream-name-prefix $J --filter-pattern "?Error ?FAIL" --query 'events[].message' --output text
```

**5.7 The green run, and the approval.** A green run ends with ManualApproval `InProgress` and a new `PendingManualApproval` package. You are the approver. Read the metrics on the package, then:

```bash
G=arn:aws:sagemaker:us-east-1:${ACCOUNT}:model-package/northstar-churn-models
aws sagemaker update-model-package --model-package-arn $G/<N> --model-approval-status Approved \
  --approval-description "AUC 0.7823, lift CI [0.0415, 0.0812], P@10 0.7167, R@10 0.3258; fairness flag reviewed"
T=$(aws codepipeline get-pipeline-state --name northstar-pipeline \
  --query "stageStates[?stageName=='ManualApproval'].actionStates[0].latestExecution.token" --output text)
aws codepipeline put-approval-result --pipeline-name northstar-pipeline --stage-name ManualApproval \
  --action-name ReviewModelMetrics --token $T --result "summary=Approved,status=Approved"
```

Approving the CodePipeline action does not change the package's status; those are two separate records. Approving the package is what makes it the champion for the next run's regression test.

**This is step 1 of the evidence order.** Approve *before* the failure demo, so that the revert's green run, your final green run, has a champion to compare against and its regression test `PASSED` rather than skipped. Keep this package `Approved` until after the capture block (8.3): `docs/lab4-model-registry.json` must show it `Approved`. Note its version number N; it is the `vN` in your champion warning.

**Check that the green run trained *your* model.** The TA runs `git show <commit>:models/churn/churn_model.py` on the green build's `resolvedSourceVersion` and checks that `train()` is yours, not the template. A run whose Build phase stopped on `NotImplementedError` can't score Task 2's first item.

**Why a failed build never leaves an approvable package.** The SageMaker Pipeline registers *before* CodeBuild runs `tests/test_model.py`. A model that fails a gate inside training never registers, because `evaluate_model()` raises and the training step fails. A model that fails a CodeBuild-only test is already registered, so the buildspec's `post_build` sets it to `Rejected`, with the build ID in the approval description. You'll see `Rejected arn:...` in the build log when that happens.

---

## Phase 6 — Demonstrate Failure and Recovery (45 min)

The rubric grades this (8 + 6 + 6 points), and the TA can't run it for you because they have no access to your account. Your evidence files *are* the demonstration. A claim that the registry "gained no version" needs a *before* to compare against, so you take three labelled snapshots into `docs/lab4-failure-demo.txt`.

**What each rubric item reads**

| Item | Pts | Evidence |
|---|---|---|
| Pipeline halts on test failure | 8 | `AFTER FAILED RUN`: build `FAILED`, `PRE_BUILD FAILED`, **no `BUILD` phase**. `docs/lab4-build-failed.log` shows the failing assertion. The failure commit is in `main` and its SHA matches the build |
| Registry promotion only on green | 6 | Newest package version **identical** in `BEFORE` and `AFTER FAILED RUN`; `AFTER REVERT` shows one more, `PendingManualApproval`. Cross-checked against `docs/lab4-model-registry.json` |
| Notification delivers | 6 | `OK` in `BEFORE`, `ALARM` in `AFTER FAILED RUN`, *Successfully executed action* in the history, a subscription ARN (not `PendingConfirmation`), plus `docs/lab4-alarm-email.png` |

**6.1 Preconditions.**

- A champion is `Approved` (5.7).
- The email subscription is confirmed (5.4).
- The feature job ran within 48 hours, or the *revert* fails `pre_build` too (`aws glue start-job-run --job-name northstar-dev-feature-engineer`, ~90 s).
- `northstar-ci-build-failure` reads `OK`. An alarm already in `ALARM` sends nothing new, because it notifies on state *changes*.

**6.2 Define the two helpers** once, in bash or zsh, from the repo root, while the CI stack is up. Both come from the handout: `snap` appends a labelled snapshot, and `save_log` writes a CodeBuild build's complete log to a file.

```bash
TOPIC=$(aws cloudformation describe-stacks --stack-name northstar-cicd \
  --query "Stacks[0].Outputs[?OutputKey=='ModelApprovalTopicArn'].OutputValue" --output text)

snap () {   # usage: snap "LABEL"  -> appends a labelled snapshot to docs/lab4-failure-demo.txt
  {
    echo; echo "===== $1  ($(date -u +%Y-%m-%dT%H:%M:%SZ)) ====="
    echo "--- newest CodeBuild build: id, commit, status, then phases"
    B=$(aws codebuild list-builds-for-project --project-name northstar-ci --query 'ids[0]' --output text)
    aws codebuild batch-get-builds --ids "$B" --query 'builds[0].[id,resolvedSourceVersion,buildStatus]' --output text
    aws codebuild batch-get-builds --ids "$B" --query 'builds[0].phases[].[phaseType,phaseStatus]' --output text
    echo "--- newest 3 model packages"
    aws sagemaker list-model-packages --model-package-group-name northstar-churn-models \
      --sort-by CreationTime --sort-order Descending --max-results 3 \
      --query 'ModelPackageSummaryList[].[ModelPackageVersion,ModelApprovalStatus,CreationTime]' --output text
    echo "--- alarm state"
    aws cloudwatch describe-alarms --alarm-names northstar-ci-build-failure \
      --query 'MetricAlarms[0].[StateValue,StateUpdatedTimestamp]' --output text
    echo "--- alarm action history"
    aws cloudwatch describe-alarm-history --alarm-name northstar-ci-build-failure \
      --history-item-type Action --max-records 5 --query 'AlarmHistoryItems[].[Timestamp,HistorySummary]' --output text
    echo "--- SNS subscriptions (an ARN, not PendingConfirmation)"
    aws sns list-subscriptions-by-topic --topic-arn "$TOPIC" --query 'Subscriptions[].[Protocol,SubscriptionArn]' --output text
  } 2>&1 | tee -a docs/lab4-failure-demo.txt
}

save_log () {   # usage: save_log <codebuild-build-id> <output-file>
  read -r G S <<< "$(aws codebuild batch-get-builds --ids "$1" \
      --query 'builds[0].logs.[groupName,streamName]' --output text)"
  aws logs filter-log-events --log-group-name "$G" --log-stream-names "$S" --output json \
    | python3 -c 'import json,sys; sys.stdout.write("".join(e["message"] if e["message"].endswith("\n") else e["message"]+"\n" for e in json.load(sys.stdin)["events"]))' \
    > "$2"
}
```

**6.3 BEFORE, break a test, AFTER FAILED RUN.**

```bash
snap "BEFORE"            # alarm OK; note the newest package version
sed -i '' 's/assert n == 0, f"{n} rows with null customer_id/assert n == 999, f"{n} rows with null customer_id/' tests/test_data.py
git commit -am "TEMPORARY: deliberate test failure (Task 2 demo)" && git push
```

The failing test is in `test_data.py` on purpose: it fails in `pre_build`, which is exactly the evidence the rubric names (`PRE_BUILD FAILED`, no `BUILD` phase). A failure placed in `test_model.py` would fail in `build`, *after* registration, and add an auto-`Rejected` version that breaks "newest version identical in BEFORE and AFTER FAILED RUN".

Wait for the build to fail **and** for the alarm to reach `ALARM` (about 2 minutes after the build ends). Then, without waiting further:

```bash
snap "AFTER FAILED RUN"
FAILED=$(aws codebuild list-builds-for-project --project-name northstar-ci --query 'ids[0]' --output text)
save_log "$FAILED" docs/lab4-build-failed.log
grep -nE 'FAILED|[0-9]+ failed' docs/lab4-build-failed.log | head    # the assertion and "1 failed, 27 passed"
```

Screenshot the email whose subject starts `ALARM: "northstar-ci-build-failure"`, with its received time visible (you may blur your address), and save it as `docs/lab4-alarm-email.png`. The alarm also emails `OK:` when it recovers; that one is not the evidence.

Reference (run 4): `1 failed, 27 passed`, PRE_BUILD FAILED, POST_BUILD absent, newest package unchanged, ALARM about 2 minutes after the build failed (22:40:04 → 22:41:57 UTC), *Successfully executed action*. The lag is the alarm's 5-minute evaluation period on `FailedBuilds`.

> **Take `AFTER FAILED RUN` promptly (unverified timing).** The alarm has a 300 s period with `TreatMissingData: notBreaching`, so it may return to `OK` on its own before your revert goes green. The reference run saw `OK` about 2 minutes after the green build, so this may not happen. Either way, a late snapshot reads `OK`, and the rubric needs `ALARM` in that snapshot.

**6.4 Revert, then AFTER REVERT.** Keep both commits in `main`; the TA matches the failing commit's SHA to the build in `AFTER FAILED RUN`.

```bash
git revert --no-edit HEAD && git push
# wait for the green build AND for the alarm to read OK, then:
snap "AFTER REVERT"      # one more package, PendingManualApproval; alarm OK
```

Reference: alarm back to `OK` about 2 minutes after the green build finished, again with *Successfully executed action*. This revert run is your **final green run**. Note its build ID and package version: 7.4 and 8.3 use both. If you push anything else to `main` before the capture block, that later run becomes the newest one instead, so do Phase 7's AWS steps from your own shell, not by pushing.

Notice where the failure stopped: `pre_build`, with no `POST_BUILD` phase at all. That is why the alarm watches CodeBuild's own `FailedBuilds` metric. A metric published from `post_build` would have been silent for exactly this failure.

**Check the file before moving on:** `grep -n '^=====' docs/lab4-failure-demo.txt` shows all three labels, and `BEFORE` and `AFTER FAILED RUN` list the same newest version.

---

## Phase 7 — MLOps Configuration (Task 3, 1.5 hours)

The written parts go in `docs/lab4-xops-assessment.md` under **exact headings**, so the TA can find them: `## Champion-Challenger` (7.1) and `## Retraining Triggers` (7.2). The other two parts are evidence files: `docs/lab4-mlflow-runs.txt` (7.3) and `docs/lab4-model-package.json` (7.4). Do 7.3 and 7.4 from your own shell: a push to `main` would start another pipeline run after your final green run.

**7.1 Champion–challenger criterion (5 pts): a number and a yes/no.** Reference:

> A challenger replaces the champion iff (1) it passes the promotion gates (P@10 ≥ 0.50, R@10 ≥ 0.25, lift CI lower bound > 0), **and** (2) AUC_challenger ≥ AUC_champion − 0.02, **and** (3) no reliable tier loses more than 0.05 AUC against the champion's same tier.

Defend the number. The reference model's AUC has a standard deviation of 0.029 across random splits. A "+0.005 better" rule would be decided by the split. Weekly retraining on fresh data has to be able to replace a champion measured on older data, and the −0.02 tolerance permits that while refusing a material regression. Criteria 1 and 2 are automated in CI; say who checks 3.

**7.2 Retraining triggers (8 pts): each needs a threshold and a named AWS service that fires it.**

- *Scheduled:* a Glue trigger runs the feature job weekly (`cron(0 6 ? * MON *)`). An **EventBridge rule** on `Glue Job State Change` = `SUCCEEDED` for that job starts **CodePipeline** `northstar-pipeline`. Chain it to the job, not to the clock: a bare weekly cron trips the 48-hour freshness test whenever the job runs late.
- *Performance-based:* churn labels arrive 90 days late, so production AUC lags. Pair a lagging trigger with a leading one. Lagging: a monthly Lambda (EventBridge Scheduler) scores customers whose outcome window has closed and publishes `ProductionAUC`; a **CloudWatch alarm** fires below **0.72**, the recency baseline's AUC. Leading: Lab 6's drift job publishes PSI for `days_since_last_purchase`; alarm at **PSI > 0.2**. An EventBridge rule on `CloudWatch Alarm State Change` starts the pipeline.

**7.3 Experiment tracking (4 pts): MLflow App runs that vary something.** Use your Lab 3 MLflow App (re-create it if you deleted it; it is free). Train the pipeline's own `churn_model.train()` under at least three hyperparameter settings and log each:

```python
mlflow.set_tracking_uri(MLFLOW_APP_ARN); mlflow.set_experiment("northstar-churn-lab4")
for name, override in {"d3-eta0.1": {"max_depth": 3}, "d6-eta0.03": {"eta": 0.03, "num_round": 600},
                       "d8-eta0.3": {"max_depth": 8, "eta": 0.3}}.items():
    churn_model.HYPERPARAMETERS = {**base, **override}
    _, metrics = churn_model.train(df, seed=42)
    with mlflow.start_run(run_name=name):
        mlflow.log_params(churn_model.HYPERPARAMETERS)
        mlflow.log_metrics({k: v for k, v in metrics.items() if isinstance(v, (int, float))})

# Evidence: write the WHOLE table. Printing the DataFrame truncates params.* to "...",
# which hides exactly what is being graded.
runs = mlflow.search_runs(experiment_names=["northstar-churn-lab4"])
cols = ["run_id", "tags.mlflow.runName", "start_time"] + \
       [c for c in runs.columns if c.startswith(("params.", "metrics."))]
with open("docs/lab4-mlflow-runs.txt", "w") as f:
    f.write(f"tracking_uri: {mlflow.get_tracking_uri()}\n\n{runs[cols].to_string()}\n")
```

Reference results (local, XGBoost 3.2):

| run | AUC | lift CI | P@10 | R@10 | best iter |
|---|---|---|---|---|---|
| d6-eta0.1 | 0.7796 | [0.0366, 0.0749] | 0.7067 | 0.3212 | 36 |
| d3-eta0.1 | 0.7812 | [0.0389, 0.0761] | 0.7400 | 0.3364 | 49 |
| d6-eta0.03 | 0.7827 | [0.0398, 0.0776] | 0.7267 | 0.3303 | 84 |
| d8-eta0.3 | 0.7496 | [0.0048, 0.0466] | 0.6867 | 0.3121 | 7 |

Interpret them. The three sensible settings sit within 0.003 AUC of each other, which is inside split noise. The deep, fast model peaks at iteration 7 and barely clears the lift gate. The SageMaker Experiment `northstar-churn-pipeline`, which your pipeline creates automatically, doesn't count. It records that a pipeline ran, not what you varied.

**Check `docs/lab4-mlflow-runs.txt` before moving on.** Its first line must be an MLflow App ARN (`tracking_uri: arn:aws:sagemaker:...:mlflow-app/...`). A local `mlruns` path or a Tracking Server does not count. It also needs ≥3 rows whose `params.*` values differ and whose `metrics.*` are filled in. `docs/lab4-mlflow-compare.png` (a screenshot of the comparison view) is optional and never replaces the text file.

**7.4 Lineage (3 pts): `describe-model-package` must show the training data URI, its timestamp, the commit SHA and the evaluation metrics.** Write them onto the **final green run's** package (the version `snap "AFTER REVERT"` showed). The pipeline's `RegisterModel` step records neither on the package. Both live one hop away, on the training job: its input channel, and its `COMMIT_SHA` environment variable. Follow the hop and write the answers onto the package as `CustomerMetadataProperties` (the one field `UpdateModelPackage` allows after registration):

```python
pkg = sm.describe_model_package(ModelPackageName=arn)
url = pkg["InferenceSpecification"]["Containers"][0]["ModelDataUrl"]   # .../training/<job>/output/model.tar.gz
parts = url.split("/"); job = sm.describe_training_job(TrainingJobName=parts[parts.index("output") - 1])
meta = {"commit_sha": job["Environment"]["COMMIT_SHA"],
        "training_data_s3_uri": job["InputDataConfig"][0]["DataSource"]["S3DataSource"]["S3Uri"],
        "training_started": job["TrainingStartTime"].isoformat(),
        "training_data_last_modified": ...,   # newest LastModified under that URI
        "training_data_sha256": ...,          # hash of the sorted (key, ETag) list: the data "version"
        **{k: str(v) for k, v in metrics.items() if k in ("auc_roc", "lift_ci_low", "lift_ci_high",
                                                         "precision_top10", "recall_top10")}}
sm.update_model_package(ModelPackageArn=arn, CustomerMetadataProperties={**existing, **meta})
```

Run it with your own credentials after the final green run, or add it to the buildspec after the model gate (the CodeBuild role may call `UpdateModelPackage`; then every run is covered, but you must push that change *before* the failure demo). Then save the description. It needs the full **ARN**: the short form `northstar-churn-models/N` is rejected with a `ValidationException`.

```bash
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
N=<the version your final green run registered>
aws sagemaker describe-model-package \
  --model-package-name "arn:aws:sagemaker:us-east-1:${ACCOUNT}:model-package/northstar-churn-models/${N}" \
  > docs/lab4-model-package.json
python3 -c "import json; print(json.dumps(json.load(open('docs/lab4-model-package.json'))['CustomerMetadataProperties'], indent=2))"
```

The printout must show the data URI, its timestamp, the commit SHA and the metrics. `COMMIT_SHA` on the training job is the first 8 characters, which is fine as long as `git rev-parse <sha8>` resolves on `main`.

---

## Phase 8 — Maturity Assessment, Evidence, Teardown, Tag (1.5 hours)

**8.1 Task 4.** Use the template in the handout, under the exact headings `## DataOps Maturity` and `## MLOps Maturity`, each with the lines `Current level:`, `Evidence:`, `Gap to Level [N+1]:` and `Top priority investment:`. The gap and investment lines are graded on their own (6 and 4 pts). Cite files and measured results, not intentions. **Every path you cite must exist at your `lab4-submit` tag; the TA opens them.** Citing a measured line from your own evidence (e.g. the `champion vN auc=...` warning in `docs/lab4-build-green.log`) is stronger than citing a config file. Check your citations before tagging:

```bash
grep -oE '`[^` ]+\.(py|ya?ml|tf|md|txt|json|log|sh|png)(::[^` ]*)?`' docs/lab4-xops-assessment.md \
  | tr -d '`' | sed 's/::.*//' | sort -u | while read -r p; do [ -e "$p" ] || echo "MISSING $p"; done
```
 Reference levels: DataOps **2** (pipeline as code, two data-quality gates, a leakage test, a proven pandas/Glue equivalence; gap: nothing runs or tests the data pipeline on a schedule). MLOps **2** (push-to-registry with no manual step, a statistical gate, a live champion check, human promotion, failure notification; gap: the retraining triggers are designed but not deployed, and nothing measures production performance until Lab 6). "Missing automated drift detection (Lab 6)" earns full gap credit; "need more automation" earns 1.

**8.2 The stage mapping (part of the 10 points).** Put it under `## Pipeline Stage Mapping` in `docs/lab4-xops-assessment.md`: map the five phases to stages, and give your rationale.

| Phase | CodePipeline stage | Where exactly |
|---|---|---|
| Source | `Source` | CodeConnections, `main`, DetectChanges |
| Test | `Build` | `buildspec.yml` `pre_build`: test_data, test_features |
| Build | `Build` | `build`: upsert + start the SageMaker Pipeline; `TrainChurnModel` on spot |
| Evaluate | `Build` | `evaluate_model()` inside training (blocks registration), then `tests/test_model.py` in CodeBuild |
| Register | `Build` → `ManualApproval` | `RegisterChurnModel` (`PendingManualApproval`), then a human approves |

Say why you chose CodePipeline. The reference reason: no AWS keys in GitHub, a native approval action, and everything runs in the same account under IAM roles.

**8.3 Capture everything else: the stack must still be up.** The TA grades your tagged commit after your stack is gone. Deleting the stack erases CodePipeline's run history, and deleting the log group erases every build log. Run this from the repo root, in the same shell where `save_log` (6.2) is defined:

```bash
# 1. Every run: CodePipeline, CodeBuild (with phases and pytest summary lines), SageMaker Pipeline
{
  echo "===== CodePipeline executions: start, status, commit, execution id ====="
  aws codepipeline list-pipeline-executions --pipeline-name northstar-pipeline \
    --query 'pipelineExecutionSummaries[].[startTime,status,sourceRevisions[0].revisionId,pipelineExecutionId]' --output text
  echo; echo "===== CodeBuild builds, newest first: start, status, commit, build id ====="
  for B in $(aws codebuild list-builds-for-project --project-name northstar-ci --query 'ids[]' --output text); do
    aws codebuild batch-get-builds --ids "$B" --query 'builds[0].[startTime,buildStatus,resolvedSourceVersion,id]' --output text
    aws codebuild batch-get-builds --ids "$B" --query 'builds[0].phases[].[phaseType,phaseStatus]' --output text | sed 's/^/    /'
    save_log "$B" /tmp/lab4-build.log && grep -E '^=+ .*(passed|failed|error)' /tmp/lab4-build.log | sed 's/^/    pytest: /'
  done
  echo; echo "===== SageMaker Pipeline executions: start, status, name ====="
  aws sagemaker list-pipeline-executions --pipeline-name northstar-churn-pipeline \
    --query 'PipelineExecutionSummaries[].[StartTime,PipelineExecutionStatus,PipelineExecutionDisplayName]' --output text
} 2>&1 | tee docs/lab4-pipeline-runs.txt

# 2. The full log of your final green build (the newest SUCCEEDED build above: the revert's run)
save_log <final-green-build-id> docs/lab4-build-green.log

# 3. Every version in the registry, with approval status and metadata (champion still Approved)
aws sagemaker list-model-packages --model-package-group-name northstar-churn-models \
  --sort-by CreationTime --sort-order Descending --output json > docs/lab4-model-registry.json
```

**Read every file before you tear down.** None of them can be regenerated afterwards. A quick self-check against what the rubric reads:

```bash
G=docs/lab4-build-green.log
for t in test_data test_features test_model test_fairness; do        # need >=2 PASSED each (>=5 features), SKIPPED doesn't count
  printf '%-14s PASSED=%s SKIPPED=%s\n' $t "$(grep -cE "tests/$t\.py::.* PASSED" $G)" "$(grep -cE "tests/$t\.py::.* SKIPPED" $G)"
done
grep -nE 'champion v[0-9]+ auc=|FAIRNESS FLAG|Pipeline succeeded|Registered: arn:' $G
grep -n 'SUCCEEDED' docs/lab4-pipeline-runs.txt | head -3              # a green build; its phases run through POST_BUILD
python3 -c "import json; [print(p['ModelPackageVersion'], p['ModelApprovalStatus']) for p in json.load(open('docs/lab4-model-registry.json'))['ModelPackageSummaryList']]"
ls -la docs/lab4-*                                                     # the 9 required docs files from the evidence map, non-empty
```

An empty `lab4-build-green.log` usually means the wrong build ID. A `pytest:` line reading `1 failed` on what you thought was your green build means it wasn't. The registry listing must show your champion `Approved`, the failed run adding nothing, and the final run `PendingManualApproval`.

**8.4 Delete the CI stack, *then* commit, tag and push.** Deleting first means the docs push doesn't start one more training run.

```bash
aws cloudformation delete-stack --stack-name northstar-cicd          # pipeline, CodeBuild, roles, topic, alarm
aws cloudformation wait stack-delete-complete --stack-name northstar-cicd
bash scripts/check-secrets.sh
git add docs/ tests/ models/ data/feature_engineering.py buildspec.yml pipeline.yaml requirements.txt pytest.ini .gitignore
git status --short                                                    # nothing you didn't mean to add (no data/*.parquet, no template copy)
git commit -m "Lab 4: tests, churn_model, CI/CD, MLOps config, assessment, evidence"
git push origin main
git tag lab4-submit && git push origin lab4-submit
```

The TA grades `git checkout lab4-submit`. If you forget the tag, you are graded at your last commit before the deadline. The deliberate-failure commit and its revert are already in `main`; leave them there.

**8.5 Finish the teardown, in this order.** Your champion's `Approved` status is already captured in `docs/lab4-model-registry.json`, so you can now reject it before the bucket that holds its artifact goes.

```bash
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AB=northstar-dev-cicd-artifacts-$ACCOUNT                                 # your old shell variable is probably gone
aws sagemaker update-model-package --model-package-arn \
  "arn:aws:sagemaker:us-east-1:${ACCOUNT}:model-package/northstar-churn-models/<champion N>" \
  --model-approval-status Rejected
aws s3 rm s3://$AB --recursive && aws s3api delete-bucket --bucket $AB   # versioned: delete versions too (console "Empty")
aws logs delete-log-group --log-group-name /aws/codebuild/northstar-ci   # CodeBuild made it, not the stack
aws codebuild list-report-groups                                         # delete northstar-ci-northstar-test-reports
bash scripts/teardown-lab2.sh                                            # if you are done with Lab 2's infrastructure
```

`teardown-lab2.sh` rewrites `docs/lab2-destroy-output.txt`; if you want to keep your Lab 2 copy, `git checkout` it afterwards (and don't commit the change after tagging). **Going straight on to Lab 5?** Lab 5 deploys a model package whose artifact lives in the data bucket, so running `teardown-lab2.sh` means re-running Lab 2 and one pipeline run first. Either way, don't leave the NAT Gateway up between sessions.

---

## Troubleshooting Quick Reference

Every row happened on 2026-10-19 except the last two of the original table and the rows from "`pre_build` fails on the revert too" down, which were added with the 2026-10-28 evidence update (derived from the handout, not yet observed). Rows marked *old kit* cannot happen with the corrected kit; they are here for anyone who downloaded it before the fix.

| Symptom | Cause | Fix |
|---|---|---|
| INSTALL: `Could not open requirements file` | *Old kit:* no `requirements.txt` | Download the current kit (0.3) |
| `data/feature_engineering.py not found` under plain `pytest`, but the file exists | *Old kit:* no `pytest.ini` | Download the current kit (0.4) |
| `test_avg_basket_size_correct` expects ~365 | *Old kit* used dollars per order | Current kit expects 5.0 items per order (2.1) |
| Your leakage test fails on good data | Asserted `max(purchase_date) <= T`; `processed/` contains the holdout | Recompute features from history ≤ T (2.2) |
| `test_features_are_fresh` fails | Feature job last ran > 48 h ago | Re-run `northstar-dev-feature-engineer` |
| Glue: `Could not find S3 endpoint or NAT gateway for subnetId` | Job started before `terraform apply` finished | Wait for `Apply complete!`, re-run |
| `TypeError: only integer scalar arrays...` in `train_test_split` | pandas 3 Arrow string `.values` | `.to_numpy(dtype=object)` (Phase 3) |
| `ValueError: assignment destination is read-only` | pandas 3 copy-on-write: `.values` is a read-only view | `np.array(..., copy=True)` before writing |
| `not authorized to perform: iam:PassRole on ... MLEngineer` | Pipeline passes MLEngineer to its own training job | Phase 4 |
| `AlgorithmError: ExecuteUserScriptError` and nothing else | Your code raised inside the container | Training job log (5.6) |
| `test_model_monotone_on_recency`: "Only 3/5 pairs are increasing" | *Old kit* counted ties as failures | Current kit tolerates ties (2.3) |
| Build red, and a new package shows `Rejected` | Expected: post_build rejects a package from a failed build | Nothing to do (5.7) |
| `The policy failed legacy parsing` creating `CodeBuildRole` | zsh ate part of the `SageMakerRoleArn` (`$A:role`) | `${A}` or the terraform output form (5.3) |
| ManualApproval reads `Succeeded` after a failed build | `get-pipeline-state` shows each stage's latest execution | Check the execution ID |
| Alarm in ALARM but no new notification | Already in ALARM: no transition | 6.1 |
| *Successfully executed action* but no email | Email subscription not confirmed | Click the link (5.4) |
| Alarm `ALARM`, history says `Failed to execute action` | Topic policy lacks `cloudwatch.amazonaws.com` | Keep the kit's `AllowCloudWatchAlarmNotifications` statement |
| Source stage fails | `GitHubRepo` wrong, or the GitHub app can't see the repo | 5.2, 5.3 |
| `pre_build` fails on the revert too | Feature job > 48 h old by the time you reverted | Re-run `northstar-dev-feature-engineer` before the demo (6.1) |
| `AFTER FAILED RUN` shows `OK`, not `ALARM` | Snapshot taken too late, or before the alarm reached `ALARM` | Take it as soon as the alarm reads `ALARM` (6.3) |
| `AFTER FAILED RUN` shows a new `Rejected` version | The deliberate failure was in `test_model.py` (fails in `build`, after registration) | Put it in `test_data.py` so it fails in `pre_build` (6.3) |
| Subscriptions show `PendingConfirmation` | Confirmation link never clicked | 5.4; notification item scores 0 otherwise |
| Regression test `SKIPPED` in the final green log | No package was `Approved` before the final green run | Approve the first green run's package (5.7), then redo the demo |
| `describe-model-package` → `ValidationException` | Short name `northstar-churn-models/N` | Pass the full ARN (7.4) |
| `lab4-mlflow-runs.txt` shows `params...` as `...` | Printed the DataFrame | Use the `to_string()` writer (7.3) |
| `lab4-build-green.log` is empty | Wrong build ID passed to `save_log` | Use the newest `SUCCEEDED` id from `lab4-pipeline-runs.txt` (8.3) |
| `lab4-model-registry.json` shows no `Approved` package | Champion rejected before the capture block | Capture first, reject after (8.5) |

---

## Further Reading

- AWS: [CodePipeline manual approval](https://docs.aws.amazon.com/codepipeline/latest/userguide/approvals.html), [CodeBuild build phase transitions](https://docs.aws.amazon.com/codebuild/latest/userguide/view-build-details.html#view-build-details-phases), [CodeBuild CloudWatch metrics](https://docs.aws.amazon.com/codebuild/latest/userguide/monitoring-metrics.html), [SageMaker managed spot training](https://docs.aws.amazon.com/sagemaker/latest/dg/model-managed-spot-training.html), [Pipelines ConditionStep](https://docs.aws.amazon.com/sagemaker/latest/dg/build-and-manage-steps.html#step-type-condition), [UpdateModelPackage](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_UpdateModelPackage.html), [CloudWatch alarm actions](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- Testing ML systems: Breck et al., *The ML Test Score: A Rubric for ML Production Readiness and Technical Debt Reduction* (2017); Ribeiro et al., *Beyond Accuracy: Behavioral Testing of NLP Models with CheckList* (2020), the idea behind the monotonicity test
- Continuous delivery for ML: Sato, Wider & Windheuser, [*Continuous Delivery for Machine Learning*](https://martinfowler.com/articles/cd4ml.html) (2019)
- Sculley et al., *Hidden Technical Debt in Machine Learning Systems* (NeurIPS 2015)
