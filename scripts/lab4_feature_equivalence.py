"""Lab 4: prove data/feature_engineering.py agrees with the Glue feature job.

Runs the pandas port on the processed transactions and compares every column
with what Glue wrote to features/. Local only; download the data first
(solution notes, Phase 0):

    python scripts/lab4_feature_equivalence.py /tmp/lab4data > docs/lab4-feature-equivalence.txt
"""

import glob
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from data.feature_engineering import FEATURE_CUTOFF, build_churn_feature_set  # noqa: E402

NUMERIC = ["days_since_last_purchase", "customer_tenure_days",
           "purchase_frequency_30d", "purchase_frequency_90d", "purchase_frequency_180d",
           "avg_order_value", "total_spend_90d", "total_lifetime_value",
           "avg_basket_size_6m", "category_diversity_score", "online_to_store_ratio",
           "churn_risk_score", "churn_label"]
TOL = 1e-4   # Spark rounds HALF_UP, pandas rounds half to even


def read_dir(path):
    files = [f for f in glob.glob(f"{path}/**/*.parquet", recursive=True)
             if "_glue_temp" not in f]
    if not files:
        raise SystemExit(f"no Parquet files under {path}")
    return pd.concat((pd.read_parquet(f) for f in files), ignore_index=True)


def main(d):
    proc = read_dir(f"{d}/processed")
    glue = read_dir(f"{d}/features").set_index("customer_id").sort_index()
    mine = (build_churn_feature_set(None, proc, FEATURE_CUTOFF)
            .set_index("customer_id").reindex(glue.index))

    print(f"Feature equivalence: data/feature_engineering.py vs Glue features/ ({d})")
    print(f"T = {FEATURE_CUTOFF.date()}; processed rows = {len(proc)}")
    print(f"customers: glue = {len(glue)}, pandas = {mine.notna().all(axis=1).sum()} matched, "
          f"pandas-only = {len(set(build_churn_feature_set(None, proc).customer_id) - set(glue.index))}")
    print()
    print(f"{'column':28s} {'max_abs_diff':>12s} {'rows_diff':>9s} {'rows_>tol':>9s}")
    worst = 0.0
    for c in NUMERIC:
        diff = (glue[c].astype(float) - mine[c].astype(float)).abs()
        worst = max(worst, diff.max())
        print(f"{c:28s} {diff.max():12.6f} {(diff > 0).sum():9d} {(diff > TOL + 1e-9).sum():9d}")
    tier_mismatch = (glue["loyalty_tier"] != mine["loyalty_tier"]).sum()
    print(f"{'loyalty_tier':28s} {'':12s} {tier_mismatch:9d} {tier_mismatch:9d}")
    print()
    ok = worst <= TOL + 1e-9 and tier_mismatch == 0
    print("RESULT:", "MATCH (differences within 0.0001 rounding)" if ok else "MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/lab4data"))
