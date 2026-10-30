"""Your Lab 3 churn model, packaged for the Lab 4 pipeline.

YOU WRITE THIS FILE. The pipeline's training job runs train_sagemaker.py
(beside this file; do not edit it), which imports this module and calls
train(). Everything the job needs from you goes through the three names below.

Contract (train_sagemaker.py checks it in the first seconds of the job):

    FEATURE_COLUMNS   list[str]   model input columns, in order
    LABEL             str         "churn_label"
    train(df, seed=42) -> (xgboost.Booster, dict)

`df` is the full labeled feature table: every column of your Lab 2 output,
including `loyalty_tier` for slice evaluation. It is already loaded. Do not
query Athena or the Feature Store from here; the training container stages
the data for you and has no business making service calls for its input.

The metrics dict must include the four numbers the CI gate in
tests/test_model.py reads. Your Lab 3 evaluate_model() already returns them:

    precision_top10, recall_top10      gated at 0.50 / 0.25
    lift_ci_low, lift_ci_high          bootstrap 95% CI on AUC lift over the
                                       recency-only baseline; lift_ci_low > 0

Include anything else you reported in Lab 3 (auc_roc, baseline_auc,
positive_rate_val, slice results). It is all written to evaluation_metrics.json
and attached to the registered model.

What runs in the container: the SageMaker XGBoost 1.7-1 image ships pandas,
numpy, scikit-learn, xgboost and boto3. It does NOT ship mlflow or sagemaker,
so do not import them at the top of this file. MLflow tracking stays in your
Lab 3 script.

Only this directory (models/churn/) is uploaded to the training job, so the
code must live here. `import churn_training_skeleton` will fail inside the
container even though it works on your laptop. Copy the functions you need.

Test it locally before pushing:

    python models/churn/train_sagemaker.py \
        --train-channel <dir containing your features CSV or Parquet> \
        --model-dir /tmp/model --output-data-dir /tmp/out
"""

# Keeps Lab 3 annotations like `-> tuple[np.ndarray, np.ndarray]` from being
# evaluated, whatever Python the training container runs.
from __future__ import annotations

import json
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401
import xgboost as xgb  # noqa: F401
from datetime import datetime
from types import SimpleNamespace

from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

# Must match the columns your Lab 3 model was trained on, in the same order.
FEATURE_COLUMNS = [
    "days_since_last_purchase",
    "customer_tenure_days",
    "purchase_frequency_30d",
    "purchase_frequency_90d",
    "purchase_frequency_180d",
    "avg_order_value",
    "total_spend_90d",
    "total_lifetime_value",
    "avg_basket_size_6m",
    "category_diversity_score",
    "online_to_store_ratio",
]

LABEL = "churn_label"
BASELINE_COLUMN = "churn_risk_score"
BASELINE_FEATURE = "days_since_last_purchase"
SLICE_COLUMN = "loyalty_tier"

HYPERPARAMETERS = {"max_depth": 6, "eta": 0.1, "num_round": 200, "min_child_weight": 5,
                   "subsample": 0.8, "colsample_bytree": 0.8, "early_stopping_rounds": 20}

# ── Feature Preprocessing ──────────────────────────────────────────────────────

