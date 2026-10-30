# Lab 4 instruction suggestions

Reviewed 2026-10-28 against:

- `CS_401R_Labs/Lab_4--XOps & CICD.md` (handout, including the Oct 23 evidence clarification)
- `CS_401R_Labs/Lab_4--Solution Notes.md` (student walkthrough, verified 2026-10-19)
- `Sample Solutions/Lab Solution Notes/Lab 4 - XOps & CICD (Solution).md` (TA grading guide)
- `Starter Kits/Lab 4/` (byte-identical to the `cs401r-lab4-template` GitHub repo apart from its README and `.gitignore`)
- `Lab_5--Deployment & Security.md` (for cross-lab consistency only)

"Verified" means I confirmed it by reading the named file(s). Nothing here has
been run on AWS yet; items that depend on runtime behavior are marked
**Inferred** until my own pipeline run confirms or refutes them.

Findings are ordered by how likely they are to block or cost students points.

## 1. The handout never says students must write `data/feature_engineering.py`

**Finding (verified, handout + kit + solution notes):** `tests/test_features.py`
imports five functions from `data.feature_engineering` and calls
`pytest.fail()` at import time if the module is missing. The solution notes make
the module Phase 1 (1–1.5 hours, "T1 (10)"), and the test file's comments call
it "the assignment." The handout mentions the module only once, in passing, in
the `pytest.ini` bullet ("so plain `pytest tests/` can import
`data/feature_engineering.py`"). It is absent from the Starter Kit list, from
the Task 1 text, and from *The complete list* of submitted files. The handout
also never gives the required function names or signatures.

**Why it could confuse or block students:** A student reading only the handout
treats the module as something that should already exist. `test_features.py`
runs in `pre_build`, so until the module exists **every build fails before
training**, nothing can reach Register, and none of Task 2 can be demonstrated.
The error message names the fix, but a student meets it only after copying in
the kit and running pytest. Students planning their time from the handout will
also underestimate Task 1 by about an hour.

**Belongs in:** Both. The student tips explain the module and its signatures.

**Suggested revision:** Add to Task 1, under *Feature engineering unit tests*:

> **You write `data/feature_engineering.py`.** Lab 2's features are PySpark, which
> cannot run in a unit test. Port the same computations to pandas, in functions
> `test_features.py` imports:
> `compute_recency_features(transactions, as_of, customer_ids=None, sentinel=999.0)`,
> `compute_frequency_features(transactions, as_of, customer_ids=None)`,
> `compute_monetary_features(transactions, as_of, customer_ids=None)`,
> `compute_behavioral_features(transactions, as_of=FEATURE_CUTOFF, customer_ids=None)`,
> `build_churn_feature_set(customers, transactions, snapshot_date)`.
> They must match your Glue job definition for definition (windows are
> `purchase_date > T − N days`; `avg_basket_size_6m` is items per order). Until
> this file exists, `pre_build` fails on every push.

Also add `data/feature_engineering.py` to the Starter Kit list (as "you
create") and to *The complete list* (Task 1).

## 2. The grading guide deducts for pandas↔Glue disagreement, but the handout asks for no evidence of agreement

**Finding (verified, grading guide vs handout):** The TA guide says: "Ask for,
or look for, evidence that the port agrees with the Glue output (the gold repo
has `docs/lab4-feature-equivalence.txt`). If the two disagree … −3." The
Deductions table repeats "pandas port disagrees with Lab 2 definitions: −3."
The handout does not mention equivalence, does not list
`lab4-feature-equivalence.txt`, and says Task 1 is graded from the four test
files and `lab4-build-green.log`. The solution notes (Phase 1, 8.3) do list the
file.

**Why it could confuse or block students:** The handout says "File names are
exact" and "If the evidence is not committed … the task was not done," so
students treat *The complete list* as exhaustive. A TA following the guide
would then deduct for evidence that was never requested, and the TA can't
"ask for" it after the stack is torn down. Grading will also differ by TA:
some will look for the file and some won't.

**Belongs in:** Instructor notes, plus a student tip recommending the check.

**Suggested revision:** Choose one:

- (a) Require it. Add `docs/lab4-feature-equivalence.txt | 1 | Max absolute
  difference per feature between your pandas port and the Glue output` to
  *The complete list*, and add the solution notes' five-line comparison
  snippet to Task 1.
- (b) Don't require it. Change the guide so that −3 applies only when a
  definition is visibly wrong in the code or tests (for example, a
  dollars-per-order basket size), not when an evidence file is missing.

## 3. The two `test_data.py` TODOs that are graded are not in the handout's Task 1 list

**Finding (verified):** The handout's data-validation bullets are schema, grain,
"Leakage check: `churn_label` is not perfectly separable by recency alone",
distribution, and freshness. The kit already implements the recency-separability
leakage test (`test_label_not_trivially_separable`). The kit's TODO asks for a
**different** leakage test: recompute the time-sensitive features from rows
≤ cutoff and compare them with the Glue output. The grading guide grades that
TODO ("The two `test_data.py` TODOs … Leakage. Full credit recomputes … half
credit" for a filter-first version). Freshness is in both the handout and the
kit TODO, so it is not a problem.

**Why it could confuse or block students:** Reading the handout, a student
sees the leakage bullet already satisfied by a shipped test and reasonably
skips the TODO. The grading guide then grades a requirement that only a code
comment states. The obvious implementation (`max(purchase_date) <= cutoff`) also
fails on correct data. The kit comment warns about this, but the handout doesn't.

**Belongs in:** Both.

**Suggested revision:** Replace the leakage bullet with:

> - Leakage checks (two): the shipped `churn_label` is not perfectly separable by
>   recency alone; **and you add** a test that recomputes recency, tenure and the
>   30/90/180-day frequencies from processed rows with `purchase_date <=
>   2026-04-01` and asserts they equal what Glue wrote. (`processed/` contains the
>   holdout purchases, so "no purchase after the cutoff" is false on correct data.)

## 4. The champion regression test ships with no stub and no data contract

**Finding (verified, kit + `pipeline_definition.py`):** `tests/test_model.py`
has no regression test and no TODO for one, unlike every other Task 1 item.
The handout says only "retrieves champion AUC from Model Registry." It never
says where the AUC is stored. A pipeline-registered package has no AUC in its
`CustomerMetadataProperties`: `RegisterModel` sets only `ModelMetrics`, which
points at `s3://<data-bucket>/artifacts/evaluations/<sha8>/evaluation_metrics.json`.
The handout also never names the metrics key (`auc_roc`), and the
`churn_model.py` contract requires only the four gate keys. The solution notes
give a working `champion_from_registry()` that reads the S3 object, but the
handout does not point to it.

**Why it could confuse or block students:** This item is worth 8 points, and
the guide gives 3/8 for a hardcoded champion and 4/8 for "newest package of
any status." Both are the natural fallbacks for a student who can't find the
AUC on the package. A student whose Lab 3 `evaluate_model()` named the key
differently gets a `KeyError` only in CI.

**Belongs in:** Both.

**Suggested revision:** Add a commented stub to `tests/test_model.py`:
`list_model_packages(ModelApprovalStatus="Approved", SortBy="CreationTime",
SortOrder="Descending", MaxResults=1)` → `describe_model_package(arn)` →
follow `ModelMetrics.ModelQuality.Statistics.S3Uri` → read `auc_roc`. Then add
one sentence to the handout:

> The champion's AUC is not on the package itself; `ModelMetrics` points at the
> `evaluation_metrics.json` its training job wrote. Your metrics dict must
> include `auc_roc`.

Also add `auc_roc` to the required keys in `churn_model.py`'s docstring.

## 5. The ALARM state lasts only about 5 minutes, so the `AFTER FAILED RUN` snapshot window is short

**Finding (Inferred from `pipeline.yaml`; consistent with solution notes 1.7
and 6.3, not yet observed by me):** `BuildFailureAlarm` uses `Period: 300`,
`EvaluationPeriods: 1`, `TreatMissingData: notBreaching`. After the one
`FailedBuilds` datapoint, the next 5-minute period has no data, which is
treated as not breaching, so the alarm should return to `OK` on its own
roughly 5–7 minutes after the failure, *whether or not the revert has been
pushed*. The handout's wording ("Revert and push. Wait for the green build
and for the alarm to return to `OK`") implies that the green build causes the
recovery. The `OK` transition also sends an `OK:` email, because `OKActions`
is set.

**Why it could confuse or block students:** A student who pushes the failure,
leaves, and runs `snap "AFTER FAILED RUN"` 10 minutes later records `OK`, not
`ALARM`. The rubric item (6 points) requires `ALARM` in that snapshot. The
action history will still show the ALARM transition, but the state line won't
match the rubric text. A student may also screenshot the `OK:` email instead
of the `ALARM:` one.

**Belongs in:** Both.

**Suggested revision:** In step 2 of *Recording the demonstration*, add:

> Run `snap "AFTER FAILED RUN"` as soon as the alarm reads `ALARM`. It returns
> to `OK` by itself about five minutes later (one quiet evaluation period), and
> sends an `OK:` email when it does. Screenshot the `ALARM:` email, not the `OK:` one.

In step 3, change "for the alarm to return to `OK`" to "confirm the alarm reads `OK`."

**To verify:** my own failure demo. Record the ALARM→OK interval here.

## 6. Lab 5's handout contradicts Lab 4's approval and teardown steps

**Finding (verified, text conflict; consequence inferred):** Lab 5 line 63 says
"Lab 4 registered your model as `PendingManualApproval`. Nothing in Labs 1–4
ever approves it." Lab 4 now requires approving a champion (Recommended order,
step 1), and its teardown says "set any `Approved` package to `Rejected`" and
run `teardown-lab2.sh`, which deletes the data bucket that holds every model
artifact (`artifacts/training/...`).

**Why it could confuse or block students:** A student who follows Lab 4's
teardown exactly starts Lab 5 with no deployable artifact (the S3 object is
gone) and only `Rejected` packages, while Lab 5 says to look for a
`PendingManualApproval` package. They then have to re-run Lab 2 and a Lab 4
pipeline run without being told to.

**Belongs in:** Instructor notes, plus a student tip about not tearing down
more than necessary before Lab 5.

**Suggested revision:** Update Lab 5 line 63 to:

> Lab 4 left your champion `Rejected` and (if you ran `teardown-lab2.sh`) deleted
> its artifact. Re-apply Lab 2 and push once to register a fresh
> `PendingManualApproval` package, or, if your data bucket still exists,
> re-approve your Lab 4 champion.

Alternatively, have Lab 4 teardown say "if you are going straight to Lab 5,
keep the data bucket."

## 7. The kit's `.gitignore` does not exclude the data the kit downloads into the repo

**Finding (verified, `.gitignore`, `buildspec.yml`, `test_data.py` docstring):**
`test_data.py`'s "Run locally" instructions and the buildspec stage data at
`./data/northstar-raw-sample.csv`, `./data/processed/`, `./data/features/`
(inside the repo). The kit's `.gitignore` excludes none of these. Because
`data/feature_engineering.py` must be committed, students cannot ignore the
whole `data/` directory. The solution notes (0.6) cover this, but the handout
doesn't.

**Why it could confuse or block students:** A student following the test
docstring and then running `git add -A` (as solution notes 8.5 suggests)
commits a 13 MB CSV and the Parquet output to a public repo. That's not a
secret, but it bloats every clone and the TA's `ta_clone.py`.

**Belongs in:** Both.

**Suggested revision:** Add to the kit `.gitignore`:
`data/*.csv`, `data/processed/`, `data/features/`, `reports/`. Add a one-line
note under the `pytest.ini` bullet.

## 8. Placeholder tests pass vacuously, and the kit already meets the "≥5 feature tests" count

**Finding (verified):** Two shipped `test_features.py` tests contain only
comments and `pass`
(`test_customer_with_no_transactions_returns_sentinel`) or compute a value and
assert nothing (`test_no_null_features_for_known_customers`). Both report
`PASSED`. The kit already has 18 feature tests and 26 data tests (the grading
guide confirms "the kit alone has 26 and 18 before the TODOs"). The zero-purchase
sentinel test is the handout's named boundary case, and it is one of the
placeholders.

**Why it could confuse or block students:** The rubric's log evidence ("≥5
`test_features.py ... PASSED` lines") is met by an untouched kit. A student
can collect the PASSED lines for the named boundary case without implementing
it. Students may also read "≥5 feature unit tests" as a count they already
meet and add no edge cases.

**Belongs in:** Instructor notes (TA grading), plus a student tip.

**Suggested revision:** In the kit, change both placeholders to
`pytest.fail("TODO: implement")` (or `pytest.xfail`) so an unimplemented test is
visibly not passing. In the handout rubric, say:

> The kit's tests don't count toward this item; you add at least one boundary
> and one edge test of your own, and fill the two TODOs.

In the grading guide, tell TAs to open the bodies of the two placeholder tests.

## 9. The handout's teardown misses the CodeBuild report group and assumes `$AB` is still set

**Finding (verified):** Solution notes 8.4 include
`aws codebuild list-report-groups  # delete northstar-ci-northstar-test-reports`.
The handout's teardown does not. The buildspec's `reports:` block creates the
report group, which CloudFormation doesn't own. The handout's
`aws s3api delete-bucket --bucket "$AB"` relies on a shell variable defined in
prerequisite 1, often days earlier.

**Why it could confuse or block students:** These are minor. The report group
is left behind (I believe report groups have negligible cost, but I haven't
checked). An unset `$AB` makes `delete-bucket` fail with a confusing parameter
error.

**Belongs in:** Both (minor).

**Suggested revision:** In teardown, re-derive `AB=northstar-dev-cicd-artifacts-$(aws sts get-caller-identity --query Account --output text)`
first, and add
`aws codebuild delete-report-group --arn $(aws codebuild list-report-groups --query 'reportGroups[?contains(@, \`northstar-ci\`)]' --output text) --delete-reports`.

## 10. The metric names still come in two vocabularies (known open thread, low)

**Finding (verified; already listed as open in the instructor session handoffs):**
The handout says the training script "has to emit `baseline_auc_roc`." The
Lab 3 skeleton and the student Lab 3 code emit `baseline_auc` /
`auc_vs_baseline`. `train_sagemaker.normalise_metrics()` copies only
canonical → alias (`baseline_auc_roc` → `baseline_auc`), never the other way.
Nothing gates on either name, so this blocks no one.

**Why it could confuse:** Students may rename working Lab 3 keys to match the
handout and then wonder why both names appear in `evaluation_metrics.json`.

**Belongs in:** Instructor notes only.

**Suggested revision:** Change the handout to "emit the baseline AUC
(`baseline_auc` or `baseline_auc_roc`) and the CI bounds (`lift_ci_low`,
`lift_ci_high`)."

## 11. Both solution guides predate the Oct 23 evidence rewrite

**Finding (verified, git history + grep):** The TA grading guide
(`Lab 4 - XOps & CICD (Solution).md`) and the student walkthrough
(`Lab_4--Solution Notes.md`) were last changed 2026-10-19 (`ebac039`). The
handout's evidence section, its Evidence columns, and four new files arrived
in `45a2677` (2026-10-27). Neither guide mentions `lab4-build-green.log`,
`lab4-build-failed.log`, `lab4-model-registry.json`, `lab4-alarm-email.png`, the
`BEFORE` snapshot, the five required assessment headings, the MLflow App URI
requirement, or the `git show` authorship check (0 matches each).

Two old-guide rules also conflict with the new Evidence column:

- 2.2 accepted a `BUILD`-gate failure; the handout now names `PRE_BUILD FAILED`.
- 2.4 accepted an older action line when the alarm was already red; the handout
  now requires `OK` in `BEFORE`.

**Why it matters:** TAs grading from the old guide will not check most of the
required evidence, and they will apply criteria the handout no longer states.
The old guide also has no policy for students who tore down before the
clarification (the handout tells them to contact the TA).

**Belongs in:** Instructor notes only.

**Suggested revision:** Adopt `grading/lab4/ta_grading_guide.md`, my updated
draft with 12 flagged decisions (D1–D12) for the professor. For the
walkthrough, adopt `grading/lab4/lab4_solution_notes.md`, my updated copy with
the evidence map, `snap`/`save_log`, the capture block and the handout's
evidence order. It should replace the original before release after the deadline.

## 12. Smaller wording issues (low)

All verified by reading. Instructor notes only.

- **Lineage "timestamp" is ambiguous.** "Training data version (S3 URI +
  timestamp)" could mean training start time, the data's `LastModified`, or
  the feature job's `event_time`. The rubric says "its timestamp" (the data's).
  Suggest: "the newest `LastModified` under the training data URI."
