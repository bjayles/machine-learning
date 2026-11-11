"""Tests for scoring backtest estimates and the "good enough" check (project ADR-0006)."""

import pandas as pd
import pytest

from hdb_resale.evaluate import evaluate, good_enough, score


def months(*values: str) -> list[pd.Period]:
    return [pd.Period(v, freq="M") for v in values]


def test_score_reports_error_size_bias_and_spread_per_window():
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
    # Bias, the mean of log(price / estimate), > 0 when estimates are too low:
    # March, ln(1/1.1) over 2 sales; April, ln(500/600) plus ln(500/450) over 3 sales
    assert scores.loc[march, "bias"] == pytest.approx(-0.04766, abs=1e-5)
    assert scores.loc[april, "bias"] == pytest.approx(-0.02565, abs=1e-5)
    # 90th percentile of the % error, interpolated: of (0%, 10%); of (0%, 10%, 20%)
    assert scores.loc[march, "p90_ape"] == pytest.approx(0.09)
    assert scores.loc[april, "p90_ape"] == pytest.approx(0.18)


def scores_table(log_mae: float, p90_ape: float, bias: float) -> pd.DataFrame:
    """Scores of two backtest windows with the same values."""
    return pd.DataFrame(
        {"log_mae": [log_mae] * 2, "p90_ape": [p90_ape] * 2, "bias": [bias] * 2}
    )


def test_good_enough_checks_each_condition_of_the_threshold():
    baseline = scores_table(log_mae=0.12, p90_ape=0.25, bias=0.0)

    passing = good_enough(scores_table(0.04, 0.08, 0.003), baseline)
    # Each failing model breaks exactly one condition (project ADR-0006)
    not_worth_it = good_enough(scores_table(0.065, 0.08, 0.003), baseline)  # > 0.12 / 2
    wide_tail = good_enough(scores_table(0.04, 0.12, 0.003), baseline)  # p90 > 10%
    biased = good_enough(scores_table(0.04, 0.08, -0.02), baseline)  # |bias| > 1%

    assert passing.all()
    assert not not_worth_it["half_the_baseline"]
    assert not not_worth_it["log_mae"]  # 0.065 also breaks the 0.05 ceiling
    assert not wide_tail["p90_ape"] and wide_tail.drop("p90_ape").all()
    assert not biased["bias"] and biased.drop("bias").all()


def periods_predictions(over: float) -> pd.DataFrame:
    """Two windows per period, every estimate `over` (0.1 = 10%) above the price."""
    month = months("2024-01", "2024-02", "2024-03", "2024-04")
    return pd.DataFrame(
        {
            "period": ["validation", "validation", "test", "test"],
            "month": month,
            "resale_price": [500_000.0] * 4,
            "estimate": [500_000.0 * (1 + over)] * 4,
        }
    )


def test_evaluate_scores_each_estimator_and_period_and_checks_the_test_period():
    windows, summary = evaluate(periods_predictions(0.0), periods_predictions(0.1))

    # One row per estimator, period and backtest window
    assert len(windows) == 2 * 4
    assert set(windows["estimator"]) == {"model", "baseline"}
    # Averages per estimator and period
    assert summary["model"]["test"]["log_mae"] == pytest.approx(0.0)
    assert summary["baseline"]["validation"]["mape"] == pytest.approx(0.1)
    # The threshold is checked on the test period: an exact model passes everything
    assert summary["good_enough"] == {
        "half_the_baseline": True,
        "log_mae": True,
        "p90_ape": True,
        "bias": True,
        "all": True,
    }
