"""Tests for `train()`: the model to ship, fitted on the latest complete months."""

import pandas as pd

from hdb_resale.train import train

from factories import make_clean

# Six registration months; the last one is the current month, still filling up
MONTHS = ["2024-01", "2024-02", "2024-03", "2024-04", "2024-05", "2024-06"]


class SpyModel:
    """Model that remembers the months it was trained on."""

    def fit(self, train: pd.DataFrame) -> None:
        self.trained_on = sorted(train["month"].unique())


def months(*values: str) -> list[pd.Period]:
    return [pd.Period(v, freq="M") for v in values]


def test_trains_on_the_latest_complete_months_only():
    fitted = train(make_clean(MONTHS), SpyModel(), train_months=3)

    # Like the next backtest window: the current month (2024-06) is never used
    assert fitted.trained_on == months("2024-03", "2024-04", "2024-05")


def test_without_a_window_trains_on_all_complete_months():
    fitted = train(make_clean(MONTHS), SpyModel())

    assert fitted.trained_on == months(*MONTHS[:-1])
