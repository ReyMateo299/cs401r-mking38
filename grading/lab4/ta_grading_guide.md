# Lab 4 — XOps + CI/CD + Testing: TA Grading Guide (updated for the evidence-file structure)

> **Status:** draft by Matt King (TA), 2026-10-28. Not for students.
> **Replaces, for grading purposes:** `Sample Solutions/Lab Solution Notes/Lab 4 - XOps & CICD (Solution).md`,
> last changed 2026-10-19 (commit `ebac039`).
> **Aligned to:** `Lab_4--XOps & CICD.md` as of commit `45a2677` (2026-10-27), which added the
> Evidence column to every rubric table, the *Evidence You Submit* section, four new evidence
> files, the `BEFORE` snapshot, and required headings in `docs/lab4-xops-assessment.md`.
> Total: 100 points. Test Suite 30 · CI/CD Pipeline 30 · MLOps Configuration 20 · XOps Maturity 20.

## How to read this guide

Every scoring rule is tagged by where it comes from:

- **[Handout]**: stated in the current handout's rubric or Evidence column. Apply it as written.
- **[2026-10-19 guide]**: carried over unchanged from the previous TA guide, and still consistent with the handout.
- **[Proposed]**: new, or changed to fit the handout. **Needs the professor's sign-off before grading.**
  Each one is also listed under [Decisions needed](#decisions-needed-before-grading).

## What changed from the 2026-10-19 guide

| Area | 2026-10-19 guide | Handout now (2026-10-27) | This guide |
|---|---|---|---|
| Evidence files | 2 named (`lab4-pipeline-runs.txt`, `lab4-failure-demo.txt`) | 12 files plus git history, names exact | Full checklist (§1) and per-item evidence |
| `lab4-build-green.log` | not mentioned | Task 1 (all three items) and Task 2 item 1 | Checked in §2 and §3 |
| `lab4-build-failed.log` | not mentioned | Task 2 item 2 | §3 |
| `lab4-model-registry.json` | not mentioned | Task 1 regression, Task 2 item 3 | §2, §3 |
| `lab4-alarm-email.png` | not mentioned | Task 2 item 4 | §3 |
| Failure-demo snapshots | "the failure demo" | `BEFORE` / `AFTER FAILED RUN` / `AFTER REVERT`, same newest version in the first two | §3 |
| Halt criterion | "PRE_BUILD (or BUILD gate) FAILED" | `PRE_BUILD FAILED`, no `BUILD` phase | §3; conflict flagged (D2) |
| Notification | ALARM + *Successfully executed action*; an older action line accepted if already red | `OK` in BEFORE, `ALARM` after, confirmed subscription ARN, plus email screenshot | §3; conflict flagged (D3) |
| `churn_model.py` authorship | grep for `NotImplementedError` | `git show <green-build SHA>:models/churn/churn_model.py` | §3 |
| Deliberate-failure commits | not mentioned | Both in `main` history, SHA matches the failed build | §3 |
| MLflow | `search_runs` output | `lab4-mlflow-runs.txt` whose tracking URI is an MLflow App ARN | §4 |
| Lineage | data URI and commit SHA | data URI, its timestamp, commit SHA, eval metrics in `CustomerMetadataProperties`; SHA in `main` history | §4 |
| Assessment headings | none required | five exact `##` headings | §4, §5 |
| Task 4 citations | "names files" | every cited path must exist at the tag | §5 |
| "Missing evidence → item = 0" | Task 2 only | every rubric item now names evidence | applied to all items [Proposed, D1] |
| Late clarification | — | "If you have already torn your stack down, tell the TA before the deadline" | §0 policy [Proposed, D4] |

---

## 0. Before you start

**You grade the `lab4-submit` tag only, from the repository.** [Handout] Student AWS accounts are
standalone and you have no access to them. Every Task 2 and Task 3 AWS fact is graded from files in
`docs/`. If the tag is missing, grade the last commit before the Canvas deadline. [Handout]

```bash
python3 ta_clone.py 4                         # grading/lab4/<student> at lab4-submit
cd grading/lab4/<student>
git describe --tags --exact-match HEAD        # expect lab4-submit
bash scripts/check-secrets.sh                 # never `git log -S AKIA`
```

**Students who tore down before the Oct 23 clarification.** [Proposed, D4] Before grading, get from
the professor the list of students who told the TA before the deadline. For those students only,
a missing *new* file (`lab4-build-green.log`, `lab4-build-failed.log`, `lab4-model-registry.json`,
`lab4-alarm-email.png`, or the `BEFORE` snapshot) does not zero the item. Grade that item from
the evidence the pre-Oct-23 handout required (`lab4-pipeline-runs.txt`, `lab4-failure-demo.txt`,
`lab4-model-package.json`, `lab4-mlflow-runs.txt`) and note it in feedback. Everyone else is graded
on the full list.

### Old-kit symptoms: do not deduct [2026-10-19 guide]

| Symptom in their evidence | Old-kit cause | Fixed by |
|---|---|---|
| INSTALL fails: `Could not open requirements file` | no `requirements.txt` | kit ships one |
| `data/feature_engineering.py not found` under plain `pytest` | no `pytest.ini` | kit ships one |
| `test_avg_basket_size_correct` expected ~365 | test used dollars; Lab 2 defines items/order | test expects 5.0 |
| `test_model_monotone_on_recency`: "Only 3/5 pairs increasing" | ties counted as failures | tolerant test |
| TrainChurnModel: `iam:PassRole` denied | MLEngineer cannot pass itself | handout prerequisite 4 |
| A failed build left a `PendingManualApproval` package | registration precedes the CodeBuild gate | buildspec `post_build` auto-rejects |

### Reference run (2026-10-19, account 711457211658) [2026-10-19 guide]

| Measure | Value |
|---|---|
| install / pre_build / SageMaker Pipeline / model gate | 36–74 s / 5–7 s / ~210–240 s / ~1.5 s |
| Training on `ml.m5.large` spot | 155 s, 60 s billable |
| pre_build tests | test_data 28, test_features 24 (gold; the kit alone has 26 and 18 before the TODOs) |
| Build-phase gate | test_model 21 + test_fairness 6 (gold) |
| Container model (XGBoost 1.7.4) | AUC 0.7823, baseline 0.7208, lift CI [0.0415, 0.0812], P@10 0.7167, R@10 0.3258 |
| Same code, local XGBoost 3.2 | AUC 0.7796, baseline 0.7233, lift CI [0.0366, 0.0749], P@10 0.7067, R@10 0.3212 |
| Fairness flag | recall@10 gap ≈ 32 pts (Bronze 0.41 vs Platinum 0.10): expected, flag-only |

---

## 1. Evidence checklist

Run this first. File names are exact. [Handout: *The complete list*]

```bash
for f in tests/test_data.py tests/test_features.py tests/test_model.py tests/test_fairness.py \
         models/churn/churn_model.py buildspec.yml pipeline.yaml \
         docs/lab4-build-green.log docs/lab4-build-failed.log docs/lab4-pipeline-runs.txt \
         docs/lab4-failure-demo.txt docs/lab4-alarm-email.png docs/lab4-model-registry.json \
         docs/lab4-model-package.json docs/lab4-mlflow-runs.txt docs/lab4-xops-assessment.md; do
  [ -s "$f" ] && echo "ok       $f" || echo "MISSING  $f"
done
```

A GitHub Actions or GitLab CI config may stand in for `buildspec.yml` + `pipeline.yaml`. [Handout]

| File | Task | Rubric items that depend on it | What it must show [Handout] |
|---|---|---|---|
| `tests/test_*.py` (4 files) | 1 | 1.1, 1.2, 1.3 | The tests themselves |
| `models/churn/churn_model.py` | 2 | 2.1 | Their Lab 3 logic behind `train()` |
| `buildspec.yml`, `pipeline.yaml` | 2 | 2.1 | The five phases |
| `docs/lab4-build-green.log` | 1, 2 | 1.1, 1.2, 1.3, 2.1 | Full log of the final green build: every test file's `-v` output, champion and fairness warnings, SageMaker Pipeline `Succeeded`, package registered |
| `docs/lab4-build-failed.log` | 2 | 2.2 | Full log of the deliberate-failure build: the failing assertion, `PRE_BUILD` failed |
| `docs/lab4-pipeline-runs.txt` | 2 | 2.1 | Every run: commit, status, phases, pytest summary, SageMaker Pipeline executions |
| `docs/lab4-failure-demo.txt` | 2 | 2.2, 2.3, 2.4 | `BEFORE`, `AFTER FAILED RUN`, `AFTER REVERT` snapshots |
| `docs/lab4-alarm-email.png` | 2 | 2.4 | The `ALARM` email as received, with its time |
| `docs/lab4-model-registry.json` | 1, 2 | 1.3, 2.3 | Every package version and status, including the `Approved` champion |
| `docs/lab4-model-package.json` | 3 | 3.4 | Lineage in `CustomerMetadataProperties` on the final green run's package |
| `docs/lab4-mlflow-runs.txt` | 3 | 3.3 | MLflow App tracking URI; ≥3 runs with params and metrics |
| `docs/lab4-xops-assessment.md` | 2, 3, 4 | 2.1, 3.1, 3.2, 4.1–4.3 | `## Pipeline Stage Mapping`, `## Champion-Challenger`, `## Retraining Triggers`, `## DataOps Maturity`, `## MLOps Maturity` |
| Git history on `main` | 2 | 2.2 | The deliberate-failure commit and its revert |

Optional, not required: `docs/lab4-mlflow-compare.png` (supports 3.3; does not replace the text file) [Handout];
`docs/lab4-feature-equivalence.txt` (see D5).

**Missing evidence.** [Proposed, D1] A missing or empty file scores 0 on every item that depends on
it *only through that file*. For example, a missing `lab4-alarm-email.png` zeroes 2.4, but a missing
`lab4-build-green.log` does not erase the code-reading part of 1.2. Old guide: "Missing evidence
file for a Task 2 item → that item = 0."

---

## 2. Task 1 — Test Suite (30)

Offline checks you can run on the clone:

```bash
NORTHSTAR_FEATURES=/nonexistent python -m pytest tests/test_data.py -q   # must FAIL/ERROR, not skip or pass
ALLOW_MISSING_DATA=1 python -m pytest tests/test_features.py tests/test_fairness.py -q   # unit tests run offline
G=docs/lab4-build-green.log
for t in test_data test_features test_model test_fairness; do
  printf '%-14s PASSED=%s SKIPPED=%s FAILED=%s\n' $t \
    "$(grep -cE "tests/$t\.py::.* PASSED" $G)" "$(grep -cE "tests/$t\.py::.* SKIPPED" $G)" \
    "$(grep -cE "tests/$t\.py::.* FAILED" $G)"
done
grep -nE 'champion v[0-9]+ auc=' $G          # regression-test record
grep -niE 'fairness|recall.*gap' $G | head    # fairness flag in the warnings summary
```

### 1.1 All 4 test categories implemented (12)

| | |
|---|---|
| **Pass criteria** [Handout] | Each category has ≥2 passing tests |
| **Evidence** [Handout] | The four files in `tests/`, plus `lab4-build-green.log` showing each of the four files with ≥2 `PASSED` lines. **`SKIPPED` does not count.** The fairness flag should appear in the warnings summary |
| **Check** | Counts from the loop above; open each file |
| **Deductions** | Missing data skips or passes instead of failing: **−6** [2026-10-19 guide; the handout requires FAIL]. A category with <2 `PASSED` in the green log: **−3 per category** [Proposed, D6]. `test_fairness.py` absent from the green log: treat as missing category |

The two `test_data.py` TODOs [2026-10-19 guide]:

- **Leakage (post-cutoff).** Full credit recomputes the time-sensitive features from processed rows
  ≤ cutoff and compares them with Glue's output. `max(purchase_date) <= cutoff` fails on correct data
  (processed data contains the holdout). If they "made it pass" by filtering first, it tests nothing:
  half credit. *Note: the handout's leakage bullet names only the shipped separability test; see D7.*
- **Freshness.** Reads `event_time` (epoch seconds, the Glue run time) against 48 h. Comparing
  against the cutoff date (2026-04-01) is a conceptual error.

### 1.2 ≥5 feature unit tests with edge cases (10)

| | |
|---|---|
| **Pass criteria** [Handout] | Tests cover normal, boundary, and edge cases |
| **Evidence** [Handout] | `tests/test_features.py`: **read the test names and bodies**, plus ≥5 `test_features.py ... PASSED` lines in `lab4-build-green.log` |
| **Full credit** [2026-10-19 guide] | Boundary (zero purchases → sentinel with no NaN; purchase on the cutoff day; the 90-day window edge) and edge (single transaction) cases |
| **Watch for** [Proposed, D8] | The kit already has 18 tests, so the PASSED count is met by an untouched kit. Two kit placeholders pass vacuously: `test_customer_with_no_transactions_returns_sentinel` (body is `pass`) and `test_no_null_features_for_known_customers` (no assert). If the named boundary case is still the placeholder, it does not count |
| **Definitions** [2026-10-19 guide] | `avg_basket_size_6m` is items per order; `category_diversity_score` excludes `unknown` and divides by 8. A port that disagrees with Lab 2: **−3** (see D5 about evidence) |

### 1.3 Regression test compares against champion (8)

| | |
|---|---|
| **Pass criteria** [Handout] | Test retrieves the champion AUC from the Model Registry and fails if the new model regresses. Champion = newest **Approved** package |
| **Evidence** [Handout] | Code in `tests/test_model.py`; `lab4-build-green.log` shows the regression test **`PASSED` (not skipped)** with the `champion vN auc=...` warning; `lab4-model-registry.json` shows version N as `Approved` |
| **Cross-check** | The N in the warning matches an `Approved` entry in the registry JSON (snippet below) |
| **Scoring** [2026-10-19 guide] | Newest package of any status (compares with itself): 4/8. Hardcoded champion AUC: 3/8. A registry error that skips silently: −2. An empty registry is a legitimate skip *in code* |
| **New case** [Proposed, D9] | Code correct but the test `SKIPPED` in the final green log (no champion approved first): **4/8** |

```bash
python3 -c "import json; d=json.load(open('docs/lab4-model-registry.json'));
[print(p['ModelPackageVersion'], p['ModelApprovalStatus'], p['CreationTime']) for p in d['ModelPackageSummaryList']]"
```

### Fairness (within 1.1) [2026-10-19 guide]

A flag, never a block. A test that *fails* the build on the gap: **−3**. A silent flag (no warning
or log line naming the tiers and gap): **−2**. Tiers with fewer than ~20 positives should be marked
unreliable. Clarify is allowed but not expected (processing quota on new accounts covers only `ml.t3.*`).

---

## 3. Task 2 — CI/CD Pipeline (30)

Graded from evidence only; the TA cannot re-run the pipeline. [Handout]

```bash
D=docs/lab4-failure-demo.txt
grep -n '^===== ' $D                                       # expect BEFORE, AFTER FAILED RUN, AFTER REVERT
awk '/^===== AFTER FAILED RUN/,/^===== AFTER REVERT/' $D    # read the failed-run snapshot
SHA=$(awk '/^===== AFTER FAILED RUN/{f=1} f&&/^[0-9a-z:-]+\t[0-9a-f]{40}\t/{print $2; exit}' $D)
git merge-base --is-ancestor "$SHA" lab4-submit && git show --stat "$SHA"   # failing commit in history
git log --oneline lab4-submit | grep -i -m3 revert
grep -nE 'Phase complete: PRE_BUILD +State: FAILED|FAILED|[0-9]+ failed' docs/lab4-build-failed.log | head
grep -nE 'Pipeline succeeded|Registered: arn:' docs/lab4-build-green.log
```

The `SHA=` extraction assumes the snapshot's tab-separated `id  sha  status` line. If it comes back
empty, read the SHA by eye. The `Phase complete` wording is CodeBuild's usual log format; I haven't
checked it against a real student log yet.

### 2.1 All 5 phases present, ordered, with a documented stage mapping (10)

| | |
|---|---|
| **Pass criteria** [Handout] | Config plus mapping shows all five phases; a green run trained **their** Lab 3 model through `churn_model.train()` and reached Register |
| **Evidence** [Handout] | `buildspec.yml` + `pipeline.yaml` (or GH Actions / GitLab CI); `## Pipeline Stage Mapping` in `docs/lab4-xops-assessment.md`, mapping five phases to stages **with rationale**; `lab4-pipeline-runs.txt` with a `SUCCEEDED` build whose phases run through `POST_BUILD`; `lab4-build-green.log` showing SageMaker Pipeline `Succeeded` and a package registered |
| **Authorship check** [Handout] | Take the SUCCEEDED build's `resolvedSourceVersion` from `lab4-pipeline-runs.txt`, then `git show <sha>:models/churn/churn_model.py`. It must not be the template (`raise NotImplementedError`) |
| **Scoring** | Template `train()` in every run: **max 4** [2026-10-19 guide]. Stage count is not graded; three stages is the reference [Handout]. Missing mapping heading or no rationale: **−3** [Proposed, D6] |

Reference mapping [2026-10-19 guide]:

| Phase | CodePipeline stage | Where |
|---|---|---|
| Source | `Source` | CodeConnections, `main`, DetectChanges |
| Test | `Build` | `pre_build`: test_data, test_features |
| Build | `Build` | `build`: upsert + start SageMaker Pipeline; `TrainChurnModel` on spot |
| Evaluate | `Build` | `evaluate_model()` inside training (blocks registration), then `test_model.py` in CodeBuild |
| Register | `Build` → `ManualApproval` | `RegisterChurnModel` (`PendingManualApproval`), then a human approves |

### 2.2 Pipeline halts correctly on test failure (8)

| | |
|---|---|
| **Pass criteria** [Handout] | The deliberate failure stopped the run in the phase that owns tests and did **not** reach Register |
| **Evidence** [Handout] | `lab4-failure-demo.txt` `AFTER FAILED RUN`: build `FAILED`, `PRE_BUILD FAILED`, **no `BUILD` phase**; `lab4-build-failed.log` showing the failing assertion; the deliberate-failure commit in `main` history with its SHA matching the build |
| **Notes** [2026-10-19 guide] | No `POST_BUILD` after a `pre_build` failure is correct: CodeBuild skips it, which is why the alarm watches `AWS/CodeBuild FailedBuilds` |
| **Conflict** | The old guide also accepted a BUILD-phase gate failure. The handout now names `PRE_BUILD FAILED` with no `BUILD` (see D2) |

### 2.3 Model Registry promotion only on green gates (6)

| | |
|---|---|
| **Pass criteria** [Handout] | No new version on the failed run; a new `PendingManualApproval` version on the clean one |
| **Evidence** [Handout] | `lab4-failure-demo.txt`: newest version **identical in `BEFORE` and `AFTER FAILED RUN`**; `AFTER REVERT` shows exactly one more version, `PendingManualApproval`; cross-checked against `lab4-model-registry.json` |
| **Old-kit allowance** [2026-10-19 guide] | A failed build that left a `PendingManualApproval` package still counts if the student rejected it by hand and explained why. With the current kit, `post_build` auto-rejects only BUILD-phase failures; a `PRE_BUILD` failure registers nothing |

### 2.4 Failure notification demonstrably delivers (6)

| | |
|---|---|
| **Pass criteria** [Handout] | Alarm reached `ALARM`, SNS accepted the notification, and it reached a confirmed subscriber |
| **Evidence** [Handout] | `lab4-failure-demo.txt`: `OK` in `BEFORE`, `ALARM` in `AFTER FAILED RUN`, *Successfully executed action* in the history, a **subscription ARN (not `PendingConfirmation`)**; plus `lab4-alarm-email.png` with subject starting `ALARM: "northstar-ci-build-failure"` and a visible received time (address may be blurred) |
| **Zero** [Handout] | An alarm that fires without delivering: 0. `Failed to execute action` in history: 0 [2026-10-19 guide] |
| **Timing sanity** [Proposed] | The email's received time should fall between the failed build's end and roughly 10 min after. With a 300 s period and `notBreaching`, the alarm likely returns to `OK` on its own about 5 min later (inferred, not yet observed), so an `OK` state in `AFTER FAILED RUN` plus an OK→ALARM→OK action history and a valid email is a timing slip, not a missing notification. See D3 |

---

## 4. Task 3 — MLOps Configuration (20)

```bash
A=docs/lab4-xops-assessment.md
for h in 'Pipeline Stage Mapping' 'Champion-Challenger' 'Retraining Triggers' 'DataOps Maturity' 'MLOps Maturity'; do
  grep -qE "^## +$h" $A && echo "ok       ## $h" || echo "MISSING  ## $h"
done
head -1 docs/lab4-mlflow-runs.txt | grep -q ':mlflow-app/' && echo "MLflow App URI ok" || echo "NOT an MLflow App URI"
python3 -c "import json; p=json.load(open('docs/lab4-model-package.json')); print(json.dumps(p.get('CustomerMetadataProperties',{}), indent=2))"
```

| Item | Pts | Evidence [Handout] | Full credit | Partial / zero |
|---|---|---|---|---|
| 3.1 Champion-challenger numeric and binary | 5 | `## Champion-Challenger` | A number and a yes/no rule. Reference: gates pass **and** AUC ≥ champion − 0.02 **and** no reliable tier loses > 0.05 AUC [2026-10-19 guide] | "If it's better": 0. A strict "+0.005 better" rule passes, but note in feedback that AUC's split-to-split sd is 0.029 [2026-10-19 guide] |
| 3.2 Both retraining triggers, automatable | 8 | `## Retraining Triggers`: per trigger, threshold or schedule expression **and** the AWS service that fires it. Designed, not deployed, is fine | Each has a threshold and a named firing service (EventBridge rule/Scheduler, CloudWatch alarm, Glue trigger) [2026-10-19 guide] | No mechanism: 3 [2026-10-19 guide]. Ignoring the 90-day label delay is fine for points; mention it |
| 3.3 ≥3 MLflow App runs | 4 | `lab4-mlflow-runs.txt`: tracking URI is an MLflow App ARN (`...:mlflow-app/...`); ≥3 rows with differing `params.*` and filled `metrics.*` | As stated | Identical runs: 2; pipeline-auto-generated SageMaker Experiments: 2 [2026-10-19 guide]. Tracking URI not an MLflow App (local `mlruns`, Tracking Server): **2** [Proposed, D10]. Params truncated to `...` so differences can't be seen: **2** [Proposed, D10] |
| 3.4 Lineage in the registry | 3 | `lab4-model-package.json`: `CustomerMetadataProperties` holds the training data S3 URI, its timestamp, the commit SHA, and the evaluation metrics. The SHA must be in `main` history | All four present; `git merge-base --is-ancestor <sha> lab4-submit` succeeds (an 8-char SHA from the training job is fine) | Only the SHA inside the metrics S3 path: 1 [2026-10-19 guide]. URI + SHA but missing timestamp or metrics: **2** [Proposed, D11]. SHA not in history: **1** [Proposed, D11] |

3.4 should be the **final green run's** package (the version in `AFTER REVERT`). [Handout]

---

## 5. Task 4 — XOps Maturity (20)

Graded on specificity. An honest Level 2 with file references beats a Level 4 claim in generic
language. [2026-10-19 guide]

**Path check** [Handout: "Every path you cite must exist at your `lab4-submit` tag; the TA opens them"]:

```bash
grep -oE '`[^` ]+\.(py|ya?ml|tf|md|txt|json|log|sh|png)(::[^` ]*)?`' docs/lab4-xops-assessment.md \
  | tr -d '`' | sed 's/::.*//' | sort -u | while read -r p; do [ -e "$p" ] || echo "MISSING $p"; done
