# HDB Resale Price Estimator

Estimating fair resale prices of Singapore HDB flats so a buyer can judge
whether a listing's asking price is reasonable.

## Language

### Market

**Resale transaction**:
A completed resale of an HDB flat, registered with HDB. One row of the source data.
_Avoid_: Sale, deal, record

**Resale price**:
The price recorded in a resale transaction.
_Avoid_: Sale price, transaction price

**Registration month**:
The month a resale transaction was registered with HDB, weeks after the deal was agreed.
_Avoid_: Sale month, transaction date

**Listing**:
A flat currently advertised for resale, with an asking price.
_Avoid_: Ad, offer

**Asking price**:
The price a seller requests in a listing.
_Avoid_: List price

### Estimator output

**Estimate**:
The model's single best guess of a flat's resale price.
_Avoid_: Valuation (reserved for licensed valuers), prediction

**Price range**:
The interval expected to contain a stated share of resale prices for flats like the one entered.
_Avoid_: Confidence interval, error bars

**Verdict**:
Fair, high, or low: where a listing's asking price sits relative to its price range.
_Avoid_: Rating, score

### Data and validation

**Snapshot**:
A full, unmodified copy of the source dataset as downloaded on a given date.
_Avoid_: Dump, extract

**Backtest window**:
One step of the rolling backtest: train on all registration months up to T, test on month T+1.
_Avoid_: Fold, split
