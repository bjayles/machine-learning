# Rolling backtest, not random splits

A buyer uses past resale prices to judge a listing today, and HDB prices
trend strongly over time. A random split or K-fold would train on months
after the ones it tests on, leaking the future and flattering the score. We
validate with a rolling backtest with an expanding window: train on all
months up to T, test on T+1, then advance T, over about 12 monthly test
windows. The current, still-filling registration month is excluded. This
mirrors production exactly, where the model is retrained each month and
used on the next.

## Considered Options

- **Single time holdout.** Rejected: one score from one period, with no view
  of how stable performance is from month to month.

## Update (step 2)

The training window doesn't have to expand. Its length became a setting of each model, chosen on a validation period (the 12 months before the test period): sliding windows won for every model, even with month levels in the model, because the effects themselves drift over time (notebooks/02-baselines.ipynb, 03-first-model.ipynb, 04-residuals.ipynb). The rest stands: always train on the past only and test on the next month.
