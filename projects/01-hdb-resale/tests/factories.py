"""Test data builders shared by the test files: small, valid tables to start from."""

import pandas as pd

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


def make_clean(months: list[str], rows_per_month: int = 2) -> pd.DataFrame:
    """Cleaned table with `rows_per_month` valid transactions in each registration month."""
    return clean(
        make_raw(*[{"month": m} for m in months for _ in range(rows_per_month)])
    )