def preprocess_features(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """
    Clean and prepare features for XGBoost training.
    Returns (X, y) arrays.
    """
    print(f"Preprocessing {len(df):,} samples...")

    # Drop rows where label is missing
    df = df.dropna(subset=[LABEL])

    # TODO: Handle missing values in features
    # XGBoost can handle NaN natively, but document your imputation strategy.
    # For features with business-meaningful nulls (e.g., clickstream for non-web customers),
    # consider median imputation or a sentinel value.
    X = df[FEATURE_COLUMNS].fillna(-1).values  # Sentinel -1 for missing
    y = df[LABEL].values.astype(int)

    print(f"  Positive class rate: {y.mean():.1%}")
    print(f"  Feature matrix shape: {X.shape}")

    return X, y


# ── Model Training ─────────────────────────────────────────────────────────────

def train_model(X_train: np.ndarray,
                y_train: np.ndarray,
                X_val: np.ndarray,
                y_val: np.ndarray,
                args) -> xgb.Booster:
    """Train the XGBoost churn model."""

    dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=FEATURE_COLUMNS)
    dval = xgb.DMatrix(X_val, label=y_val, feature_names=FEATURE_COLUMNS)

    # Class imbalance, computed from the training split rather than hardcoded.
    # On the reference dataset this lands at 3.545.
    spw = (args.scale_pos_weight if args.scale_pos_weight is not None
           else float((y_train == 0).sum() / max((y_train == 1).sum(), 1)))

    # Record the RESOLVED value so track_run() can log what was actually used.
    # Logging args.scale_pos_weight instead would log None on every run that
    # let it compute itself -- which is most of them -- and your MLflow
    # comparison would be missing the one parameter most likely to explain a
    # precision/recall difference between runs.
    args.resolved_scale_pos_weight = spw

    params = {
        # eval_metric ORDER MATTERS. XGBoost early-stops on the LAST metric in
        # this list, not the first. This used to read ["auc", "logloss"], which
        # silently made logloss the early-stopping criterion: under
        # scale_pos_weight the reweighted logloss keeps improving long after
        # ranking quality peaks, so training ran the full 200 rounds instead of
        # stopping near round 31 and validation AUC came out 0.7603 instead of
        # 0.7822. Measured across 50 splits, that cost the model the promotion
        # gate on 28% of them -- a student doing everything right was told their
        # features did not beat recency. Keep "auc" last (defect 49).
        "objective": "binary:logistic",
        "eval_metric": ["logloss", "auc"],
        "max_depth": args.max_depth,
        "eta": args.eta,
        "min_child_weight": args.min_child_weight,
        "subsample": args.subsample,
        "colsample_bytree": args.colsample_bytree,
        "scale_pos_weight": spw,
        # More dormant must never mean less likely to churn: every split on
        # recency gives the higher-recency side a value >= the lower side, so
        # the score is non-decreasing in recency with all else fixed. Without
        # it the 3.2 model dipped 0.054 from 60 to 90 days and failed
        # test_model_monotone_on_recency. 1 = increasing, 0 = unconstrained,
        # positional, so build it from FEATURE_COLUMNS.
        "monotone_constraints": "(" + ",".join(
            "1" if c == "days_since_last_purchase" else "0" for c in FEATURE_COLUMNS) + ")",
        "seed": 42,
        "verbosity": 1,
    }

    print(f"\nTraining XGBoost with params: {json.dumps(params, indent=2)}")

    model = xgb.train(
        params=params,
        dtrain=dtrain,
        num_boost_round=args.num_round,
        evals=[(dtrain, "train"), (dval, "validation")],
        early_stopping_rounds=20,
        verbose_eval=25,
    )

    return model


# ── Evaluation ─────────────────────────────────────────────────────────────────

EVAL_THRESHOLDS = {
    "precision_top10":   0.50,   # Minimum precision @ top 10% scored customers
    "recall_top10":      0.25,   # Minimum recall @ top 10% scored customers
    # Note the recall ceiling: with ~22% positives, targeting the top 10% of
    # customers caps achievable recall near 0.45. Hitting 0.25 means capturing
    # roughly half of what is reachable within that contact budget.
}

# There is deliberately NO absolute AUC threshold. One used to live here
# (auc_roc >= 0.72) and it was removed on 2026-08-02: measured across 200
# random train/test splits of the same data, the reference model fell below
# 0.72 on 58% of them. A gate the reference clears by luck of the shuffle
# grades your random seed, not your model. Report AUC; do not gate on it.
#
# The baseline gate is an INTERVAL, not a threshold: the 95% CI on
# (your AUC - recency-only baseline AUC) must exclude zero.
# BASELINE_FEATURE is defined once, near FEATURE_COLUMNS above.
BOOTSTRAP_N = 2000
BOOTSTRAP_SEED = 42


