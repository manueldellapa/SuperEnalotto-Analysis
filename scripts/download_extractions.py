"""Download and process historical SuperEnalotto extractions."""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from collections.abc import Iterable
from datetime import date
from pathlib import Path

import requests

from superenalotto.constants import (
    EXTRACTIONS_FILE_NAME,
    MIN_ARCHIVE_YEAR,
    MONTH_NUMBER_TO_NAME,
    PARTIAL_EXTRACTIONS_FILE_NAME,
    PROCESSED_DATA_DIRECTORY,
    RAW_DATA_DIRECTORY,
    RAW_FILE_NAME_TEMPLATE,
)
from superenalotto.models import Extraction
from superenalotto.scraper import (
    ScrapingError,
    create_http_session,
    download_archive_page,
    parse_archive_page,
)

LOGGER = logging.getLogger(__name__)


def configure_logging(verbose: bool = False) -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def build_raw_file_path(year: int, month: int) -> Path:
    """Return the raw HTML file path for a given year and month."""
    filename = RAW_FILE_NAME_TEMPLATE.format(
        year=year,
        month=month,
    )

    return RAW_DATA_DIRECTORY / filename


def save_raw_html(
    html: str,
    *,
    year: int,
    month: int,
) -> Path:
    """Save raw archive HTML to disk."""
    RAW_DATA_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = build_raw_file_path(
        year,
        month,
    )

    temp_path = path.with_name(path.name + ".tmp")

    temp_path.write_text(
        html,
        encoding="utf-8",
    )

    temp_path.replace(path)

    return path


def load_raw_html(
    year: int,
    month: int,
) -> str:
    """Load previously downloaded raw archive HTML."""
    path = build_raw_file_path(
        year,
        month,
    )

    return path.read_text(
        encoding="utf-8",
    )


def download_month(
    year: int,
    month: int,
    *,
    session: requests.Session,
    force: bool = False,
) -> Path:
    """Download and persist one monthly archive page.

    Existing files are reused unless force is enabled.
    """
    path = build_raw_file_path(
        year,
        month,
    )

    month_name = MONTH_NUMBER_TO_NAME[month]

    if path.exists() and not force:
        LOGGER.info(
            "Using cached archive: %04d-%02d (%s)",
            year,
            month,
            month_name,
        )

        return path

    LOGGER.info(
        "Downloading archive: %04d-%02d (%s)",
        year,
        month,
        month_name,
    )

    html = download_archive_page(
        year,
        month,
        session=session,
    )

    path = save_raw_html(
        html,
        year=year,
        month=month,
    )

    LOGGER.info(
        "Saved raw archive: %s",
        path,
    )

    return path


def process_month(
    year: int,
    month: int,
    *,
    session: requests.Session,
    force: bool = False,
) -> list[Extraction]:
    """Download, cache and parse one monthly archive."""
    path = download_month(
        year,
        month,
        session=session,
        force=force,
    )

    html = path.read_text(
        encoding="utf-8",
    )

    extractions = parse_archive_page(
        html,
    )

    for extraction in extractions:
        if (
            extraction.extraction_date.year,
            extraction.extraction_date.month,
        ) != (year, month):
            raise ScrapingError(
                f"Contest {extraction.contest_number}: extraction date "
                f"{extraction.extraction_date.isoformat()} is outside requested "
                f"{year:04d}-{month:02d}"
            )

    LOGGER.info(
        "Parsed %d extraction(s) from %04d-%02d",
        len(extractions),
        year,
        month,
    )

    return extractions


def deduplicate_extractions(
    extractions: Iterable[Extraction],
) -> list[Extraction]:
    """Remove duplicated extractions and sort chronologically."""
    unique: dict[
        tuple[int, date],
        Extraction,
    ] = {}

    dates_by_contest: dict[int, date] = {}

    for extraction in extractions:
        previous_date = dates_by_contest.get(extraction.contest_number)

        if previous_date is not None and previous_date != extraction.extraction_date:
            LOGGER.warning(
                "Contest %d has conflicting dates: %s and %s",
                extraction.contest_number,
                previous_date.isoformat(),
                extraction.extraction_date.isoformat(),
            )

        dates_by_contest[extraction.contest_number] = extraction.extraction_date

        key = (
            extraction.contest_number,
            extraction.extraction_date,
        )

        unique[key] = extraction

    return sorted(
        unique.values(),
        key=lambda extraction: (
            extraction.extraction_date,
            extraction.contest_number,
        ),
    )


def save_extractions_csv(
    extractions: Iterable[Extraction],
    *,
    output_path: Path | None = None,
) -> Path:
    """Save extractions to a CSV file."""
    if output_path is None:
        output_path = PROCESSED_DATA_DIRECTORY / EXTRACTIONS_FILE_NAME

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    rows = [extraction.as_dict() for extraction in extractions]

    temp_path = output_path.with_name(output_path.name + ".tmp")

    with temp_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=Extraction.CSV_FIELDNAMES,
        )

        writer.writeheader()
        writer.writerows(rows)

    temp_path.replace(output_path)

    LOGGER.info(
        "Saved %d extraction(s) to %s",
        len(rows),
        output_path,
    )

    return output_path


