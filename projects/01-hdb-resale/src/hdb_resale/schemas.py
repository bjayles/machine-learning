"""Data contracts: what the raw snapshot and the cleaned table must look like.

Each schema (Pandera) declares the columns, their types, and the values they may
hold. `clean()` validates its input against RAW_SCHEMA and its output against
CLEAN_SCHEMA, so a snapshot that breaks a rule (a missing value, a new format, a
new flat model, a renamed column) stops the pipeline with every offending value
listed, instead of quietly producing a table that would bias the model later.
"""

import pandas as pd
import pandera.pandas as pa

# "61 years 04 months", "62 years 01 month" or "47 years": the months part is optional
LEASE_PATTERN = r"(?P<years>\d+) years?(?: (?P<months>\d+) months?)?"

# "10 TO 12": all bands are 3 storeys today; any width works, (3 + 4) / 2 = 3.5 is fine
STOREY_PATTERN = r"(?P<low>\d+) TO (?P<high>\d+)"

# "2024-07"
MONTH_PATTERN = r"\d{4}-\d{2}"

# Every flat model in the snapshot, mapped to a design family. Only similar designs with
# similar prices (vs comparable sales, EDA section 4) are merged; rare models with their
# own price level (DBSS, Type S, Terrace, 2-room) keep their own group
FLAT_MODEL_GROUPS = {
    "Model A": "Model A",
    "Model A2": "Model A",
    "Improved": "Improved",
    "New Generation": "New Generation",
    "Premium Apartment": "Premium Apartment",
    "Premium Apartment Loft": "Premium Apartment",
    "Simplified": "Simplified",
    "Apartment": "Apartment",
    "Maisonette": "Maisonette",
    "Model A-Maisonette": "Maisonette",
    "Improved-Maisonette": "Maisonette",
    "Premium Maisonette": "Maisonette",
    "Standard": "Standard",
    "DBSS": "DBSS",
    "2-room": "2-room",
    "Adjoined flat": "Adjoined flat",
    "Type S1": "Type S",
    "Type S2": "Type S",
    "Terrace": "Terrace",
    "Multi Generation": "Multi-generation",
    "3Gen": "Multi-generation",
}


def _text(pattern: str | None = None) -> pa.Column:
    """A required text column, optionally matching a whole-value regex pattern."""
    checks = [pa.Check.str_matches(f"^(?:{pattern})$")] if pattern else []
    return pa.Column(str, checks=checks)


# The snapshot as `pd.read_csv` reads it. Every column is required and never missing
# (Pandera's default), so a renamed column fails; strict=True also fails on a new one
RAW_SCHEMA = pa.DataFrameSchema(
    {
        "month": _text(MONTH_PATTERN),
        "town": _text(),
        "flat_type": _text(),
        "block": pa.Column(),  # identifier: may be read as text or number, clean() fixes
        "street_name": _text(),
        "storey_range": _text(STOREY_PATTERN),
        "floor_area_sqm": pa.Column(float, pa.Check.gt(0)),
        "flat_model": pa.Column(str, pa.Check.isin(list(FLAT_MODEL_GROUPS))),
        "lease_commence_date": pa.Column(int),
        "remaining_lease": _text(LEASE_PATTERN),
        "resale_price": pa.Column(float, pa.Check.gt(0)),
    },
    strict=True,
)

# The cleaned table: raw columns with fixed types, plus the derived columns
CLEAN_SCHEMA = RAW_SCHEMA.update_columns(
    {
        "month": {"dtype": pd.PeriodDtype("M"), "checks": []},
        "block": {"dtype": str},
    }
).add_columns(
    {
        "remaining_lease_years": pa.Column(float, pa.Check.in_range(0, 99)),
        "storey_mid": pa.Column(float, pa.Check.ge(1)),
        "flat_model_group": pa.Column(
            str, pa.Check.isin(sorted(set(FLAT_MODEL_GROUPS.values())))
        ),
    }
)
