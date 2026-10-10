# Exercise 1: Home Value Estimation — California Housing

## Key results

- Final model: **Random Forest**, MAE 0.1556 (log scale) on held-out data — 39% better than the best linear model (0.2539), 66% better than the naive baseline.
- Residuals matched a Student-t distribution far better than Normal or Laplace (AIC 2373 vs. 2594 / 2549), the evidence base for the metric choice below.
- Two real data problems fixed before modeling (target censoring, a leverage point from extreme `AveRooms`/`AveBedrms` ratios): worst single error dropped from +9.88 to +3.66.
- Regularization added nothing (Ridge/Lasso/ElasticNet ≈ plain fit): genuine underfitting, not overfitting, confirmed by training error (0.2513) matching test error (0.2539).

## Key decisions

1. **Metric and model family, from one finding.** Residuals fit a Student-t distribution far better than Normal (AIC 2373 vs. 2594), meaning some neighborhoods are inherently harder to price than others, not uniform noise. That justified MAE in log space over RMSE, and later, once linear regression hit a hard ceiling, a decision tree specifically: a model built to fit different regions differently, not just the next technique on the list.
2. **Excluded mislabeled rows, not just outliers.** The target was capped at its max for 4.3% of rows, and a feature leverage point was driving the worst remaining errors; both fixed at the source (dropped from training, log-transformed) rather than patched with a more robust loss function.
3. **Multicollinearity fix used VIF, not assumption.** The obvious guess (`AveRooms`/`AveBedrms`, both ratios) was wrong; VIF pointed at `Latitude`/`Longitude` instead, an inherent, unfixable correlation rather than a redundancy to engineer away.
4. **Kept all 8 features despite 3 looking negligible.** p-values and an ablation test, not raw coefficient size, showed small but statistically real contributions, worth keeping over a simpler model.

## What I learned

- Tuning and comparing tree ensembles (Random Forest, Gradient Boosting) against regularized linear models via cross-validation.
- Fitting and comparing candidate residual distributions (AIC) to justify a metric choice, rather than defaulting to one.
- Diagnosing multicollinearity with VIF instead of assuming apparently obvious pairs.
- Separating statistical significance (p-values) from practical significance (effect size, ablation tests).


## Skills

Random Forest & Gradient Boosting · regularization (Ridge/Lasso/ElasticNet) · regression diagnostics (residual/distribution analysis) · hypothesis testing (p-values, paired t-test) · multicollinearity (VIF) · cross-validation · Python (pandas, scikit-learn, statsmodels)

[Full notebook →](notebook.ipynb)
