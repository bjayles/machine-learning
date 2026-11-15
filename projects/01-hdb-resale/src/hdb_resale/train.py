"""Training: fit the model to ship, on the latest complete months.

The backtest measures a recipe and throws its fitted models away; this fits the same
recipe once, on the most recent data, for the demo to serve. It trains like the next
backtest window would: the current registration month, still filling up, is the one
being estimated, so it's never learned from.
"""

import pandas as pd

from hdb_resale.backtest import Model, training_window
from hdb_resale.schemas import CLEAN_SCHEMA


def train(data: pd.DataFrame, model: Model, train_months: int | None = None) -> Model:
    """Fit `model` on the latest complete months and return it.

    Args:
        data: The cleaned table (must match CLEAN_SCHEMA).
        model: The recipe to fit, with the settings chosen on the validation period.
        train_months: As in `backtest()`: the N latest complete months, or all.

    Returns:
        The fitted model.
    """
    data = CLEAN_SCHEMA.validate(data)
    current_month = data["month"].max()
    model.fit(training_window(data, current_month, train_months))
    return model
