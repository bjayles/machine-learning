# Log-space MAE as the primary metric, and the "good enough" threshold

The primary metric, which chooses between models and will gate them in CI, is the **log-space MAE**: the mean of |log(estimate / resale price)| over a backtest window, averaged over the windows. It counts every error (unlike MdAPE, which ignores the worse half), treats 10% too high like 10% too low (unlike MAPE, which penalises over-estimates more and so nudges models to under-estimate), and matches the model's log-price target; at our error levels it reads as an average % error. Humans get MdAPE and the 90th percentile of the % error ("half within 3%, 9 in 10 within 8%"), plus the MAE in S$.

A model is **good enough** to deploy when, over the backtest windows: its log-space MAE is at most **half the reference baseline's** (the town + flat type median), so it's clearly worth its complexity; its log-space MAE is at most **0.05**; **9 in 10** estimates fall within **10%**, so a listing priced 10% above its flats' value can be told apart; and its average signed log error (bias) is within **±1%**, so verdicts aren't tilted one way. The anchors are the noise floor (flats in the same block and year spread about ±3%, EDA section 3) and what a verdict needs. `backtest.good_enough()` checks the four conditions (notebooks/04-residuals.ipynb).

## Considered Options

- **MdAPE as primary.** The most intuitive, but blind to the tail: a model making the worst-estimated tenth much worse would score the same.
- **MAPE.** Asymmetric, as above.
- **MAE in S$.** Dominated by expensive flats, while buyers think in %.

## Consequences

The CI gate (step 5) will also need a tolerance for retrained models; the window-to-window spread of the log-space MAE (about 0.001) suggests allowing 0.002.
