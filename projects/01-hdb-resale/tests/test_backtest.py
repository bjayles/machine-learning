"""Tests for `backtest()`: a cleaned table and a model go in, per-row estimates come out.

The model is a test double (`SpyModel`) that records what the harness shows it, so the
tests can check the backtest windows and, above all, that no window ever trains on its
test month or later (project ADR-0001).
"""

import pandas as pd
import pytest

from hdb_resale.backtest import backtest

from factories import make_clean

# Six registration months; the last one is the current month, still filling up
MONTHS = ["2024-01", "2024-02", "2024-03", "2024-04", "2024-05", "2024-06"]


class SpyModel:
    """Model that remembers every training and test table it receives."""

    def __init__(self):
        self.train_months = []  # per window: the months of its training rows
        self.predict_inputs = []  # per window: the table it was asked to estimate

    def fit(self, train: pd.DataFrame) -> None:
        self.train_months.append(sorted(train["month"].unique()))

    def predict(self, test: pd.DataFrame) -> pd.Series:
        self.predict_inputs.append(test)
        return pd.Series(500_000.0, index=test.index)


def months(*values: str) -> list[pd.Period]:
    return [pd.Period(v, freq="M") for v in values]


def test_tests_the_latest_complete_months():
    predictions = backtest(make_clean(MONTHS), SpyModel(), n_windows=3)

    # 2024-06 is still filling: the 3 windows test the 3 complete months before it
    assert sorted(predictions["month"].unique()) == months(
        "2024-03", "2024-04", "2024-05"
    )


def test_never_trains_on_the_test_month_or_later():
    model = SpyModel()

    predictions = backtest(make_clean(MONTHS), model, n_windows=3)

    test_months = sorted(predictions["month"].unique())
    assert len(model.train_months) == len(test_months) == 3  # the loop below must run
    for trained_on, test_month in zip(model.train_months, test_months, strict=True):
        assert max(trained_on) < test_month


def test_expanding_window_trains_on_all_earlier_months():
    model = SpyModel()

    backtest(make_clean(MONTHS), model, n_windows=3)

    # Testing 2024-03 trains on Jan-Feb, 2024-04 on Jan-Mar, 2024-05 on Jan-Apr
    assert model.train_months == [
        months("2024-01", "2024-02"),
        months("2024-01", "2024-02", "2024-03"),
        months("2024-01", "2024-02", "2024-03", "2024-04"),
    ]


def test_sliding_window_trains_on_the_last_n_months_only():
    model = SpyModel()

    backtest(make_clean(MONTHS), model, n_windows=3, train_months=2)

    assert model.train_months == [
        months("2024-01", "2024-02"),
        months("2024-02", "2024-03"),
        months("2024-03", "2024-04"),
    ]


def test_model_never_sees_the_test_prices():
    model = SpyModel()

    backtest(make_clean(MONTHS), model, n_windows=3)

    # The answer must not be handed to the model it's testing
    assert len(model.predict_inputs) == 3  # the loop below must run
    for test in model.predict_inputs:
        assert "resale_price" not in test.columns


def test_every_test_transaction_gets_one_estimate():
    data = make_clean(MONTHS, rows_per_month=4)

    predictions = backtest(data, SpyModel(), n_windows=3)

    # 3 test months x 4 transactions, each with its real price and an estimate
    assert len(predictions) == 12
    assert predictions["estimate"].notna().all()
    assert predictions["resale_price"].notna().all()


def test_too_few_months_fails_loudly():
    # 6 months = 5 complete ones: 5 windows would leave the first with nothing to train on
    with pytest.raises(ValueError, match="months"):
        backtest(make_clean(MONTHS), SpyModel(), n_windows=5)


def test_end_shifts_the_windows_earlier_for_validation():
    model = SpyModel()

    # Validation: stop testing before 2024-05, as if 2024-05 were the test period
    predictions = backtest(make_clean(MONTHS), model, n_windows=2, end="2024-05")

    assert sorted(predictions["month"].unique()) == months("2024-03", "2024-04")
    # No window ever trains on 2024-05 or later
    assert len(model.train_months) == 2
    assert all(
        max(trained_on) < pd.Period("2024-05", freq="M")
        for trained_on in model.train_months
    )