- **`test_features.py` header says "have the Glue job and these tests share
  that logic."** The handout and solution notes say to copy the logic, and a
  Glue PySpark job can't import a pandas module without packaging work. Suggest:
  "port the same logic, and prove the two agree."
- **`test_model.py` comment refers to `churn_training_skeleton.py`.** In Lab 4
  the source of truth is `models/churn/churn_model.py`.
- **`aws s3api create-bucket --bucket "$AB"` works only in us-east-1.**
  Solution notes 5.1 say so; the handout doesn't. Suggest a trailing comment.
- **"Five phases" vs. the Evaluate phase running twice.** The handout's stage
  table says `pre_build runs pytest tests/`, but the buildspec runs only
  `test_data.py` and `test_features.py` in `pre_build`; `test_model.py` and
  `test_fairness.py` run in `build`. The Task 2 phase list also says "Test —
  runs `pytest tests/`." Suggest: "Test — `pre_build` runs the data and feature
  tests; the model and fairness tests run after training, in `build`."

## 13. The Phase 1 walkthrough snippet looks complete but isn't

**Finding (verified by reading, and by my own run-through on 2026-10-29).**
Under "The core of it", Phase 1 of the solution notes shows a code block that
reads like a finished module. It is about 40% of one:

- No `import numpy as np`, which `compute_monetary_features` uses.
- No `_ids()`, which both functions it shows call.
- No `compute_recency_features`, `compute_frequency_features` or
  `build_churn_feature_set`. The prose says they "follow the same pattern".

