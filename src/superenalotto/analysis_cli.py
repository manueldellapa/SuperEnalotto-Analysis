"""Read-only command-line analysis of the canonical extraction dataset."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from .analysis import Category, FrequencyReport, calculate_frequencies
from .paths import DataPaths
from .pipeline import load_extractions_csv


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the base analysis command (whole dataset, numeric order)."""
    parser = argparse.ArgumentParser(
        prog="superenalotto-analyze",
        description="Describe historical frequencies in the canonical CSV, offline.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        help="Data root; defaults to checkout data/ or ./data when installed.",
    )
    parser.add_argument(
        "--category",
        choices=("main", "jolly", "superstar"),
        default="main",
        help="Number category to count. Default: main.",
    )
    return parser


def format_report(report: FrequencyReport, source: Path) -> str:
    """Render metadata and round percentages only for presentation."""
    first = report.first_date.isoformat() if report.first_date else "N/A"
    last = report.last_date.isoformat() if report.last_date else "N/A"
    lines = [
        f"Source: {source}",
        f"Category: {report.category}",
        "Requested start: unbounded",
        "Requested end: unbounded",
        f"Source dates: {first} .. {last}",
        f"Selected dates: {first} .. {last}",
        f"N = {report.extraction_count}",
        "Historical coverage is not certified: continuity, completeness and "
        "freshness cannot be inferred from the CSV.",
        "Statistics are descriptive, not predictions.",
        "presence_percent = 100 * count / N (contests, not drawn balls).",
    ]
    if not report.extraction_count:
        lines.append("No extractions in selected period")
    lines.append("number count presence_percent")
    for row in report.frequencies:
        percent = (
            "N/A" if row.presence_percent is None else f"{row.presence_percent:.2f}"
        )
        lines.append(f"{row.number} {row.count} {percent}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Print a complete report or an expected error without partial stdout."""
    args = build_argument_parser().parse_args(argv)
    paths = (
        DataPaths.default()
        if args.data_dir is None
        else DataPaths.from_root(args.data_dir)
    )
    try:
        extractions = load_extractions_csv(paths=paths)
        report = calculate_frequencies(extractions, cast(Category, args.category))
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(format_report(report, paths.extractions_csv))
    return 0