```

| Item | Pts | Evidence [Handout] | Full credit / scoring |
|---|---|---|---|
| 4.1 Level supported by specific evidence | 10 | `## DataOps Maturity` and `## MLOps Maturity` | Names files and measured results (e.g. `buildspec.yml`, `tests/test_data.py::test_no_feature_uses_post_cutoff_data`, a line in `lab4-build-green.log`); citing a measured result beats citing a config [Handout]. Generic prose: ≤ 4 [2026-10-19 guide]. **Each cited path that doesn't exist at the tag: −1, max −4** [Proposed, D12] |
| 4.2 Gap is specific | 6 | The `Gap to Level` line of each section | "No production performance monitoring until Lab 6" or "Gate is not a ConditionStep before registration" = full; "need more automation" = 1 [2026-10-19 guide] |
| 4.3 Priority investment actionable | 4 | The `Top priority investment` line of each section | Names a specific tool or practice [Handout] |

Reference levels [2026-10-19 walkthrough]: DataOps 2, MLOps 2.

---

## 6. Deductions summary

| Issue | Deduction | Source |
|---|---|---|
| Tests skip instead of fail on missing data | −6 | 2026-10-19 guide |
| Gate passes on missing metrics (e.g. a `\|\| echo {}` fallback) | −8 | 2026-10-19 guide |
| Template `churn_model.py` at the green build's SHA | 2.1 max 4 | 2026-10-19 guide; check via `git show` per Handout |
| Champion = newest package of any status | −4 | 2026-10-19 guide |
| Hardcoded champion AUC | −5 | 2026-10-19 guide |
| Regression test only `SKIPPED` in the final green log | −4 | Proposed (D9) |
| Fairness check blocks the build | −3 | 2026-10-19 guide |
| Silent fairness flag | −2 | 2026-10-19 guide |
| pandas port disagrees with Lab 2 definitions | −3 | 2026-10-19 guide (evidence basis: D5) |
| Champion-challenger not numeric | −5 | 2026-10-19 guide |
| Retraining trigger with no firing service | −5 | 2026-10-19 guide |
| Pipeline-auto-generated Experiments as MLflow evidence | −2 | 2026-10-19 guide |
| Missing evidence file | dependent item(s) = 0 | Handout (Task 2) / Proposed for all tasks (D1) |
| Cited path missing at tag (Task 4) | −1 each, max −4 | Proposed (D12) |
| `.tfstate`, `.tfvars` or `.env` committed | −5 + flag | 2026-10-19 guide |
| AWS key in history (`check-secrets.sh`) | Task score 0 + email Scott | 2026-10-19 guide; the handout says "automatic zero" |