def train_recency_baseline(X_train: np.ndarray,
                           y_train: np.ndarray,
                           X_val: np.ndarray) -> np.ndarray:
    """Train the recency-only baseline and score the validation split.

    The baseline is a model over `days_since_last_purchase` ALONE, trained on
    the same training rows and scored on the same validation rows as the full
    model. That is what makes the comparison fair.

    It is deliberately NOT a constant predictor. A constant prediction has an
    AUC of exactly 0.5 by construction, so "beating" it proves only that your
    model is better than a coin flip. The question Lab 3 asks is whether your
    feature engineering beats the rule the business already has for free:
    "contact whoever has not purchased in a while."
    """
    i = FEATURE_COLUMNS.index(BASELINE_FEATURE)
    dtr = xgb.DMatrix(X_train[:, [i]], label=y_train, feature_names=[BASELINE_FEATURE])
    dva = xgb.DMatrix(X_val[:, [i]], feature_names=[BASELINE_FEATURE])
    spw = float((y_train == 0).sum() / max((y_train == 1).sum(), 1))
    params = {
        "objective": "binary:logistic", "eval_metric": "auc",
        "max_depth": 4, "eta": 0.1, "subsample": 0.9,
        "colsample_bytree": 0.9, "scale_pos_weight": spw, "seed": 42,
    }
    return xgb.train(params, dtr, num_boost_round=200).predict(dva)



def bootstrap_lift_ci(y_true: np.ndarray,
                      proba: np.ndarray,
                      baseline_proba: np.ndarray,
                      n: int = BOOTSTRAP_N,
                      seed: int = BOOTSTRAP_SEED,
                      alpha: float = 0.05) -> tuple[float, float]:
    """Percentile CI for (model AUC - baseline AUC), by resampling the val set.

    PAIRED: each replicate resamples row indices once and scores BOTH models on
    those same rows, so the interval is on the difference and the correlation
    between the two models is preserved. Resampling them independently breaks
    the pairing and inflates the interval, which would make a real improvement
    look inconclusive.

    Replicates whose resample happens to be single-class are skipped, because
    AUC is undefined there.

    The seed is fixed so the gate is reproducible: the same split must always
    produce the same verdict.
    """
    rng = np.random.default_rng(seed)
    y_true = np.asarray(y_true)
    idx = np.arange(len(y_true))
    diffs = []
    for _ in range(n):
        s = rng.choice(idx, size=len(idx), replace=True)
        ys = y_true[s]
        if len(np.unique(ys)) < 2:
            continue
        diffs.append(roc_auc_score(ys, proba[s]) - roc_auc_score(ys, baseline_proba[s]))
    if len(diffs) < n // 2:
        raise ValueError(
            "Too few usable bootstrap replicates to form a confidence interval. "
            "Your validation set is too small or too imbalanced to support this gate."
        )
    d = np.sort(diffs)
    return float(np.quantile(d, alpha / 2)), float(np.quantile(d, 1 - alpha / 2))


