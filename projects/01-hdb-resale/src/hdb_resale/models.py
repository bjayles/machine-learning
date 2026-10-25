"""Models: estimators that learn from all the drivers together.

HedonicRegression is a linear regression on the log of the resale price (EDA section
2): each characteristic multiplies the price by a factor, and each registration month
has its own level, so the month coefficients form a price index with the mix of flats
held constant (project ADR-0005). It follows the backtest's model interface.
"""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

# Each category gets one coefficient per value, against the first value as reference
CATEGORIES = ["month", "town", "flat_type", "flat_model_group", "storey_range"]

# Remaining lease in 5-year bands, so the model can draw the jumps the EDA found near
# 55 and 85 years (section 3) instead of one straight line
LEASE_EDGES = [0, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 100]


class HedonicRegression:
    """Linear regression of log price on the flat's characteristics and month levels.

    The test month is never in the training data, so it gets the latest training
    month's level: the market is assumed to stand where it stood last month.
    """

    def __init__(self, lease: str = "bands"):
        """Configure the model.

        Args:
            lease: "bands" gives each 5-year band of remaining lease its own level;
                "linear" gives each extra year the same percentage effect (one
                straight line on log price), to test whether the bands earn their place.
        """
        self.lease = lease

    def fit(self, train: pd.DataFrame) -> "HedonicRegression":
        """Learn each characteristic's effect and each training month's level."""
        self.latest_month_ = train["month"].max()
        encoder = OneHotEncoder(drop="first", handle_unknown="ignore")
        self.pipeline_ = Pipeline(
            [
                (
                    "features",
                    ColumnTransformer(
                        [
                            ("categories", encoder, self._categories()),
                            ("numbers", "passthrough", self._numbers()),
                        ]
                    ),
                ),
                ("regression", LinearRegression()),
            ]
        )
        self.pipeline_.fit(self._features(train), np.log(train["resale_price"]))
        return self

    def predict(self, test: pd.DataFrame) -> pd.Series:
        """Return estimates in S$, the test month carrying the latest month's level."""
        features = self._features(test)
        unseen = test["month"] > self.latest_month_
        features.loc[unseen, "month"] = str(self.latest_month_)
        return pd.Series(np.exp(self.pipeline_.predict(features)), index=test.index)

    def effects(self, feature: str) -> pd.Series:
        """Each value's price multiplier against the feature's reference value.

        exp(coefficient), all else equal: 1.25 means 25% above the reference (the
        first value, alphabetically or in time), which is 1.0 by construction.
        """
        names = self.pipeline_.named_steps["features"].get_feature_names_out()
        coefficients = pd.Series(
            self.pipeline_.named_steps["regression"].coef_, index=names
        )
        prefix = f"categories__{feature}_"
        levels = coefficients[coefficients.index.str.startswith(prefix)]
        levels.index = levels.index.str.removeprefix(prefix)

        encoder = self.pipeline_.named_steps["features"].named_transformers_[
            "categories"
        ]
        reference = encoder.categories_[self._categories().index(feature)][0]
        return np.exp(pd.concat([pd.Series({reference: 0.0}), levels]))

    def price_index(self) -> pd.Series:
        """Each training month's price level relative to the first, flats held fixed.

        1.10 means the same flat cost 10% more that month than in the first month.
        """
        index = self.effects("month")
        index.index = pd.PeriodIndex(index.index, freq="M")
        return index

    def _categories(self) -> list[str]:
        """The one-hot encoded features: lease bands are one of them, unless linear."""
        return [*CATEGORIES, "lease_band"] if self.lease == "bands" else CATEGORIES

    def _numbers(self) -> list[str]:
        """The features used as numbers."""
        if self.lease == "linear":
            return ["log_area", "remaining_lease_years"]
        return ["log_area"]

    @staticmethod
    def _features(sales: pd.DataFrame) -> pd.DataFrame:
        """The model's inputs: categories as text, floor area on a log scale."""
        features = sales[
            ["town", "flat_type", "flat_model_group", "storey_range"]
        ].copy()
        features["month"] = sales["month"].astype(str)
        features["remaining_lease_years"] = sales["remaining_lease_years"]
        features["lease_band"] = pd.cut(
            sales["remaining_lease_years"], LEASE_EDGES, right=False
        ).astype(str)
        # log-log: the coefficient is an elasticity (+1% area -> +b% price)
        features["log_area"] = np.log(sales["floor_area_sqm"])
        return features
