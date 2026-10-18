"""Cleaning: turn the raw snapshot into a typed, model-ready table.

Input: the raw snapshot table, exactly as `pd.read_csv` reads data/raw/resale.csv.
Output: the same rows and columns, with `month` as a monthly period and `block` as
text, plus numeric versions of the text columns (`remaining_lease_years`,
`storey_mid`) and `flat_model_group`. Each rule comes from the EDA decision summary
(notebooks/01-eda.ipynb, section 4).

Both ends are checked against the data contracts in schemas.py: the input must match
RAW_SCHEMA and the output CLEAN_SCHEMA, so any missing value or unknown format stops
the cleaning (a `pandera.errors.SchemaErrors` listing every offending value).
"""

import pandas as pd

from hdb_resale.schemas import (
    CLEAN_SCHEMA,
    FLAT_MODEL_GROUPS,
    LEASE_PATTERN,
    RAW_SCHEMA,
    STOREY_PATTERN,
)


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    """Return a cleaned copy of the raw snapshot table."""
    # lazy=True collects every failure before stopping, instead of the first one only
    cleaned = RAW_SCHEMA.validate(raw, lazy=True).copy()

    # Registration month as a monthly period ("2024-07" -> Period('2024-07', 'M'))
    cleaned["month"] = pd.PeriodIndex(cleaned["month"], freq="M")

    # Block is an identifier ("406", "406A"), never a number
    cleaned["block"] = cleaned["block"].astype(str)

    # Remaining lease as a number of years: years + months / 12 (no months part = 0)
    lease = cleaned["remaining_lease"].str.extract(LEASE_PATTERN).astype(float)
    cleaned["remaining_lease_years"] = lease["years"] + lease["months"].fillna(0) / 12

    # Storey range as its middle storey ("10 TO 12" -> 11)
    storey = cleaned["storey_range"].str.extract(STOREY_PATTERN).astype(float)
    cleaned["storey_mid"] = (storey["low"] + storey["high"]) / 2

    # Flat model grouped into design families (21 models -> 14 groups)
    cleaned["flat_model_group"] = cleaned["flat_model"].map(FLAT_MODEL_GROUPS)

    return CLEAN_SCHEMA.validate(cleaned, lazy=True)