The equivalence snippet also calls `build_churn_feature_set(None, proc)`. The
signature it gives takes a required `snapshot_date`, so that call raises
`TypeError`. The snippet also leaves `D` and `FEATURE_COLUMNS` undefined.

**Why it blocks students.** I pasted the block under the five empty stubs and
got a module that fails on import (`NameError` on `np` or `_ids`). Three of
the five functions still take no arguments, so `pre_build` fails with
`Could not import data.feature_engineering`. Students also come away unsure
whether the port is meant to match the Glue job or replace it.

**Belongs in:** Both. Instructor notes for the fix; a student tip that the
snippet is partial.

**Suggested revision.** Label the block "Partial: you still write `_ids`,
recency, frequency and `build_churn_feature_set`". Add the imports. Change the
equivalence call to
`build_churn_feature_set(None, proc, FEATURE_CUTOFF)`, with `customers=None`
allowed. Add one sentence: "Glue stays the production job. This module is a
copy that the leakage test in 2.2 checks against Glue's output on every build."

## 14. The Phase 3 `train()` sample calls a `train_model` signature that Lab 3 doesn't have

**Finding (verified by reading, 2026-10-30).** The solution notes' `train()`
calls `train_model(X_train, y_train, X_val, y_val, hp, seed=seed)`: a dict
plus a `seed` keyword. Lab 3's `train_model()`, in both the template and
`models/churn/train.py`, is `train_model(X_train, y_train, X_val, y_val, args)`.
It reads attributes (`args.max_depth`, `args.scale_pos_weight`,
`args.num_round`), takes no `seed`, and writes `args.resolved_scale_pos_weight`.
The sample also uses `train_test_split` without showing its import.

