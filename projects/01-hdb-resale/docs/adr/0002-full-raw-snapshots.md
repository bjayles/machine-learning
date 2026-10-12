# Raw data is a full, immutable snapshot

Transactions are published by registration date, so past months keep
filling in for weeks after they end (and may be corrected). Fetching only
new months would freeze those months at their incomplete state. Each
ingestion therefore downloads the full dataset (about 24 MB) and stores it
unchanged as a new DVC-versioned snapshot; all cleaning happens in later
pipeline stages. Every version is kept, so any past model can be retrained
on exactly the data it saw, and comparing snapshots shows whether HDB revises
past months.

## Considered Options

- **Append only new months.** Rejected: misses late registrations and
  corrections, and needs merge logic that can silently go wrong.