---

## Decisions needed before grading

Each is a gap or conflict between the 2026-10-19 guide and the current handout, or something
neither says. The bold choice is what this guide applies until the professor decides otherwise.

| # | Question | Options |
|---|---|---|
| D1 | Does "missing evidence → 0" now apply to Tasks 1 and 3 as well as Task 2? | **Yes, per dependent item**; or Task 2 only |
| D2 | Deliberate failure placed in `test_model.py` (fails in `BUILD`, package auto-rejected) instead of `pre_build`: full 8? | **Full 8 if `BUILD` failed, `POST_BUILD` shows the reject, and no `PendingManualApproval` was left** (meets "phase that owns tests"); or strict `PRE_BUILD` only, as the handout's Evidence column reads |
| D3 | `AFTER FAILED RUN` shows `OK` (snapshot taken late), but the action history shows the OK→ALARM transition with *Successfully executed action*, plus a valid email | **Full 6**; or −2 for not matching the Evidence column. The old guide accepted an older action line when the alarm was already red; the handout's `OK`-in-BEFORE requirement now rules that out |
| D4 | Students who tore down before the Oct 23 clarification and told the TA | **Grade against the pre-Oct-23 evidence set** (§0); or require the new files anyway |
| D5 | The −3 for a port that disagrees with Glue: what is the evidence? The handout never requires `docs/lab4-feature-equivalence.txt` | **Deduct only when a definition is visibly wrong in code or tests; don't deduct for the missing file**; or add the file to the handout |
| D6 | Size of deductions within 1.1 (−3 per category under 2 PASSED) and 2.1 (−3 for a missing mapping or rationale) | **As stated**; or professor's values |
| D7 | The post-cutoff leakage TODO is graded but not in the handout's Task 1 list | **Grade it as the 2026-10-19 guide says, but give at least half credit to a student who implemented only the handout's listed checks**; or full grading |
| D8 | Kit placeholder tests left vacuous: does the named boundary case count? | **No: the boundary case must be implemented by the student** |
| D9 | Regression test correct but `SKIPPED` in the final green log | **4/8**; or another value. The handout says SKIPPED doesn't count and requires PASSED |
| D10 | MLflow evidence with a non-MLflow-App URI, or truncated params | **2/4** |
| D11 | Lineage partial-credit ladder | **3 = all four fields + SHA in history; 2 = URI + SHA only; 1 = SHA only, or SHA not in history** |
| D12 | Cited paths missing at the tag | **−1 each, max −4** |

