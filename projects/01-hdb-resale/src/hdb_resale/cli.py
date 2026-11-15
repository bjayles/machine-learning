"""Command-line entry point: the `hdb-resale` command you type in the terminal.

`pyproject.toml` ([project.scripts]) maps the `hdb-resale` command to `main()` below,
so `uv run hdb-resale <subcommand>` ends up here. This file only reads what was typed
(which subcommand, which options) and calls the matching function elsewhere in the
package; it contains no project logic itself.

Subcommands (all but `ingest` are pipeline stages, run by `dvc repro`, see dvc.yaml):
    ingest    Download a full snapshot of the resale dataset (see ingest.py).
    clean     Clean the raw snapshot into data/interim (see clean.py).
    baseline  Backtest the reference baseline on both periods (see backtest.py).
    backtest  Backtest the model on both periods (see backtest.py).
    evaluate  Score both backtests and check the good-enough threshold (see evaluate.py).
    train     Fit the model to ship on the latest complete months (see train.py).

Settings (the model's, the baseline's, the backtest's) come from params.yaml.

Run `uv run hdb-resale --help` (or `... ingest --help`) to list them and their options.
"""

import argparse
import json
import pickle
from pathlib import Path

import pandas as pd
import yaml

from hdb_resale.backtest import backtest_periods
from hdb_resale.baselines import TownFlatTypeMedian
from hdb_resale.clean import clean
from hdb_resale.evaluate import evaluate
from hdb_resale.ingest import ingest
from hdb_resale.models import HedonicRegression
from hdb_resale.train import train

CLEANED = Path("data/interim/resale.parquet")
MODEL_PREDICTIONS = Path("data/predictions/model.parquet")
BASELINE_PREDICTIONS = Path("data/predictions/baseline.parquet")


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

    # The pipeline stages: fixed paths (dvc.yaml lists them), settings from params.yaml
    for name, help_text in [
        ("baseline", "Backtest the reference baseline on both periods."),
        ("backtest", "Backtest the model on both periods."),
        ("evaluate", "Score both backtests and check the good-enough threshold."),
        ("train", "Fit the model to ship on the latest complete months."),
    ]:
        stage_parser = subcommands.add_parser(name, help=help_text)
        stage_parser.add_argument(
            "--params",
            type=Path,
            default=Path("params.yaml"),
            help="Settings file (default: params.yaml).",
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

    if args.command in {"baseline", "backtest", "train"}:
        params = yaml.safe_load(args.params.read_text())
        cleaned = pd.read_parquet(CLEANED)
        model_params = dict(params["model"])
        train_months = model_params.pop("train_months")

    if args.command == "baseline":
        baseline = TownFlatTypeMedian(**params["baseline"])
        predictions = backtest_periods(cleaned, baseline, **params["backtest"])
        _save_parquet(predictions, BASELINE_PREDICTIONS)

    if args.command == "backtest":
        predictions = backtest_periods(
            cleaned,
            HedonicRegression(**model_params),
            train_months=train_months,
            **params["backtest"],
        )
        _save_parquet(predictions, MODEL_PREDICTIONS)

    if args.command == "evaluate":
        windows, summary = evaluate(
            pd.read_parquet(MODEL_PREDICTIONS), pd.read_parquet(BASELINE_PREDICTIONS)
        )
        Path("metrics").mkdir(exist_ok=True)
        windows.to_csv("metrics/windows.csv", index=False)
        Path("metrics/summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary["model"], indent=2))
        print(f"Good enough on the test period: {summary['good_enough']['all']}")

    if args.command == "train":
        model = train(cleaned, HedonicRegression(**model_params), train_months)
        Path("models").mkdir(exist_ok=True)
        with open("models/model.pkl", "wb") as f:
            pickle.dump(model, f)
        print(
            f"Saved the model, trained up to {model.latest_month_}, to models/model.pkl"
        )


def _save_parquet(predictions: pd.DataFrame, path: Path) -> None:
    """Write a backtest's estimates, creating the folder if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_parquet(path, index=False)
    print(f"Saved {len(predictions):,} estimates to {path}")
