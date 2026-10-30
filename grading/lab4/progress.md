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
| 2 | `test_data.py` TODOs (post-cutoff leakage, freshness); `test_features.py` TODOs + edge cases; champion regression test; `tests/test_fairness.py` | in progress | `test_features.py` done 2026-10-30: both placeholders filled, 6 boundary/edge tests added (24 tests; not yet run). Remaining: `test_data.py` TODOs, champion regression test, `test_fairness.py` |
| 3 | `churn_model.train()` from `models/churn/train.py`; local `train_sagemaker.py` + `pytest tests/test_model.py` | todo | Lab 3 `train_model()` takes argparse `args`; adapt |
| 4 | `PassSelfToSageMaker` statement in `infrastructure/modules/iam/main.tf` | todo | `AddTags`/`ListTags` already present (verified) |
| 5 | Artifacts bucket, GitHub connection `AVAILABLE`, deploy `northstar-cicd`, subscribe + confirm email | todo | |
| 6 | Green run → approve champion | todo | |
| 7 | Failure demo: BEFORE / AFTER FAILED RUN / AFTER REVERT, failed log, ALARM email png | todo | Record the ALARM→OK interval (instruction note 5) |
| 8 | Lineage metadata on final package; `lab4-model-package.json`; MLflow ≥ 3 runs → `lab4-mlflow-runs.txt` | todo | |
| 9 | `docs/lab4-xops-assessment.md` (5 headings) | todo | |
| 10 | Capture block → delete stack → commit docs → tag `lab4-submit` → teardown | todo | Capture registry JSON before rejecting the champion |

## Open verification items for instruction_notes.md

- Note 5: does the alarm really return to `OK` ~5 min after a failure without a green build?
- Does the CodeBuild role's `ListModelPackages` grant work for the regression test? (The grading guide says yes, verified in run 5.)
