"""Command-line entry point: the `hdb-resale` command you type in the terminal.

`pyproject.toml` ([project.scripts]) maps the `hdb-resale` command to `main()` below,
so `uv run hdb-resale <subcommand>` ends up here. This file only reads what was typed
(which subcommand, which options) and calls the matching function elsewhere in the
package; it contains no project logic itself.

Subcommands:
    ingest    Download a full snapshot of the resale dataset (see ingest.py).
    clean     Clean the raw snapshot into data/interim (see clean.py).

Run `uv run hdb-resale --help` (or `... ingest --help`) to list them and their options.
"""

import argparse
from pathlib import Path

import pandas as pd

from hdb_resale.clean import clean
from hdb_resale.ingest import ingest


def main() -> None:
    """Parse the subcommand and its options, then run the matching function."""
    parser = argparse.ArgumentParser(
        prog="hdb-resale", description="HDB resale price estimator."
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    # hdb-resale ingest
    ingest_parser = subcommands.add_parser(
        "ingest", help="Download a full snapshot of the resale dataset."
    )
    ingest_parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/raw"),
        help="Where to write the snapshot (default: data/raw, relative to where you run the command).",
    )

    # hdb-resale clean
    clean_parser = subcommands.add_parser(
        "clean", help="Clean the raw snapshot into a typed table."
    )
    clean_parser.add_argument(
        "--raw",
        type=Path,
        default=Path("data/raw/resale.csv"),
        help="Raw snapshot to read (default: data/raw/resale.csv).",
    )
    clean_parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/interim/resale.parquet"),
        help="Where to write the cleaned table (default: data/interim/resale.parquet).",
    )

    args = parser.parse_args()

    if args.command == "ingest":
        metadata = ingest(args.out_dir)
        print(f"Saved {metadata['rows']:,} rows to {args.out_dir / metadata['file']}")

    if args.command == "clean":
        # Parquet keeps the types clean() sets (monthly periods, text blocks)
        cleaned = clean(pd.read_csv(args.raw, dtype={"block": str}))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        cleaned.to_parquet(args.out, index=False)
        print(f"Saved {len(cleaned):,} cleaned rows to {args.out}")
