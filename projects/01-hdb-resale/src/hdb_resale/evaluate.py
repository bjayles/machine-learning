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