def evaluate_model(model: xgb.Booster,
                   X_val: np.ndarray,
                   y_val: np.ndarray,
                   baseline_proba: np.ndarray) -> dict:
    """
    Evaluate the trained model against required thresholds.
    Returns a metrics dict. Raises ValueError if thresholds are not met.
    """
    dval = xgb.DMatrix(X_val, feature_names=FEATURE_COLUMNS)
    y_pred_proba = model.predict(dval)
    y_pred_binary = (y_pred_proba > 0.5).astype(int)

    auc_roc = roc_auc_score(y_val, y_pred_proba)

    # Precision and recall @ top 10%
    top10_threshold = np.percentile(y_pred_proba, 90)
    top10_mask = y_pred_proba >= top10_threshold
    precision_top10 = y_val[top10_mask].mean() if top10_mask.sum() > 0 else 0.0
    recall_top10 = y_val[top10_mask].sum() / y_val.sum() if y_val.sum() > 0 else 0.0

    # Baseline: a model trained on days_since_last_purchase ALONE.
    #
    # This used to be `np.full_like(y_pred_proba, y_val.mean())` - a constant
    # prediction, whose AUC is exactly 0.5 by definition. Beating a coin flip
    # is not evidence that your feature engineering did anything, and it is not
    # what Lab 3 asks for. The comparison that matters is against recency,
    # because recency is the rule the business already has for free.
    #
    baseline_auc = roc_auc_score(y_val, baseline_proba)
    auc_vs_baseline = auc_roc - baseline_auc

    lift_ci_low, lift_ci_high = bootstrap_lift_ci(
        y_val, y_pred_proba, baseline_proba)

    metrics = {
        "auc_roc": round(float(auc_roc), 4),
        "precision_top10": round(float(precision_top10), 4),
        "recall_top10": round(float(recall_top10), 4),
        "auc_vs_baseline": round(float(auc_vs_baseline), 4),
        "baseline_auc": round(float(baseline_auc), 4),
        "lift_ci_low": round(float(lift_ci_low), 4),
        "lift_ci_high": round(float(lift_ci_high), 4),
        "positive_rate_val": round(float(y_val.mean()), 4),
        "n_val_samples": int(len(y_val)),
        "eval_timestamp": datetime.utcnow().isoformat(),
    }

    print("\n── Evaluation Results ──────────────────────────────")
    failures = []
    for metric, threshold in EVAL_THRESHOLDS.items():
        value = metrics[metric]
        status = "✓ PASS" if value >= threshold else "✗ FAIL"
        print(f"  {metric:25s}: {value:.4f}  (threshold: {threshold:.4f})  {status}")
        if value < threshold:
            failures.append(f"{metric}={value:.4f} < {threshold}")

    # The baseline gate: the interval must exclude zero.
    ci_status = "\u2713 PASS" if lift_ci_low > 0 else "\u2717 FAIL"
    print(f"  {'auc_lift 95% CI':25s}: [{lift_ci_low:.4f}, {lift_ci_high:.4f}]"
          f"  (must exclude 0)  {ci_status}")
    if lift_ci_low <= 0:
        failures.append(
            f"auc_lift 95% CI [{lift_ci_low:.4f}, {lift_ci_high:.4f}] includes "
            f"zero - no evidence the model beats the recency-only baseline")

    if failures:
        raise ValueError(
            f"Model failed evaluation thresholds: {'; '.join(failures)}. "
            f"Do not promote to Model Registry."
        )

    print("  All thresholds passed ✓")

    return metrics


# ── Slice Evaluation ───────────────────────────────────────────────────────────

