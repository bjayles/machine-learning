"""Tests for the naive baselines: each one is fitted on a tiny hand-made table.

The seam is the model interface the backtest uses: `fit(train)`, then
`predict(test)`. Expected estimates are worked out by hand in the comments.
"""

import pandas as pd
import pytest

from hdb_resale.baselines import OverallMedian, TownFlatTypeMedian
from hdb_resale.clean import clean

from factories import make_raw


def sale(month="2024-06", town="ANG MO KIO", flat_type="3 ROOM", price=0.0, sqm=60.0):
    """One raw transaction with the fields the baselines look at."""
    return {
        "month": month,
        "town": town,
        "flat_type": flat_type,
        "resale_price": float(price),  # the snapshot stores both as decimals
        "floor_area_sqm": float(sqm),
    }


def table(*sales: dict) -> pd.DataFrame:
    return clean(make_raw(*sales))


def flat(town="ANG MO KIO", flat_type="3 ROOM", sqm=60.0) -> pd.DataFrame:
    """A test transaction to estimate, without its resale price (as backtest() sends it)."""
    return table(sale(town=town, flat_type=flat_type, price=1.0, sqm=sqm)).drop(
        columns="resale_price"
    )


def test_overall_median_estimates_the_median_training_price():
    train = table(sale(price=100_000), sale(price=200_000), sale(price=900_000))

    estimates = OverallMedian().fit(train).predict(flat())

    assert estimates.iloc[0] == 200_000


def test_group_median_uses_the_same_town_and_flat_type():
    train = table(
        sale(price=300_000),
        sale(price=320_000),
        sale(price=340_000),
        sale(flat_type="4 ROOM", price=500_000),  # other flat type: ignored
        sale(town="TAMPINES", price=400_000),  # other town: ignored
    )

    estimates = TownFlatTypeMedian().fit(train).predict(flat())

    # Median of the three Ang Mo Kio 3-room sales
    assert estimates.iloc[0] == 320_000


def test_group_median_only_uses_the_recent_months():
    train = table(
        sale(month="2023-01", price=100_000),  # 17 months before the latest: ignored
        sale(month="2024-01", price=300_000),
        sale(month="2024-06", price=340_000),
    )

    estimates = TownFlatTypeMedian(recent_months=12).fit(train).predict(flat())

    # Median of the 2024 sales only: (300k + 340k) / 2
    assert estimates.iloc[0] == 320_000


def test_empty_group_falls_back_to_the_flat_type_anywhere():
    train = table(
        sale(flat_type="4 ROOM", price=500_000),
        sale(town="BEDOK", flat_type="4 ROOM", price=600_000),
        sale(price=300_000),  # Ang Mo Kio 3-room: other flat type, ignored
    )

    # No Tampines 4-room sale: use 4-room flats in any town
    estimates = TownFlatTypeMedian().fit(train).predict(flat("TAMPINES", "4 ROOM"))

    assert estimates.iloc[0] == 550_000


def test_unknown_flat_type_falls_back_to_all_sales():
    train = table(sale(price=300_000), sale(price=400_000), sale(price=800_000))

    # No 1-room sale anywhere: use the median of all recent sales
    estimates = TownFlatTypeMedian().fit(train).predict(flat(flat_type="1 ROOM"))

    assert estimates.iloc[0] == 400_000


def test_per_sqm_median_scales_with_floor_area():
    train = table(
        sale(price=300_000, sqm=60),  # S$5,000 per m²
        sale(price=330_000, sqm=66),  # S$5,000 per m²
    )

    estimates = TownFlatTypeMedian(per_sqm=True).fit(train).predict(flat(sqm=70))

    # S$5,000 per m² x 70 m²
    assert estimates.iloc[0] == pytest.approx(350_000)
