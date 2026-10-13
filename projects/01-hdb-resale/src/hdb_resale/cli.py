"""Command-line entry point: the `hdb-resale` command you type in the terminal.

`pyproject.toml` ([project.scripts]) maps the `hdb-resale` command to `main()` below,
so `uv run hdb-resale <subcommand>` ends up here. This file only reads what was typed
(which subcommand, which options) and calls the matching function elsewhere in the
package; it contains no project logic itself.

Subcommands:
    ingest    Download a full snapshot of the resale dataset (see ingest.py).

Run `uv run hdb-resale --help` (or `... ingest --help`) to list them and their options.
"""

import argparse
from pathlib import Path

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

    args = parser.parse_args()

    if args.command == "ingest":
        metadata = ingest(args.out_dir)
        print(f"Saved {metadata['rows']:,} rows to {args.out_dir / metadata['file']}")
