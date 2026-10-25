"""Naive baselines: simple estimates every real model must clearly beat.

They follow the backtest's model interface (`fit(train)`, `predict(test)`), so they go
through exactly the same backtest windows as real models.

- OverallMedian: every flat is worth the median training price. The floor.
- TownFlatTypeMedian: the median of recent sales of the same town and flat type, what
  a buyer can already look up (HDB publishes medians by town and flat type). With
  `per_sqm=True`, the median price per m² times the flat's floor area.
"""

import pandas as pd


class OverallMedian:
    """Estimate every flat at the median resale price of the training sales."""

    def fit(self, train: pd.DataFrame) -> "OverallMedian":
        """Learn the median training price."""
        self.median_ = train["resale_price"].median()
        return self

    def predict(self, test: pd.DataFrame) -> pd.Series:
        """Return the same estimate for every test transaction."""
        return pd.Series(self.median_, index=test.index)


class TownFlatTypeMedian:
    """Estimate a flat at the median of recent sales of the same town and flat type.

    A group with no recent sale falls back to the same flat type in any town, then to
    all recent sales, so every flat gets an estimate.
    """

    def __init__(self, recent_months: int = 12, per_sqm: bool = False):
        """Configure the baseline.

        Args:
            recent_months: Only the latest N months of training sales are used, since
                prices trend over time (EDA section 2).
            per_sqm: Take medians of the price per m², then multiply by the flat's
                floor area, instead of medians of the price.
        """
        self.recent_months = recent_months
        self.per_sqm = per_sqm

    def fit(self, train: pd.DataFrame) -> "TownFlatTypeMedian":
        """Learn the medians of each group, from the most to the least specific."""
        latest = train["month"].max()
        recent = train[train["month"] > latest - self.recent_months]
        value = self._value(recent)

        self.by_town_type_ = value.groupby(
            [recent["town"], recent["flat_type"]]
        ).median()
        self.by_type_ = value.groupby(recent["flat_type"]).median()
        self.overall_ = value.median()
        return self

    def predict(self, test: pd.DataFrame) -> pd.Series:
        """Return each flat's group median, falling back when its group is empty."""
        town_type = pd.MultiIndex.from_frame(test[["town", "flat_type"]])
        median = pd.Series(
            self.by_town_type_.reindex(town_type).to_numpy(), index=test.index
        )
        median = median.fillna(test["flat_type"].map(self.by_type_))
        median = median.fillna(self.overall_)

        return median * test["floor_area_sqm"] if self.per_sqm else median

    def _value(self, sales: pd.DataFrame) -> pd.Series:
        """The quantity whose median is taken: price, or price per m²."""
        if self.per_sqm:
            return sales["resale_price"] / sales["floor_area_sqm"]
        return sales["resale_price"]
