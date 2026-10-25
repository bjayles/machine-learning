"""Tests for `backtest()`: a cleaned table and a model go in, per-row estimates come out.

The model is a test double (`SpyModel`) that records what the harness shows it, so the
tests can check the backtest windows and, above all, that no window ever trains on its
test month or later (project ADR-0001).
"""

import pandas as pd
import pytest

from hdb_resale.backtest import backtest, score

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


def test_score_reports_the_four_candidate_metrics_per_window():
    # Worked by hand. 2024-03: one sale 10% over (550k vs 500k), one exact.
    # 2024-04: one 20% over (600k), one 10% under (450k), one exact.
    predictions = pd.DataFrame(
        {
            "month": months("2024-03", "2024-03", "2024-04", "2024-04", "2024-04"),
            "resale_price": [500_000.0, 400_000.0, 500_000.0, 500_000.0, 500_000.0],
            "estimate": [550_000.0, 400_000.0, 600_000.0, 450_000.0, 500_000.0],
        }
    )

    scores = score(predictions)

    march, april = months("2024-03", "2024-04")
    assert list(scores.index) == [march, april]
    assert scores.loc[march, "sales"] == 2
    # MAE in S$: (50k + 0) / 2; (100k + 50k + 0) / 3
    assert scores.loc[march, "mae"] == pytest.approx(25_000)
    assert scores.loc[april, "mae"] == pytest.approx(50_000)
    # MAPE: (10% + 0%) / 2; (20% + 10% + 0%) / 3
    assert scores.loc[march, "mape"] == pytest.approx(0.05)
    assert scores.loc[april, "mape"] == pytest.approx(0.10)
    # MdAPE: median of (10%, 0%); median of (20%, 10%, 0%)
    assert scores.loc[march, "mdape"] == pytest.approx(0.05)
    assert scores.loc[april, "mdape"] == pytest.approx(0.10)
    # Log-space MAE: |ln 1.1| / 2; (|ln 1.2| + |ln 0.9|) / 3
    assert scores.loc[march, "log_mae"] == pytest.approx(0.04766, abs=1e-5)
    assert scores.loc[april, "log_mae"] == pytest.approx(0.09589, abs=1e-5)


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