## Verified vs not verified

**Verified by reading (2026-10-28):** every [Handout] rule above against `Lab_4--XOps & CICD.md` at
`45a2677`; that the 2026-10-19 guide mentions none of the four new files or the required headings
(grep counts: 0); the kit's test counts (26 data, 18 features) and vacuous placeholders; the
`pipeline.yaml` alarm settings.

**Carried from the 2026-10-19 guide (verified on AWS by the instructor then):** the CodeConnections
source; install/pre_build/build/post_build; spot training + register; the in-training gate blocking
registration; the CodeBuild gate failing after registration with auto-reject; the live champion check
from CodeBuild; alarm OK → ALARM → OK with *Successfully executed action*; SNS delivery; ManualApproval.

**Not verified:** the alarm's automatic return to `OK` timing (D3; I'll measure it in my own run);
the exact CodeBuild log wording the grep commands match; the snippets above against a real
student submission.

## Also out of date: the student walkthrough

`Lab_4--Solution Notes.md` (verified 2026-10-19) predates the evidence rewrite too: its Phase 6 has no
`BEFORE` snapshot, `save_log`, `lab4-build-failed.log` or email screenshot; its 8.3 evidence table lists
6 files, not the 12 required (and includes `lab4-feature-equivalence.txt`, which the handout doesn't
require); and none of the four new files appear in it. It is distributed after the deadline, so it is
lower priority than this guide, but it should be updated before release.