def evaluate_slices(model, X_val, y_val, tiers, min_class_count=20,
                    n_boot=1000, seed=42) -> dict:
    """Per-tier AUC and recall@10%, with n, positives, and an AUC interval.

    Uses the GLOBAL top-10% cutoff: the retention team contacts the top 10% of
    all customers, not the top 10% within each tier, so recall per tier is
    'of this tier's churners, how many made the global contact list'.
    """
    proba = model.predict(xgb.DMatrix(X_val, feature_names=FEATURE_COLUMNS))
    cutoff = np.percentile(proba, 90)
    contacted = proba >= cutoff
    agg_recall = contacted[y_val == 1].mean()
    agg_auc = roc_auc_score(y_val, proba)

    rng = np.random.default_rng(seed)
    tiers = np.asarray(tiers)
    results = {}
    print(f"\n── Slice evaluation (aggregate AUC {agg_auc:.4f}, recall@10% {agg_recall:.4f}) ──")
    print(f"  {'tier':10s} {'n':>5s} {'pos':>4s} {'churn':>6s} {'AUC':>7s} {'95% CI':>17s} {'rec@10':>7s}  note")

    for tier in ["Bronze", "Silver", "Gold", "Platinum"]:
        m = tiers == tier
        y_t, p_t, c_t = y_val[m], proba[m], contacted[m]
        n, pos = int(m.sum()), int(y_t.sum())
        neg = n - pos
        if n == 0:
            continue

        auc_t = roc_auc_score(y_t, p_t) if pos and neg else float("nan")
        rec_t = c_t[y_t == 1].mean() if pos else float("nan")

        # Bootstrap the slice AUC so its width - not just its point value - is visible.
        boots = []
        for _ in range(n_boot):
            s = rng.integers(0, n, n)
            if 0 < y_t[s].sum() < n:
                boots.append(roc_auc_score(y_t[s], p_t[s]))
        lo, hi = (np.percentile(boots, [2.5, 97.5]) if boots else (np.nan, np.nan))

        reliable = pos >= min_class_count and neg >= min_class_count
        weak_recall = reliable and rec_t < agg_recall - 0.10
        note = ("TOO SMALL - no conclusion" if not reliable
                else "recall >10pp below aggregate" if weak_recall else "")

        results[tier] = {"n": n, "positives": pos, "churn_rate": round(pos / n, 4),
                         "auc": round(float(auc_t), 4), "auc_ci_low": round(float(lo), 4),
                         "auc_ci_high": round(float(hi), 4), "recall_top10": round(float(rec_t), 4),
                         "reliable": reliable, "flag_weak_recall": bool(weak_recall)}
        print(f"  {tier:10s} {n:5d} {pos:4d} {pos/n:6.1%} {auc_t:7.4f} "
              f"[{lo:.3f}, {hi:.3f}] {rec_t:7.4f}  {note}")

    reliable_tiers = {t: r for t, r in results.items() if r["reliable"]}
    if reliable_tiers:
        worst = min(reliable_tiers, key=lambda t: reliable_tiers[t]["auc"])
        print(f"  Weakest reliable tier by AUC: {worst}")
        results["_worst_tier"] = worst
    return results


def train(df: pd.DataFrame, seed: int = 42):
    """Train the churn model on `df` and return (booster, metrics).

    TODO (Lab 4): implement this from your Lab 3 code. The usual shape:

      1. X, y from FEATURE_COLUMNS and LABEL (handle missing values the way
         your Lab 3 preprocess_features() did)
      2. train_test_split(..., test_size=0.30, random_state=seed, stratify=y)
         -- carry the tier through the same call if you report slices. Pass
         df["loyalty_tier"] (a Series) or .to_numpy(dtype=object); NOT
         .values, which under pandas 3 is an Arrow array that
         train_test_split cannot index
      3. train the XGBoost model (your Lab 3 train_model())
      4. train the recency-only baseline (train_recency_baseline())
      5. metrics = evaluate_model(...)   # keep Lab 3's raise on a failed gate:
                                         # it fails the training step, so a
                                         # model that misses a gate is never
                                         # registered
      6. return model, metrics

    Return an xgboost.Booster (what xgb.train() gives you). If you used
    XGBClassifier, return clf.get_booster().
    """
    hp = dict(HYPERPARAMETERS)
    X, y = preprocess_features(df)
    tiers = df.dropna(subset=[LABEL])["loyalty_tier"].to_numpy(dtype=object)

    X_train, X_val, y_train, y_val, _, tier_val = train_test_split(
        X, y, tiers, test_size=0.30, random_state=seed, stratify=y)

    # Lab 3's train_model reads argparse-style attributes; there is no command
    # line in the container, so build the same shape from HYPERPARAMETERS.
    # scale_pos_weight=None lets it compute the class weight from the split.
    args = SimpleNamespace(**hp, scale_pos_weight=None)
    model = train_model(X_train, y_train, X_val, y_val, args)
    baseline_proba = train_recency_baseline(X_train, y_train, X_val)
    metrics = evaluate_model(model, X_val, y_val, baseline_proba)   # RAISES on a failed gate

    slices = evaluate_slices(model, X_val, y_val, tier_val)
    metrics["slice_results"] = {k: v for k, v in slices.items() if not k.startswith("_")}
    metrics["slice_worst_tier"] = slices.get("_worst_tier")
    metrics["best_iteration"] = int(model.best_iteration)
    metrics["hyperparameters"] = hp
    metrics["xgboost_version"] = xgb.__version__
    return model, metrics
