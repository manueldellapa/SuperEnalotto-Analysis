"""Command-line interface for the SuperEnalotto extraction downloader.

Registered as the ``superenalotto-download`` console script. All orchestration
lives in pipeline.py; this module only parses arguments, resolves defaults and
maps outcomes onto exit codes.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from .paths import DataPaths, default_data_directory
from .pipeline import (
    ExtractionConflictError,
    count_csv_rows,
    download_interval,
    remove_partial_extractions_csv,
    save_extractions_csv,
)

LOGGER = logging.getLogger(__name__)


def configure_logging(verbose: bool = False) -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="superenalotto-download",
        description=("Download and process historical SuperEnalotto extractions."),
    )

    parser.add_argument(
        "--start-year",
        type=int,
        required=True,
        help="First year to download.",
    )

    parser.add_argument(
        "--start-month",
        type=int,
        default=1,
        help="First month to download (1-12). Default: 1.",
    )

    parser.add_argument(
        "--end-year",
        type=int,
        help=("Last year to download. Defaults to --start-year."),
    )

    parser.add_argument(
        "--end-month",
        type=int,
        help=(
            "Last month to download. "
            "Defaults to --start-month when "
            "--end-year is omitted, to the current month when "
            "--end-year is the current year, otherwise 12."
        ),
    )

    parser.add_argument(
        "--data-dir",
        type=Path,
        help=(
            "Root directory for cached archive pages and generated datasets; "
            "raw/ and processed/ are created underneath it. Defaults to the "
            "data directory of the source checkout when running from one, "
            "otherwise ./data."
        ),
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download raw HTML files even if already cached.",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )

    return parser


def resolve_interval(
    args: argparse.Namespace,
) -> tuple[int, int, int, int]:
    """Resolve CLI arguments into a complete interval."""
    start_year: int = args.start_year
    start_month: int = args.start_month

    end_year: int = args.end_year if args.end_year is not None else start_year

    today = date.today()

    if args.end_month is not None:
        end_month = args.end_month
    elif args.end_year is None:
        end_month = start_month
    elif end_year == today.year:
        end_month = today.month
    else:
        end_month = 12

    return (
        start_year,
        start_month,
        end_year,
        end_month,
    )


def resolve_data_paths(
    args: argparse.Namespace,
) -> DataPaths:
    """Resolve CLI arguments into the filesystem layout for this run."""
    data_dir: Path | None = args.data_dir

    if data_dir is None:
        data_dir = default_data_directory()

    return DataPaths.from_root(data_dir)


def main(
    argv: Sequence[str] | None = None,
) -> int:
    """Run the command-line downloader."""
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    configure_logging(
        verbose=args.verbose,
    )

    (
        start_year,
        start_month,
        end_year,
        end_month,
    ) = resolve_interval(args)

    paths = resolve_data_paths(args)

    canonical_path = paths.extractions_csv
    partial_path = paths.partial_extractions_csv

    LOGGER.info(
        "Using data directory: %s",
        paths.root,
    )

    try:
        extractions, failures = download_interval(
            start_year,
            start_month,
            end_year,
            end_month,
            paths=paths,
            force=args.force,
        )
    except ExtractionConflictError as exc:
        LOGGER.error(
            "Data integrity error: %s",
            exc,
        )

        LOGGER.error(
            "No CSV written; %s left untouched",
            canonical_path,
        )

        return 1
    except ValueError as exc:
        LOGGER.error(
            "%s",
            exc,
        )

        return 1
    except Exception:
        LOGGER.exception("Unexpected error while downloading extractions")

        return 1

    if failures:
        save_extractions_csv(
            extractions,
            output_path=partial_path,
        )

        existing_row_count = count_csv_rows(canonical_path)

        if existing_row_count is None:
            LOGGER.warning(
                "Left %s unwritten because %d month(s) failed; "
                "partial results (%d row(s)) saved to %s",
                canonical_path,
                len(failures),
                len(extractions),
                partial_path,
            )
        else:
            LOGGER.warning(
                "Preserved %s (%d row(s)) because %d month(s) failed; "
                "partial results (%d row(s)) saved to %s",
                canonical_path,
                existing_row_count,
                len(failures),
                len(extractions),
                partial_path,
            )

        LOGGER.error(
            "Completed with %d failed month(s)",
            len(failures),
        )

        for year, month, error in failures:
            LOGGER.error(
                "Failed archive: %04d-%02d | %s",
                year,
                month,
                error,
            )

        return 1

    save_extractions_csv(
        extractions,
        output_path=canonical_path,
    )

    remove_partial_extractions_csv(partial_path)

    LOGGER.info(
        "Completed successfully: %d extraction(s)",
        len(extractions),
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
