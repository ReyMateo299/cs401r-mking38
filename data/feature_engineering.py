"""Pandas port of the Lab 2 Glue feature job (glue-scripts/feature_engineer.py).

The Glue job stays the production feature pipeline; this module exists so the
same definitions can be unit tested in CodeBuild without Spark. Every
definition here must match compute_rfm_features, assign_loyalty_tier,
compute_churn_proxy and attach_churn_label in the Glue job. The post-cutoff
leakage test in tests/test_data.py recomputes features with these functions
and compares them with what Glue wrote, so drift fails the build.

Temporal split (same as Glue):
  * features use only purchases on or before T (FEATURE_CUTOFF)
  * churn_label = 1 if no purchase in (T, HOLDOUT_END]
Windows are measured backwards from T, strictly after: purchase_date > T - N days.
"""

import numpy as np
import pandas as pd

FEATURE_CUTOFF = pd.Timestamp("2026-04-01")   # Glue: FEATURE_CUTOFF (T)
HOLDOUT_END = pd.Timestamp("2026-06-30")      # Glue: SNAPSHOT
N_CATEGORIES = 8.0

# Loyalty tier thresholds on total lifetime value (USD), from the Glue job.
TIER_BRONZE_MAX = 500.0
TIER_SILVER_MAX = 2000.0
TIER_GOLD_MAX = 5000.0

# Glue rounds these to 4 dp before writing (main()).
ROUNDED_COLUMNS = ["avg_order_value", "total_lifetime_value", "total_spend_90d",
                   "avg_basket_size_6m", "category_diversity_score", "online_to_store_ratio"]


def _dates(transactions):
    df = transactions.copy()
    df["purchase_date"] = pd.to_datetime(df["purchase_date"], format="mixed").dt.normalize()
    return df


def _history(transactions, as_of):
    df = _dates(transactions)
    return df[df["purchase_date"] <= pd.Timestamp(as_of).normalize()]   # Glue: purchase_date <= T


def _in_window(df, as_of, days):
    # Glue: purchase_date > date_sub(T, days). Strictly after.
    return df["purchase_date"] > pd.Timestamp(as_of).normalize() - pd.Timedelta(days=days)


def _ids(df, customer_ids=None):
    """Customers to emit one row for. Accepts None (everyone in the history),
    a DataFrame with a customer_id column, or a Series / list of ids."""
    if customer_ids is None:
        ids = df["customer_id"].unique()
    elif isinstance(customer_ids, pd.DataFrame):
        ids = customer_ids["customer_id"].unique()
    else:
        ids = pd.Series(customer_ids).unique()
    return pd.Index(ids, name="customer_id")


def compute_recency_features(transactions, as_of, customer_ids=None, sentinel=999.0):
    df = _history(transactions, as_of)
    idx = _ids(df, customer_ids)
    t = pd.Timestamp(as_of).normalize()
    g = df.groupby("customer_id")["purchase_date"]
    out = pd.DataFrame(index=idx)
    # No history: recency is the sentinel, tenure is 0 (never NaN).
    out["days_since_last_purchase"] = (t - g.max()).dt.days.reindex(idx).fillna(sentinel).astype(float)
    out["customer_tenure_days"] = (t - g.min()).dt.days.reindex(idx).fillna(0.0).astype(float)
    return out.reset_index()


def compute_frequency_features(transactions, as_of, customer_ids=None):
    df = _history(transactions, as_of)
    idx = _ids(df, customer_ids)
    out = pd.DataFrame(index=idx)
    for days in (30, 90, 180):
        counts = df[_in_window(df, as_of, days)].groupby("customer_id").size()
        out[f"purchase_frequency_{days}d"] = counts.reindex(idx).fillna(0).astype(float)
    return out.reset_index()


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
    # Items per order, not dollars; guarded denominator like Glue.
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


def assign_loyalty_tier(ltv):
    """Glue assign_loyalty_tier: <500 Bronze, <2000 Silver, <5000 Gold, else Platinum."""
    return pd.Series(np.select(
        [ltv < TIER_BRONZE_MAX, ltv < TIER_SILVER_MAX, ltv < TIER_GOLD_MAX],
        ["Bronze", "Silver", "Gold"], default="Platinum"), index=ltv.index)


def compute_churn_proxy(days, freq_30d):
    """Glue compute_churn_proxy: rule-based score in [0, 1], scaled within each band."""
    high = 0.7 + 0.3 * np.minimum((days - 60) / 120.0, 1.0)
    medium = 0.4 + 0.3 * np.minimum((days - 30) / 30.0, 1.0)
    low = 0.0 + 0.4 * np.minimum(days / 30.0, 1.0)
    score = np.select([(days > 60) & (freq_30d == 0), days > 30], [high, medium], default=low)
    return pd.Series(np.clip(score, 0.0, 1.0), index=days.index).round(4)


def build_churn_feature_set(customers, transactions, snapshot_date=FEATURE_CUTOFF):
    """One row per customer: the 11 model features, loyalty_tier,
    churn_risk_score and churn_label, as the Glue job writes them.

    snapshot_date is the feature cutoff T. customers may be None, in which case
    the rows are the customers with history on or before T (Glue's output);
    otherwise every customer in the roster gets a complete row.
    """
    t = pd.Timestamp(snapshot_date).normalize()
    ids = None if customers is None else _ids(customers, customers)
    if ids is None:
        ids = _ids(_history(transactions, t))

    out = compute_recency_features(transactions, t, ids)
    for part in (compute_frequency_features(transactions, t, ids),
                 compute_monetary_features(transactions, t, ids),
                 compute_behavioral_features(transactions, t, ids)):
        out = out.merge(part, on="customer_id", how="left")

    out["loyalty_tier"] = assign_loyalty_tier(out["total_lifetime_value"])
    out["churn_risk_score"] = compute_churn_proxy(out["days_since_last_purchase"],
                                                  out["purchase_frequency_30d"])

    # Label from the holdout only, (T, HOLDOUT_END], never from a feature.
    df = _dates(transactions)
    holdout = df[(df["purchase_date"] > t) & (df["purchase_date"] <= HOLDOUT_END)]
    out["churn_label"] = (~out["customer_id"].isin(holdout["customer_id"])).astype(int)

    out[ROUNDED_COLUMNS] = out[ROUNDED_COLUMNS].round(4)
    return out
