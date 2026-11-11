"""Backtest harness: score any model the way it will be used in production.

Rolling backtest (project ADR-0001): for each of the latest `n_windows` complete
registration months, train on the months before it, then estimate that month's resale
prices. Every model goes through the same windows, so their scores are comparable,
and the "never train on the future" rule lives here, once.

A model is anything with `fit(train)` and `predict(test) -> estimates`, the
scikit-learn convention. The harness returns estimates, not scores: the metric is
chosen from the residual analysis (project ADR-0006), and scoring is a separate step
(evaluate.py).
"""

from typing import Protocol

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


def backtest_periods(
    data: pd.DataFrame,
    model: Model,
    n_windows: int = 12,
    train_months: int | None = None,
) -> pd.DataFrame:
    """Backtest the test period and the validation period just before it.

    Settings are chosen on the validation period and reported on the test period, so
    choosing never looks at the test months. Every run scores both.

    Args:
        data: The cleaned table (must match CLEAN_SCHEMA).
        model: Refitted from scratch in every backtest window.
        n_windows: Test months per period: the latest complete ones for the test
            period, the ones just before them for the validation period.
        train_months: As in `backtest()`.

    Returns:
        `backtest()` output for both periods, with a `period` column ("validation" or
        "test").
    """
    test = backtest(data, model, n_windows, train_months)
    validation = backtest(
        data, model, n_windows, train_months, end=str(test["month"].min())
    )
    return pd.concat(
        [validation.assign(period="validation"), test.assign(period="test")]
    )
