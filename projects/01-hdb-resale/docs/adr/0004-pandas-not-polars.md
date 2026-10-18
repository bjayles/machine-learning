# pandas for dataframes, with Pandera data contracts

The data is small (about 240k resale transactions, 24 MB of CSV, growing by about 2k a month), so Polars' speed would buy nothing here: `clean()` runs on the full snapshot in about a second. What matters more is compatibility with the rest of the stack. scikit-learn, matplotlib and seaborn take pandas tables natively, and the EDA notebook already uses pandas. Polars would add conversions at every boundary, costing clarity for no gain. We use pandas throughout, and Pandera schemas (`schemas.py`) as the data contracts for the raw snapshot and the cleaned table. Pandera supports both libraries, so it doesn't tie the choice either way.

## Considered Options

- **Polars.** Faster and stricter about types, and the better choice for data in the millions of rows or more. Worth revisiting if the dataset grows by orders of magnitude (e.g. adding the 1990–2016 history plus geocoded features), or for a future project with genuinely large data.
