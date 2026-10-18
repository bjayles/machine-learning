"""Tests for `clean()`: a raw snapshot table goes in, a clean table comes out.

Each test builds a tiny raw table by hand, runs `clean()` on it, and checks one
cleaning rule from the EDA decision summary (notebooks/01-eda.ipynb, section 4).
Expected values are worked out by hand, never with the code's own logic.
"""

import pandas as pd
import pytest
from pandera.errors import SchemaErrors

from hdb_resale.clean import clean

# One valid raw resale transaction, as read from the snapshot (every value is text or
# a plain number, like `pd.read_csv` returns them)
VALID_ROW = {
    "month": "2017-01",
    "town": "ANG MO KIO",
    "flat_type": "2 ROOM",
    "block": "406",
    "street_name": "ANG MO KIO AVE 10",
    "storey_range": "10 TO 12",
    "floor_area_sqm": 44.0,
    "flat_model": "Improved",
    "lease_commence_date": 1979,
    "remaining_lease": "61 years 04 months",
    "resale_price": 232000.0,
}


def make_raw(*rows: dict) -> pd.DataFrame:
    """Raw table with one row per dict: each dict overrides some columns of VALID_ROW."""
    return pd.DataFrame([{**VALID_ROW, **row} for row in rows or [{}]])


# The three formats found in the snapshot, each with its value worked out by hand
@pytest.mark.parametrize(
    ("raw_lease", "expected_years"),
    [
        ("61 years 04 months", 61 + 4 / 12),
        ("62 years 01 month", 62 + 1 / 12),  # singular "month"
        ("47 years", 47.0),  # no months part
    ],
)
def test_remaining_lease_becomes_years(raw_lease, expected_years):
    raw = make_raw({"remaining_lease": raw_lease})

    cleaned = clean(raw)

    assert cleaned["remaining_lease_years"].iloc[0] == pytest.approx(expected_years)


def test_unknown_lease_format_fails_loudly():
    raw = make_raw({}, {"remaining_lease": "61 yrs"})

    # A format we don't recognise must stop the cleaning, naming the bad value
    with pytest.raises(SchemaErrors, match="61 yrs"):
        clean(raw)


@pytest.mark.parametrize(
    ("raw_storey", "expected_storey"),
    [
        ("10 TO 12", 11.0),
        ("01 TO 03", 2.0),  # leading zeros
    ],
)
def test_storey_range_becomes_middle_storey(raw_storey, expected_storey):
    raw = make_raw({"storey_range": raw_storey})

    cleaned = clean(raw)

    assert cleaned["storey_mid"].iloc[0] == expected_storey


def test_unknown_storey_format_fails_loudly():
    raw = make_raw({}, {"storey_range": "10-12"})

    with pytest.raises(SchemaErrors, match="10-12"):
        clean(raw)


def test_month_becomes_monthly_period():
    raw = make_raw({"month": "2024-07"})

    cleaned = clean(raw)

    assert cleaned["month"].iloc[0] == pd.Period("2024-07", freq="M")


def test_unknown_month_format_fails_loudly():
    raw = make_raw({}, {"month": "Jul 2024"})

    with pytest.raises(SchemaErrors, match="Jul 2024"):
        clean(raw)


def test_block_stays_text():
    # A number-only block must not become the integer 406: blocks are identifiers
    raw = make_raw({"block": 406})

    cleaned = clean(raw)

    assert cleaned["block"].iloc[0] == "406"


def test_missing_value_fails_loudly():
    raw = make_raw({}, {"town": None})

    # The snapshot has no missing values today; a future one with some must stop here
    with pytest.raises(SchemaErrors, match="town"):
        clean(raw)


@pytest.mark.parametrize(
    ("raw_model", "expected_group"),
    [
        ("Model A2", "Model A"),  # same design family, similar price
        ("Premium Maisonette", "Maisonette"),
        ("Type S2", "Type S"),
        ("3Gen", "Multi-generation"),
        ("DBSS", "DBSS"),  # distinct price level: its own group
    ],
)
def test_flat_model_is_grouped_into_families(raw_model, expected_group):
    raw = make_raw({"flat_model": raw_model})

    cleaned = clean(raw)

    assert cleaned["flat_model_group"].iloc[0] == expected_group


def test_unknown_flat_model_fails_loudly():
    # A new HDB model must be mapped to a group consciously, not guessed
    raw = make_raw({}, {"flat_model": "Model Z"})

    with pytest.raises(SchemaErrors, match="Model Z"):
        clean(raw)


def test_renamed_column_fails_loudly():
    # A schema change upstream (here "town" renamed) must stop the cleaning
    raw = make_raw().rename(columns={"town": "town_name"})

    with pytest.raises(SchemaErrors, match="town"):
        clean(raw)


def test_unexpected_column_fails_loudly():
    # A new column upstream must be reviewed before it reaches the model
    raw = make_raw().assign(latitude=1.37)

    with pytest.raises(SchemaErrors, match="latitude"):
        clean(raw)