**Why it blocks students.** A student who pastes their Lab 3 functions plus the
sample `train()`, as I did, gets a `NameError` (`train_test_split`), then a
`TypeError` (`seed`), then an `AttributeError` (dict has no `max_depth`). That
costs a 6-minute pipeline run each time if they skip the local test.
`HYPERPARAMETERS` also has no `scale_pos_weight` key, which Lab 3's
`train_model` reads.

**Belongs in:** Both. The fix goes in the instructor notes; the student tip
is "adapt the call to your Lab 3 signature".

**Suggested revision.** Show the adapter that matches Lab 3:
`args = SimpleNamespace(**HYPERPARAMETERS, scale_pos_weight=None)` and
`train_model(X_train, y_train, X_val, y_val, args)`. Alternatively, say
outright that the sample assumes a refactored `train_model(..., params, seed)`.
Add `from sklearn.model_selection import train_test_split` to the snippet.

## 15. The recency monotonicity test probes impossible customers and fails on the reference numbers

**Finding (verified on my local run, 2026-10-30).** My model reproduced the
walkthrough's Phase 3 local numbers exactly: AUC 0.7796, lift CI low 0.0366,
best iteration 36, xgboost 3.2.0. Even so, `test_model_monotone_on_recency`
failed: `[(60, 90, 0.054)]`, with scores 0.238, 0.403, 0.450, 0.396, 0.724,
0.849. The walkthrough says to expect "26 passed and 1 skipped". *Assumption:*
the reference run used a different probe or a different model; I can't tell
which.

The probe holds every other feature fixed while recency goes from 5 to 200
days, which produces combinations that can't occur:

- `purchase_frequency_30d = 2` and `purchase_frequency_180d = 6`, even at
  recency 60–200 days;
- `avg_basket_size_6m = 85.0`, which is a dollar-scale value. The feature is
  items per order, usually 1–5.

A tree model has never seen these rows, so its scores there are arbitrary.

**Why it blocks students.** A model that passes every real gate fails CI, and
the student can't tell whether their model or the test is wrong. Container
XGBoost (1.7) builds different trees, so the test may pass or fail
differently there.

**Belongs in:** Both.

**Suggested revision.** Make the probe consistent with its recency: zero the
frequencies whose windows the recency excludes, and use a realistic basket
(around 3 items). Alternatively, tell students to add
`monotone_constraints` on `days_since_last_purchase` if they want the
property guaranteed.

**What I did (2026-10-30).** I added `monotone_constraints` (1 on
`days_since_last_purchase`) to `train_model` and left the test unchanged.
`grading/lab4/progress.md` ("Decisions") has the before/after numbers once
I've retrained. If the professor wants students to do the same, the
walkthrough's 2.3 and Phase 3 should mention it.
