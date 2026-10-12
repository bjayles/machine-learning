# HDB Resale Price Estimator

**Status:** step 0 (framing) complete. No code yet.

An estimator of fair resale prices for Singapore HDB flats, built as a
production-standard ML project: versioned data, a reproducible pipeline,
experiment tracking, tests, CI with a model-quality gate, a live demo, and
monthly retraining.

> Not affiliated with or endorsed by the Housing & Development Board (HDB)
> or any Singapore government agency. Estimates are statistical, not
> valuations, and not financial advice.

## Brief

### User and decision

A **buyer sanity-checking a specific listing**: "this 4-room in Tampines is
asking S$650k; is that fair?" The buyer enters what the listing says (town,
flat type, storey range, floor area, lease), and gets back an **estimate**
plus a **price range**. Comparing the asking price to that range gives a
**verdict**: fair, high, or low.

That framing drives the choices below: the buyer judges today's listing from
past sales (so validation must respect time), and thinks in "% above fair
value" (so relative error matters as much as dollars).

### Data

[Resale flat prices based on registration date from Jan-2017 onwards](https://data.gov.sg/datasets/d_8b84c4ee58e3cfc0ece0d773c8ca6abc/view),
published by HDB on data.gov.sg. About 242k resale transactions (Jan 2017
onward), refreshed at least monthly, downloadable in full via the public API
with no key required.

- **2017+ only.** Older datasets (1990-2016) have different schemas and,
  before March 2012, a different date basis. They're added only if the
  backtest shows a need.
- **Registration lag.** Transactions appear when registered, weeks after the
  deal. The current month is always incomplete and is excluded from
  training and evaluation.
- **No coordinates.** Location is town, block, and street only. Geocoding
  (OneMap) is considered in step 2, only if errors show town-level location
  isn't enough.

### Evaluation

Both a **relative** error (%) and an **absolute** error (S$) are reported.
Which one is primary, and its exact form (log-space MAE, MAPE, MdAPE), is
decided in step 2 from the residual analysis. Once price ranges exist, their
**coverage** (share of real resale prices that land inside the range) is
tracked too.

### Validation

A **rolling backtest with an expanding window**: train on the full history
up to month T, test on month T+1, then move T forward one month and repeat,
over about 12 monthly test windows. The training set grows each time; it
never drops old months.

```
Window 1:  train [2017-01 ... 2025-09]  test 2025-10
Window 2:  train [2017-01 ... 2025-10]  test 2025-11
...
Window 12: train [2017-01 ... 2026-08]  test 2026-09
```

Repeating gives 12 scores instead of one: their average is more reliable
than a single noisy month, and their spread and trend show whether
performance is stable or drifting. This mirrors production, where the model
is retrained monthly and used on the following month. See
[ADR-0001](docs/adr/0001-rolling-backtest.md).

## Roadmap

| Step | Scope |
|---|---|
| 0 | Framing (this brief, ADRs) |
| 1 | Ingestion + DVC data versioning |
| 2 | Baseline + time-based validation |
| 3 | DVC pipeline + MLflow tracking |
| 4 | Packaging + tests |
| 5 | CI with a model-quality gate |
| 6 | FastAPI + live demo |
| 7 | Monitoring + monthly retraining |

### Decisions deferred, and when they're made

| Decision | Step |
|---|---|
| DVC remote provider (Cloudflare R2 vs AWS S3) | 1 |
| Primary metric and the "good enough" threshold | 2 |
| Geocoding via OneMap (separate terms and account) | 2 |
| MLflow hosting | 3 |
| Demo name, input granularity, disclaimer wording, final legal check | 6 |
| Keeping the monthly schedule running long term | 7 |

## Decisions

- [ADR-0001](docs/adr/0001-rolling-backtest.md): rolling backtest, not random splits
- [ADR-0002](docs/adr/0002-full-raw-snapshots.md): raw data is a full, immutable snapshot
- [ADR-0003](docs/adr/0003-private-dvc-remote.md): the DVC remote is private

Repo-wide conventions (independent package, shared data bucket) are in the
root [ADR-0001](../../docs/adr/0001-monorepo-conventions.md).

## Data licence and attribution

Contains information from *Resale flat prices based on registration date
from Jan-2017 onwards* accessed on 2026-10-10 from data.gov.sg (Housing &
Development Board), which is made available under the terms of the
[Singapore Open Data Licence version 1.0](https://data.gov.sg/open-data-licence).

The access date is updated with each data snapshot. The code is not
licensed for reuse: all rights reserved (see the repo root `LICENSE`). That
notice covers the code, not the data.
