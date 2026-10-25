"""Tests for the hedonic regression: each one fits it on a tiny hand-made market.

Prices are built from known multiplicative effects (a town premium, a monthly rise, a
size elasticity, lease bands), so a correct model must recover them exactly; expected
estimates are worked out by hand in the comments.
"""

import pandas as pd
import pytest

from hdb_resale.clean import clean
from hdb_resale.models import HedonicRegression

from factories import make_raw


def sale(month="2024-01", town="ANG MO KIO", sqm=64.0, lease="70 years", price=1.0):
    return {
        "month": month,
        "town": town,
        "floor_area_sqm": float(sqm),
        "remaining_lease": lease,
        "resale_price": float(price),
    }


def table(*sales: dict) -> pd.DataFrame:
    return clean(make_raw(*sales))


def estimate(model: HedonicRegression, **flat) -> float:
    """The model's estimate for one flat, sent without its price (as backtest() does)."""
    test = table(sale(**flat)).drop(columns="resale_price")
    return model.predict(test).iloc[0]


def test_town_and_month_effects_multiply_and_the_latest_month_carries_forward():
    # Tampines is 25% above Ang Mo Kio; February is 10% above January, in both towns
    model = HedonicRegression().fit(
        table(
            sale(month="2024-01", price=400_000),
            sale(month="2024-02", price=440_000),
            sale(month="2024-01", town="TAMPINES", price=500_000),
            sale(month="2024-02", town="TAMPINES", price=550_000),
        )
    )

    # March was never seen: it gets February's level, the latest one
    assert estimate(model, month="2024-03") == pytest.approx(440_000)
    assert estimate(model, month="2024-03", town="TAMPINES") == pytest.approx(550_000)


def test_price_scales_with_floor_area_through_its_elasticity():
    # Price grows with the square root of floor area: 64 m² -> 400k, 100 m² -> 500k
    model = HedonicRegression().fit(
        table(sale(sqm=64, price=400_000), sale(sqm=100, price=500_000))
    )

    # 81 m²: 400k x sqrt(81 / 64) = 450k
    assert estimate(model, sqm=81) == pytest.approx(450_000)


def test_remaining_lease_acts_in_five_year_bands():
    # A step between the 60-65 and 85-90 year bands, nothing within a band
    model = HedonicRegression().fit(
        table(
            sale(lease="60 years", price=400_000),
            sale(lease="88 years", price=460_000),
        )
    )

    # Same band, same level: 62 years like 60, 86 years like 88
    assert estimate(model, lease="62 years") == pytest.approx(400_000)
    assert estimate(model, lease="86 years") == pytest.approx(460_000)


def test_month_levels_form_a_price_index():
    # The same flat is 10% dearer in February and 21% dearer in March than in January
    model = HedonicRegression().fit(
        table(
            sale(month="2024-01", price=400_000),
            sale(month="2024-02", price=440_000),
            sale(month="2024-03", price=484_000),
        )
    )

    index = model.price_index()

    # Relative to the first training month
    assert list(index.index) == [
        pd.Period(m, freq="M") for m in ["2024-01", "2024-02", "2024-03"]
    ]
    assert list(index) == pytest.approx([1.00, 1.10, 1.21])


def test_effects_are_multipliers_against_the_reference_value():
    model = HedonicRegression().fit(
        table(sale(price=400_000), sale(town="TAMPINES", price=500_000))
    )

    effects = model.effects("town")

    # Ang Mo Kio is the reference (first alphabetically); Tampines is 25% above it
    assert effects.to_dict() == pytest.approx({"ANG MO KIO": 1.0, "TAMPINES": 1.25})


def test_linear_lease_option_draws_one_straight_line_on_log_price():
    # Each extra year of lease adds the same percentage: 60 -> 400k, 70 -> 440k
    model = HedonicRegression(lease="linear").fit(
        table(
            sale(lease="60 years", price=400_000), sale(lease="70 years", price=440_000)
        )
    )

    # Halfway in years is halfway on the log scale: sqrt(400k x 440k)
    assert estimate(model, lease="65 years") == pytest.approx(
        (400_000 * 440_000) ** 0.5
    )