def iter_year_months(
    start_year: int,
    start_month: int,
    end_year: int,
    end_month: int,
) -> Iterable[tuple[int, int]]:
    """Yield every year/month pair in an inclusive interval."""
    current_year = start_year
    current_month = start_month

    while (
        current_year,
        current_month,
    ) <= (
        end_year,
        end_month,
    ):
        yield current_year, current_month

        if current_month == 12:
            current_year += 1
            current_month = 1
        else:
            current_month += 1


def validate_interval(
    start_year: int,
    start_month: int,
    end_year: int,
    end_month: int,
) -> None:
    """Validate the requested download interval."""
    if start_month not in MONTH_NUMBER_TO_NAME:
        raise ValueError(f"start month must be between 1 and 12, got {start_month}")

    if end_month not in MONTH_NUMBER_TO_NAME:
        raise ValueError(f"end month must be between 1 and 12, got {end_month}")

    today = date.today()

    current_year = today.year
    current_month = today.month

    if not MIN_ARCHIVE_YEAR <= start_year <= current_year:
        raise ValueError(
            f"start year must be between {MIN_ARCHIVE_YEAR} and {current_year}, "
            f"got {start_year}"
        )

    if not MIN_ARCHIVE_YEAR <= end_year <= current_year:
        raise ValueError(
            f"end year must be between {MIN_ARCHIVE_YEAR} and {current_year}, "
            f"got {end_year}"
        )

    if (
        start_year,
        start_month,
    ) > (
        current_year,
        current_month,
    ):
        raise ValueError(
            f"start year/month must not be in the future, got "
            f"{start_year:04d}-{start_month:02d} (current: "
            f"{current_year:04d}-{current_month:02d})"
        )

    if (
        end_year,
        end_month,
    ) > (
        current_year,
        current_month,
    ):
        raise ValueError(
            f"end year/month must not be in the future, got "
            f"{end_year:04d}-{end_month:02d} (current: "
            f"{current_year:04d}-{current_month:02d})"
        )

    if (
        start_year,
        start_month,
    ) > (
        end_year,
        end_month,
    ):
        raise ValueError("start year/month must not be after end year/month")


def download_interval(
    start_year: int,
    start_month: int,
    end_year: int,
    end_month: int,
    *,
    force: bool = False,
) -> tuple[list[Extraction], list[tuple[int, int, str]]]:
    """Download and parse an inclusive year/month interval."""
    validate_interval(
        start_year,
        start_month,
        end_year,
        end_month,
    )

    extractions: list[Extraction] = []
    failures: list[tuple[int, int, str]] = []

    with create_http_session() as session:
        for year, month in iter_year_months(
            start_year,
            start_month,
            end_year,
            end_month,
        ):
            try:
                month_extractions = process_month(
                    year,
                    month,
                    session=session,
                    force=force,
                )
            except (
                requests.RequestException,
                ScrapingError,
                OSError,
            ) as exc:
                LOGGER.error(
                    "Failed %04d-%02d: %s",
                    year,
                    month,
                    exc,
                )

                failures.append(
                    (
                        year,
                        month,
                        str(exc),
                    )
                )

                continue

            extractions.extend(month_extractions)

    return (
        deduplicate_extractions(extractions),
        failures,
    )


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
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


def count_csv_rows(path: Path) -> int | None:
    """Return the number of data rows in an existing CSV file, or None if absent."""
    if not path.exists():
        return None

    with path.open(
        encoding="utf-8",
        newline="",
    ) as csv_file:
        return sum(1 for _ in csv.reader(csv_file)) - 1


def remove_partial_extractions_csv(path: Path) -> bool:
    """Delete a partial CSV left behind by an earlier failed run.

    Cleanup never fails the run: an unremovable file is only reported.
    """
    if not path.exists():
        return False

    try:
        path.unlink()
    except OSError as exc:
        LOGGER.warning(
            "Could not remove stale partial CSV %s: %s",
            path,
            exc,
        )

        return False

    LOGGER.info(
        "Removed stale partial CSV: %s",
        path,
    )

    return True


def main() -> int:
    """Run the command-line downloader."""
    parser = build_argument_parser()
    args = parser.parse_args()

    configure_logging(
        verbose=args.verbose,
    )

    (
        start_year,
        start_month,
        end_year,
        end_month,
    ) = resolve_interval(args)

    try:
        extractions, failures = download_interval(
            start_year,
            start_month,
            end_year,
            end_month,
            force=args.force,
        )
    except ValueError as exc:
        LOGGER.error(
            "%s",
            exc,
        )

        return 1
    except Exception:
        LOGGER.exception("Unexpected error while downloading extractions")

        return 1

    canonical_path = PROCESSED_DATA_DIRECTORY / EXTRACTIONS_FILE_NAME
    partial_path = PROCESSED_DATA_DIRECTORY / PARTIAL_EXTRACTIONS_FILE_NAME

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
