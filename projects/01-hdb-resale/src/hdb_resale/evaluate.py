"""Evaluation: score backtest estimates and check them against the "good enough" threshold.

Kept apart from the backtest harness (backtest.py), which only produces estimates: the
pipeline runs them as separate stages, so changing a metric doesn't rerun the backtest.
The primary metric and the threshold come from the residual analysis (project ADR-0006).
"""

import numpy as np
import pandas as pd


def score(predictions: pd.DataFrame) -> pd.DataFrame:
    """Score each backtest window: error size, bias and spread.

    The primary metric is `log_mae` (project ADR-0006); the others are reported to
    read it (`mdape`, `p90_ape`, `mae`) or to check it (`bias`). Relative metrics
    are fractions (0.05 = 5%).

    Args:
        predictions: `backtest()` output: `month`, `resale_price` and `estimate`.

    Returns:
        One row per backtest window (indexed by test month): `sales`, `mae` (S$),
        `mape`, `mdape`, `p90_ape`, `log_mae` and `bias`.
    """
    # log(price / estimate): > 0 when the estimate is too low
    residual = np.log(predictions["resale_price"] / predictions["estimate"])
    errors = pd.DataFrame(
        {
            "month": predictions["month"],
            "abs_error": (predictions["estimate"] - predictions["resale_price"]).abs(),
            "residual": residual,
            "log_error": residual.abs(),
        }
    )
    errors["pct_error"] = errors["abs_error"] / predictions["resale_price"]

    return errors.groupby("month").agg(
        sales=("abs_error", "size"),
        mae=("abs_error", "mean"),  # average error in S$
        mape=("pct_error", "mean"),  # average error in %
        mdape=("pct_error", "median"),  # typical error in %, robust to a few big misses
        p90_ape=("pct_error", lambda e: e.quantile(0.9)),  # 9 in 10 within this
        log_mae=("log_error", "mean"),  # primary: average error on log prices
        bias=("residual", "mean"),  # > 0: estimates too low on average
    )


# The "good enough" threshold (project ADR-0006), on the average over the backtest windows
MAX_SHARE_OF_BASELINE = 0.5  # log-space MAE at most half the reference baseline's
MAX_LOG_MAE = 0.05  # about 5% average error
MAX_P90_APE = 0.10  # 9 in 10 estimates within 10%
MAX_ABS_BIAS = 0.01  # estimates no more than 1% too high or too low on average


def good_enough(scores: pd.DataFrame, baseline_scores: pd.DataFrame) -> pd.Series:
    """Check a model's backtest scores against each condition of the threshold.

    Args:
        scores: `score()` output for the model.
        baseline_scores: `score()` output for the reference baseline, on the same
            backtest windows.

    Returns:
        One boolean per condition; the model is good enough if all are True.
    """
    log_mae = scores["log_mae"].mean()
    return pd.Series(
        {
            "half_the_baseline": log_mae
            <= MAX_SHARE_OF_BASELINE * baseline_scores["log_mae"].mean(),
            "log_mae": log_mae <= MAX_LOG_MAE,
            "p90_ape": scores["p90_ape"].mean() <= MAX_P90_APE,
            "bias": abs(scores["bias"].mean()) <= MAX_ABS_BIAS,
        }
    )


def evaluate(
    model_predictions: pd.DataFrame, baseline_predictions: pd.DataFrame
) -> tuple[pd.DataFrame, dict]:
    """Score the model and the reference baseline on both periods, and check the threshold.

    Settings are chosen on the validation period's averages; the threshold is checked
    on the test period's, since that's the score reported and gated on.

    Args:
        model_predictions: `backtest_periods()` output for the model.
        baseline_predictions: The same for the reference baseline.

    Returns:
        The scores per backtest window (one row per estimator, period and window),
        and a summary: each estimator's average scores per period, plus the
        `good_enough()` conditions on the test period and whether `all` hold.
    """
    scores = {
        "model": _score_periods(model_predictions),
        "baseline": _score_periods(baseline_predictions),
    }
    windows = pd.concat(scores, names=["estimator"]).reset_index()

    summary: dict = {
        estimator: {
            period: {
                metric: round(float(value), 6)
                for metric, value in by_window.drop(columns="sales").mean().items()
            }
            for period, by_window in estimator_scores.groupby(level="period")
        }
        for estimator, estimator_scores in scores.items()
    }
    checks = good_enough(scores["model"].loc["test"], scores["baseline"].loc["test"])
    summary["good_enough"] = {
        **{name: bool(passed) for name, passed in checks.items()},
        "all": bool(checks.all()),
    }
    return windows, summary


def _score_periods(predictions: pd.DataFrame) -> pd.DataFrame:
    """`score()` each period separately, indexed by period and test month."""
    return pd.concat(
        {period: score(rows) for period, rows in predictions.groupby("period")},
        names=["period"],
    )
