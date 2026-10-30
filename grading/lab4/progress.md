# My Lab 4 progress (TA run-through)

Due Sat Oct 31, midnight. Started 2026-10-28.

Order follows the solution notes' phases. Commands that touch AWS are run by
me (Matt), not by the assistant.

| # | Step | Status | Evidence / notes |
|---|---|---|---|
| 0a | Copy kit into repo (additive) | done 2026-10-28 | No path collisions. `.gitignore` gained `data/*.csv`, `data/processed/`, `data/features/`, `reports/` |
| 0b | Delete or move `cs401r-lab4-template-main/` out of the repo before any `git add -A` | todo | Duplicate of the kit |
| 0c | Pre-flight: Lab 2 up, feature job < 48 h, spot quota ≥ 1, Python 3.11 venv | todo | |
| 1 | `data/feature_engineering.py` (pandas port of Glue) + equivalence check | done 2026-10-29 | 18/18 kit tests pass locally (py3.11). `scripts/lab4_feature_equivalence.py` → `docs/lab4-feature-equivalence.txt`: 9,999/9,999 customers, all within 0.0001 (332 rows `avg_order_value`, 15 `online_to_store_ratio`: rounding, Spark HALF_UP) |
| 2 | `test_data.py` TODOs (post-cutoff leakage, freshness); `test_features.py` TODOs + edge cases; champion regression test; `tests/test_fairness.py` | code complete 2026-10-30, not yet run | `test_features.py` 24 tests; `test_model.py` +3 regression tests (21); `test_fairness.py` 5 logic + 1 model test; `test_data.py` leakage + freshness TODOs done (Matt). Next: run `pytest tests/` locally. Phase 3 must put `slice_results` and `auc_roc` in the metrics |
| 3 | `churn_model.train()` from `models/churn/train.py`; local `train_sagemaker.py` + `pytest tests/test_model.py` | in progress | Lab 3 `train_model()` takes argparse `args`. `train()` done with SimpleNamespace adapter; monotone constraint on recency added 2026-10-30 (see Decisions). Local 3.11: gates pass, 26 passed / 1 skipped. Done locally; container numbers pending first green build |
| 4 | `PassSelfToSageMaker` statement in `infrastructure/modules/iam/main.tf` | done 2026-10-30 | Statement in MLEngineer policy, `terraform validate` ok; applied (first pipeline run passed TrainChurnModel with no PassRole error) |
| 5 | Artifacts bucket, GitHub connection `AVAILABLE`, deploy `northstar-cicd`, subscribe + confirm email | done 2026-10-30 | Bucket versioning Enabled; `northstar-github` AVAILABLE; stack CREATE_COMPLETE; mattking29910@gmail.com confirmed (mking38@byu.edu left PendingConfirmation, expires ~2026-11-02, so it may show in snapshots); alarm OK |
| 6 | Green run → approve champion | done 2026-10-30 | Build `northstar-ci:aa043c70-b106-4603-a354-c49ddeac06b9` on `6fd9275` SUCCEEDED; 28 + 24 pre_build tests passed. **Champion = v5, Approved**; pipeline approval Succeeded. v3/v4 (Oct 10/13, Lab 3) still PendingManualApproval and ignored. Keep v5 Approved until after the 8.3 capture |
| 7 | Failure demo: BEFORE / AFTER FAILED RUN / AFTER REVERT, failed log, ALARM email png | done 2026-10-30 | BEFORE 09:53:30Z (v5 newest, alarm OK). Failing commit `9dc1489` → build `63485599-2b2a-472a-8411-31dbff11421c` FAILED in PRE_BUILD (1 failed, 27 passed), no BUILD phase; packages unchanged; ALARM 10:12:47Z, 56 s after the build failed (10:11:51Z). Push did not trigger the pipeline (instruction note 16), so runs were started with `start-pipeline-execution`. `docs/lab4-build-failed.log` saved. A second manual start also ran `9dc1489` (build #3 `95222c89-358c-4721-86ab-97a978f763b5`, FAILED PRE_BUILD; no package). Revert `8a3c5bc` was **push-triggered (Webhook)** → **final green build #4 `northstar-ci:71a0869a-8e86-4b6b-9df3-8ecc666ff782`** SUCCEEDED (5m17s). Its package is left PendingManualApproval; v5 stays champion. ALARM email png saved. AFTER REVERT 10:27:07Z: build #4 SUCCEEDED, v6 Pending above v5 Approved, alarm OK at 10:26:47Z. Use this build ID explicitly for `save_log` in 8.3 |
| 8 | Lineage metadata on final package; `lab4-model-package.json`; MLflow ≥ 3 runs → `lab4-mlflow-runs.txt` | done 2026-10-30 | 7.1 + 7.2 written in `docs/lab4-xops-assessment.md`. 7.3 done 2026-10-30: `scripts/lab4_mlflow_runs.py` → `docs/lab4-mlflow-runs.txt`, MLflow App `app-X2C7AC6JJGBL`, experiment `northstar-churn-lab4`, 4 runs, all gates passed. The pipeline row reproduces local `train_sagemaker.py` exactly (AUC 0.7777, best iteration 25) after switching to `read_channel()`; row order sets the split. d8-eta0.3 lift CI low 0.0023, a near-fail. 7.4 done: `scripts/lab4_lineage.py 6` → v6 CustomerMetadataProperties (commit `8a3c5bc3`, data `s3://…/features/customers/` last modified 2026-10-29T18:16:36Z, sha256 `f1de72a5…`, job `pipelines-q727bwr8b950-TrainChurnModel-byugwWq8WE`, AUC 0.7855); `docs/lab4-model-package.json` saved |
| 9 | `docs/lab4-xops-assessment.md` (5 headings) | done 2026-10-30 | All five sections written; maturity sections ~450 words; cites `docs/lab4-build-green.log` and `docs/lab4-pipeline-runs.txt`, which the 8.3 capture creates |
| 10 | Capture block → delete stack → commit docs → tag `lab4-submit` → teardown | todo | Capture registry JSON before rejecting the champion |

## Open verification items for instruction_notes.md

- Note 5: does the alarm really return to `OK` ~5 min after a failure without a green build? ALARM came 56 s after the failed build (10:11:51Z → 10:12:47Z). Returned to `OK` at 10:26:47Z, about 1 min after green build #4 finished. The extra failed build #3 (~10:19Z) kept it in `ALARM` until then, so I couldn't observe an unaided ALARM→OK.
- Does the CodeBuild role's `ListModelPackages` grant work for the regression test? **Yes, verified 2026-10-30.** In final green build `71a0869a`, `test_candidate_not_worse_than_champion` PASSED with `champion v5 auc=0.7855; candidate auc=0.7855`. Model gate: 27 passed, 0 skipped. FAIRNESS FLAG 35.1% Bronze vs Platinum.

## Decisions and deviations from the walkthrough

### 2026-10-30: monotone constraint on recency in `train_model`

- **Problem.** The local 3.11 run (xgboost 3.2.0) reproduced the walkthrough's
  numbers exactly: AUC 0.7796, lift CI low 0.0366, best iteration 36. But
  `test_model_monotone_on_recency` failed with `[(60, 90, 0.054)]`; scores
  were 0.238, 0.403, 0.450, 0.396, 0.724, 0.849. The walkthrough's only
  monotonicity fix, the tolerant 0.02 test, is already in my kit; this dip is
  beyond it. Instruction note 15 has the details.
- **Change.** `models/churn/churn_model.py`, in `train_model()` params:
  `monotone_constraints` = 1 on `days_since_last_purchase` and 0 on the other
  ten features. It's built from `FEATURE_COLUMNS`, so the order can't drift.
  The kit's test is unchanged.
- **Why this option.** Every split on recency must give higher recency a
  value ≥ lower recency, so the score can't fall as dormancy grows. That holds
  in every XGBoost version, including the container's 1.7, and CI tests the
  container's model, not my local one. I rejected two alternatives: making the
  test's probe customer realistic (it fixes the test, not the model) and
  raising the tolerance (it accepts the dip).
- **Cost to check.** The model is less flexible on recency. I have to retrain
  on 3.11 and confirm that the lift CI low stays > 0 (was 0.0366) and P@10 stays
  ≥ 0.50 (was 0.7067). Record the new numbers here.
  - **Result (local, 3.11 / xgboost 3.2.0, 2026-10-30): all gates pass.**

    | Metric | Before | After constraint |
    |---|---|---|
    | AUC | 0.7796 | 0.7777 |
    | Baseline AUC | 0.7233 | 0.7233 |
    | Lift 95% CI | [0.0366, —] | [0.0348, 0.0732] |
    | P@10 / R@10 | 0.7067 / 0.3212 (walkthrough ref) | 0.7033 / 0.3197 |
    | Best iteration | 36 | 25 |
    | `test_model.py` + `test_fairness.py` | monotonicity FAILED | **26 passed, 1 skipped** (no Approved package yet) |

    The constraint cost 0.0019 AUC and 0.0018 of lift-CI margin, so the lift
    CI still clears 0 comfortably. Slices: Bronze rec@10 0.4432, Silver
    0.1770, Gold 0.1538, Platinum 0.1429 (21 positives, so just reliable).
    The fairness flag now reads Bronze vs Platinum, about 30.0 pp.
    **Container result (first green build, v5, 2026-10-30):** AUC 0.7855,
    lift CI [0.0455, 0.0839], P@10 0.7167, R@10 0.3258. Tier rec@10: Bronze
    0.446, Silver 0.1947, Gold 0.1538, Platinum 0.0952. The model gate passed
    with the constraint in place; I reviewed the log and it looked right. The
    container beat the local run (AUC 0.7777) and is close to the walkthrough's
    container reference (0.7823). Champion warning for later runs:
    `champion v5 auc=0.7855`.
- **For Phase 8.** Mention this in `docs/lab4-xops-assessment.md` as a deliberate
  behavioural constraint encoding the business rule, not a workaround.
- Note 16 (push trigger): **confirmed.** Pushes did not trigger until the GitHub App was installed. After installing it, the revert push `8a3c5bc` triggered execution type `Webhook` with no `pipeline.yaml` change. The install created a second connection (`023577e6…`), which is unused; the pipeline still uses `e9ffcd2a…`. Delete the spare at teardown.
