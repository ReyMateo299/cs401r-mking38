# Lab 4 student tips and troubleshooting guide

A practical companion to the Lab 4 handout and starter kit. The handout is the
grading authority; these tips cover the places where students most often get
stuck or lose points without realizing it.

## Quick route: where should I start?

| If your question is… | Go to… |
|---|---|
| "What do I actually have to write?" | [What you write vs. what ships](#what-you-write-vs-what-ships) |
| "`test_features.py` fails with `Could not import data.feature_engineering`." | [Write `data/feature_engineering.py` first](#write-datafeature_engineeringpy-first) |
| "Which TODOs in `test_data.py` matter?" | [Finish the data tests](#finish-the-data-tests) |
| "How does the regression test find the champion?" | [The champion regression test](#the-champion-regression-test) |
| "How do I turn my Lab 3 script into `train()`?" | [Port Lab 3 into `churn_model.py`](#port-lab-3-into-churn_modelpy) |
| "The build says `ExecuteUserScriptError` and nothing else." | [Debugging a failed run](#debugging-a-failed-run) |
| "How do I run the failure demo without wrecking the evidence?" | [The failure demo](#the-failure-demo) |
| "What do I capture, and when do I tear down?" | [Evidence and teardown](#evidence-and-teardown) |

## What you write vs. what ships

Copy the kit into your existing `cs401r-<netid>` repo; don't start a new repo.
Then:

| You write | Ships complete; don't edit |
|---|---|
| `data/feature_engineering.py` (not in the kit, and the handout barely mentions it) | `buildspec.yml`, `pipeline.yaml`, `requirements.txt`, `pytest.ini`, `tests/conftest.py` |
| `train()` in `models/churn/churn_model.py` | `models/churn/train_sagemaker.py`, `models/churn/pipeline_definition.py` |
| The TODOs in `tests/test_data.py` and `tests/test_features.py`, plus your own edge-case tests | |
| The champion regression test in `tests/test_model.py` (no stub ships) | |
| `tests/test_fairness.py` (new file) | |
| The `iam:PassRole` statement in `infrastructure/modules/iam/main.tf` | |
| `docs/lab4-xops-assessment.md` and every evidence file | |

After copying, **delete the downloaded template folder** if you unzipped or
cloned it inside your repo. Otherwise `git add -A` commits a second copy of
the kit.

## Write `data/feature_engineering.py` first

`test_features.py` imports these five functions, and `pre_build` fails on every
push until they exist:

```python
compute_recency_features(transactions, as_of, customer_ids=None, sentinel=999.0)
compute_frequency_features(transactions, as_of, customer_ids=None)
compute_monetary_features(transactions, as_of, customer_ids=None)
compute_behavioral_features(transactions, as_of=FEATURE_CUTOFF, customer_ids=None)
build_churn_feature_set(customers, transactions, snapshot_date)
```

- **The walkthrough's code block is partial.** It shows the helpers plus the
  monetary and behavioral functions. You still write `_ids()`, recency,
  frequency and `build_churn_feature_set`, and you add `import numpy as np`.
  Replace the empty stubs; don't paste the block underneath them.
- **Copy your Glue job's definitions exactly.** Windows are
  `purchase_date > T − N days` (strictly after), history is
  `purchase_date <= T`, and `T = 2026-04-01`. `avg_basket_size_6m` is
  **items per order** over 180 days, not dollars.
- **Filter to `purchase_date <= T` inside every function.** Your leakage test
  will pass the whole processed table, holdout included.
- **`customer_ids` arrives in more than one shape.** The kit's sentinel test
  passes a one-column DataFrame; a leakage test usually passes a Series.
  Accept both.
- **A customer with no purchases gets a complete row:** recency 999, tenure 0,
  every count and spend 0, no NaN.
- **Prove it matches Glue.** Run your port on the downloaded processed data,
  compare it column by column with the Glue features, and save the max
  differences (for example, `docs/lab4-feature-equivalence.txt`). The handout
  doesn't list this file, but "how do you know the two agree?" is a fair
  grading question. Differences of 0.0001 in a few rows are just rounding:
  Spark rounds half up, pandas rounds half to even.

While you're still building it, `ALLOW_MISSING_FEATURES_MODULE=1` lets other
tests run. Never push with it set.

## Finish the data tests

`test_data.py` has two TODOs, and both are graded:

1. **Leakage, post-cutoff.** The shipped
   `test_label_not_trivially_separable` already covers the handout's leakage
   bullet. The TODO is a second test. **Don't** assert "no purchase after
   2026-04-01": `processed/` contains the holdout purchases (they make the
   label), so that test fails on correct data. Instead, recompute recency,
   tenure and the 30/90/180-day frequencies from rows `<= 2026-04-01` with
   your `feature_engineering` functions, and assert they equal what Glue wrote.
2. **Freshness.** `event_time` is epoch seconds for when the Glue job *ran*,
   not the cutoff date. Fail if it's more than 48 hours old.

The freshness test means **every session that pushes starts with**
`aws glue start-job-run --job-name northstar-dev-feature-engineer` (about 90 s).
That applies to the failure demo and the revert too.

Two placeholder tests in `test_features.py` pass while doing nothing (the
zero-purchase sentinel test and the null-count test). Fill them in; the TA
reads the bodies, not just the PASSED lines. The kit's 18 tests are almost all
"normal" cases. The handout defines the other two, and the kit ships neither
as a working test:

- **Boundary:** a customer with 0 purchases. The sentinel placeholder becomes
  this test once you uncomment it.
- **Edge:** a customer with a single transaction. Nothing in the kit covers
  it, so write it yourself. With one purchase, recency equals tenure and
  `avg_order_value` equals `total_lifetime_value`.

Window tests are worth adding on top: a purchase dated on T, and one exactly
90 days before T, which is in the 180-day window but not the 90-day one. They
catch the `>` vs `>=` mistake.

Keep downloaded data out of git. If you stage it under `./data/`, add
`data/*.csv`, `data/processed/`, `data/features/` and `reports/` to
`.gitignore` (but not `data/` itself, since `feature_engineering.py` lives there).

## The champion regression test

- **The champion is the newest `Approved` package, not the newest package.**
  The candidate is already registered as `PendingManualApproval` when the test
  runs, so "newest" compares the model with itself.
- **The champion's AUC isn't on the package.** A pipeline-registered package's
  `ModelMetrics` points at an S3 `evaluation_metrics.json`. Follow that
  `S3Uri` and read `auc_roc`. The solution walkthrough has the lookup; the
  CodeBuild role can already list and describe packages and read S3.
- **Your metrics dict must include `auc_roc`**, even though the contract
  lists only four required keys.
- **No `Approved` package yet is a legitimate skip. A registry or credentials
  error is a failure, not a skip.**
- Call `warnings.warn(f"champion v{version} auc=…; candidate auc=…")` before
  asserting, so the log shows what you compared against.
- A hardcoded champion AUC loses most of the 8 points.

## Port Lab 3 into `churn_model.py`

- **Copy the functions in; don't import your Lab 3 script.** Only
  `models/churn/` is uploaded to the training container.
- **No `mlflow`, `sagemaker` or `boto3` imports at the top.** The XGBoost 1.7
  container lacks the first two.
- **Lab 3's `train_model()` probably takes an argparse `args`.** In `train()`
  there's no command line, so build a hyperparameter dict (or a
  `types.SimpleNamespace`) instead.
- **Keep `evaluate_model()` raising on a failed gate.** That failure is what
  stops a bad model from being registered.
- **Pass tiers through the same `train_test_split` call**, as
  `df["loyalty_tier"].to_numpy(dtype=object)`, not `.values` (pandas 3 breaks it).
- **Put per-tier results into the metrics dict** so `test_fairness.py` can read
  them. Make them plain Python types (`float()`, `int()`, `bool()`):
  `json.dump` can't serialize `numpy.int64` or `numpy.bool_`.
- **Run the handout's local test before every push that changes this file.**
  Expect slightly different numbers in the container (XGBoost 1.7 vs your 3.x).

## Debugging a failed run

| Symptom | Likely cause |
|---|---|
| `PRE_BUILD` fails on `test_features_are_fresh` | The feature job last ran more than 48 h ago: re-run it, then push again |
| `PRE_BUILD` fails on `Could not import data.feature_engineering` | Module missing, or it raises on import (the message shows the real exception) |
| `AlgorithmError: ExecuteUserScriptError` and nothing else | Your `train()` raised in the container: read `/aws/sagemaker/TrainingJobs` in CloudWatch Logs |
| `not authorized to perform: iam:PassRole` ~30 s into the SageMaker Pipeline | Prerequisite 4 not applied (`terraform apply`) |
| `The policy failed legacy parsing` creating the stack | zsh ate `$VAR:role`: write `${VAR}` before a colon, or use the terraform-output form |
| Build red and a new package shows `Rejected` | Expected: `post_build` rejects a package from a build that failed after registering |
| Source stage fails | Wrong `GitHubRepo`, or the GitHub app wasn't granted that repo |

**Every push to `main` runs the whole pipeline**, including a training job,
even for a docs-only commit. Batch your commits.

## The failure demo

1. **Start with the alarm in `OK`** and the email subscription **confirmed**
   (`list-subscriptions-by-topic` shows an ARN, not `PendingConfirmation`).
2. Re-run the feature job, `snap "BEFORE"`, then push the deliberately failing test.
3. **Run `snap "AFTER FAILED RUN"` as soon as the alarm reads `ALARM`.** From
   the alarm's settings (a 5-minute period, with no data counting as not
   breaching), it should return to `OK` by itself about five minutes later,
   whether or not you've reverted. If you're late, the snapshot shows `OK`.
   *(Inferred from the template; I'll confirm this on my own run.)*
4. Save the failed build's log with `save_log`, and screenshot the email whose
   subject starts **`ALARM:`**, with its received time. You'll also get an
   `OK:` email later; that's not the one to submit.
5. Revert (keep both commits in history), wait for green, then `snap "AFTER REVERT"`.

## Evidence and teardown

- **Approve one green run first** so the final green run's regression test
  `PASSED` instead of skipping.
- **Run the capture block while the stack is up**, then open every file. An
  empty `lab4-build-green.log` usually means the wrong build ID.
- **Capture `lab4-model-registry.json` before setting your champion to
  `Rejected`.** The rubric needs to see it `Approved`.
- **Delete the CI stack before your final docs commit**, or that push trains
  once more.
- Re-define `AB=northstar-dev-cicd-artifacts-<account>` before teardown; your
  old shell variable is probably gone. Also delete the CodeBuild report group
  `northstar-ci-northstar-test-reports`.
- **Thinking about Lab 5?** Lab 5 deploys a model package whose artifact
  lives in your data bucket. `teardown-lab2.sh` deletes that bucket, so you'd
  have to re-run Lab 2 and one pipeline run to get a deployable model back.
  You still shouldn't leave the NAT Gateway running between sessions.
- Tag the commit (`git tag lab4-submit && git push origin lab4-submit`). If
  you forget, you're graded at your last commit before the deadline.
