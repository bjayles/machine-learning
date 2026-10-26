"""Backtest harness: score any model the way it will be used in production.

Rolling backtest (project ADR-0001): for each of the latest `n_windows` complete
registration months, train on the months before it, then estimate that month's resale
prices. Every model goes through the same windows, so their scores are comparable,
and the "never train on the future" rule lives here, once.

A model is anything with `fit(train)` and `predict(test) -> estimates`, the
scikit-learn convention. The harness returns estimates, not scores: the metric is
chosen from the residual analysis (project ADR-0006), and scoring is a separate step.
"""

from typing import Protocol

import numpy as np
import pandas as pd

from hdb_resale.schemas import CLEAN_SCHEMA


class Model(Protocol):
    """What the harness needs from a model: learn from past sales, estimate new ones."""

    def fit(self, train: pd.DataFrame) -> object:
        """Learn from the training months' transactions, resale prices included."""
        ...

    def predict(self, test: pd.DataFrame) -> pd.Series:
        """Return one estimate per test transaction (resale prices removed)."""
        ...


def backtest(
    data: pd.DataFrame,
    model: Model,
    n_windows: int = 12,
    train_months: int | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Run the rolling backtest and return the test transactions with their estimates.

    Args:
        data: The cleaned table (must match CLEAN_SCHEMA).
        model: Refitted from scratch in every backtest window.
        n_windows: How many test months, counting back from the latest complete one.
        train_months: None trains on all earlier months (expanding window); N trains
            on the N months before the test month only (sliding window).
        end: The first month not to test ("2025-10"), to backtest an earlier period,
            e.g. validation months before the test period. Default: the latest
            registration month, which is still filling up.

    Returns:
        The test months' transactions, with an `estimate` column next to the
        real `resale_price`. `month` identifies the backtest window.
    """
    data = CLEAN_SCHEMA.validate(data)

    # The latest registration month is the current one, still filling up: never used.
    # With `end`, the data from that month on is set aside instead
    if end is not None:
        data = data[data["month"] < pd.Period(end, freq="M")]
        complete_months = sorted(data["month"].unique())
    else:
        complete_months = sorted(data["month"].unique())[:-1]
    if n_windows >= len(complete_months):
        raise ValueError(
            f"{n_windows} windows need more than {len(complete_months)} complete months:"
            " the first window would have nothing to train on"
        )
    test_months = complete_months[-n_windows:]

    windows = []
    for test_month in test_months:
        train = data[data["month"] < test_month]
        if train_months is not None:
            train = train[train["month"] >= test_month - train_months]
        test = data[data["month"] == test_month]

        model.fit(train)
        # The model gets the test transactions without their prices: no peeking
        estimates = model.predict(test.drop(columns="resale_price"))
        windows.append(test.assign(estimate=list(estimates)))

    return pd.concat(windows)


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
