"""
NorthStar Retail — Fairness Check
CS 401R Lab 4

Flags (does not block) a recall@top10% gap of more than 10 percentage points
between the best and worst loyalty tier. A manual slice evaluation, not
SageMaker Clarify: the training job already computes per-tier recall on the
held-out split, and churn_model.train() writes it to evaluation_metrics.json
as metrics["slice_results"] (one dict per tier, from Lab 3's evaluate_slices).

Recall is measured at the GLOBAL top-10% cutoff, because the retention team
contacts the top 10% of all customers. Only reliable tiers count (>= 20
positives and >= 20 negatives); below that a tier's recall is noise.

The flag is a FairnessWarning, and the test still passes. buildspec.yml runs
this file with -rw, so "FAIRNESS FLAG" lands in the build log's warnings
summary for the approver to read. Expect it to fire on this data: high-value
tiers churn rarely, so few of them reach the global top 10%.

Run locally (after the local training run in the lab handout):
    EVAL_METRICS_PATH=/tmp/out/evaluation_metrics.json pytest tests/test_fairness.py -v -rw
"""

import json
import os
import warnings
from pathlib import Path

import pytest

MAX_RECALL_GAP = 0.10


class FairnessWarning(UserWarning):
    """A tier's recall trails another tier's by more than MAX_RECALL_GAP."""


def recall_gap(slices):
    """(gap, best tier, worst tier) over reliable tiers, or (None, None, None)
    if fewer than two tiers are reliable. Non-dict entries such as
    '_worst_tier' are ignored."""
    usable = {t: r["recall_top10"] for t, r in slices.items()
              if isinstance(r, dict) and r.get("reliable")}
    if len(usable) < 2:
        return None, None, None
    best, worst = max(usable, key=usable.get), min(usable, key=usable.get)
    return usable[best] - usable[worst], best, worst


def flag_if_unfair(slices, max_gap=MAX_RECALL_GAP):
    """Warn and return True if the reliable-tier recall gap exceeds max_gap."""
    gap, best, worst = recall_gap(slices)
    if gap is not None and gap > max_gap:
        warnings.warn(f"FAIRNESS FLAG: recall@top10% gap {gap:.1%} between {best} and {worst}",
                      FairnessWarning)
        return True
    return False


def _tier(recall, reliable=True):
    return {"recall_top10": recall, "reliable": reliable}


# ── Logic on synthetic slices (no model needed) ───────────────────────────────

class TestFairnessLogic:

    def test_large_gap_is_flagged(self):
        slices = {"Bronze": _tier(0.42), "Silver": _tier(0.30), "Gold": _tier(0.12)}
        with pytest.warns(FairnessWarning, match="Bronze and Gold"):
            assert flag_if_unfair(slices) is True

    def test_small_gap_is_not_flagged(self):
        slices = {"Bronze": _tier(0.40), "Silver": _tier(0.35), "Gold": _tier(0.32)}
        with warnings.catch_warnings():
            warnings.simplefilter("error", FairnessWarning)
            assert flag_if_unfair(slices) is False

    def test_gap_equal_to_threshold_is_not_flagged(self):
        """The handout says 'exceeds': a gap equal to the threshold is not a flag.
        (0.75 - 0.50 is exact in binary; 0.50 - 0.40 is not, so it can't test this.)"""
        slices = {"Bronze": _tier(0.75), "Gold": _tier(0.50)}
        with warnings.catch_warnings():
            warnings.simplefilter("error", FairnessWarning)
            assert flag_if_unfair(slices, max_gap=0.25) is False

    def test_unreliable_tier_is_excluded(self):
        """A tier with too few positives cannot set the gap, however extreme."""
        slices = {"Bronze": _tier(0.40), "Silver": _tier(0.36),
                  "Platinum": _tier(0.00, reliable=False), "_worst_tier": "Silver"}
        gap, best, worst = recall_gap(slices)
        assert (best, worst) == ("Bronze", "Silver")
        assert gap == pytest.approx(0.04)

    def test_fewer_than_two_reliable_tiers_gives_no_gap(self):
        slices = {"Bronze": _tier(0.40), "Gold": _tier(0.05, reliable=False)}
        assert recall_gap(slices) == (None, None, None)


# ── The trained model's slices ────────────────────────────────────────────────

@pytest.fixture(scope="module")
def eval_metrics():
    metrics_path = os.environ.get("EVAL_METRICS_PATH", "/tmp/eval_metrics.json")
    if not Path(metrics_path).exists():
        pytest.skip(f"Evaluation metrics not found at {metrics_path}.")
    with open(metrics_path) as f:
        return json.load(f)


class TestModelFairness:

    def test_recall_gap_across_loyalty_tiers(self, eval_metrics):
        """Flag, do not block. Metrics without slice_results is a failure: the
        check was asked for and could not be done, which must not read as fair."""
        slices = eval_metrics.get("slice_results")
        assert slices, (
            "evaluation_metrics.json has no slice_results. churn_model.train() must "
            "put the per-tier evaluation (Lab 3 evaluate_slices) into its metrics dict."
        )
        gap, _, _ = recall_gap(slices)
        assert gap is not None, (
            f"Fewer than two reliable tiers in slice_results ({sorted(slices)}); "
            f"the recall gap cannot be measured."
        )
        flag_if_unfair(slices)
