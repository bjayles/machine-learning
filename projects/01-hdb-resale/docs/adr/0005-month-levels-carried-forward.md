# Time as month levels, the latest carried forward

Resale prices don't follow a straight line (flat 2017–2019, about +50% to 2025, then a plateau), and the model always estimates a month it has never seen. We model time as a hedonic regression with time effects: one coefficient per registration month in the training data, so each month's level is measured with the mix of flats held constant, and the test month gets the latest training month's level. The bet is that the market moves little in one month, which holds against our error level (about 5%). As a by-product, the month coefficients form a price index; it tracks HDB's official Resale Price Index with a correlation of 0.9999 (notebooks/03-first-model.ipynb), which confirms they measure the market.

## Considered Options

- **Month as a plain category.** The test month has no coefficient, since it never appears in training.
- **A linear time trend.** One slope can't fit flat, rising and plateau phases, and it extrapolates the 2020–2025 rise into the current plateau.

## Consequences

The model lags turning points by a month. If the residual analysis shows a systematic lag, the carried-forward level can be adjusted with the recent trend.
