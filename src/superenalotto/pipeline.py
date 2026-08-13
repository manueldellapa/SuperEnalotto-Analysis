"""Download, cache, parse and persist historical SuperEnalotto extractions.

This is the only module in the package that touches the filesystem. Every path
it uses arrives as a DataPaths argument, so nothing here depends on where the
package itself lives.
"""

from __future__ import annotations

import csv
import logging
from collections.abc import Iterable
from datetime import date
from pathlib import Path

import requests

from .constants import (
    MIN_ARCHIVE_YEAR,
    MONTH_NUMBER_TO_NAME,
)
from .models import Extraction
from .paths import DataPaths
from .scraper import (
    ScrapingError,
    create_http_session,
    download_archive_page,
    parse_archive_page,
)

LOGGER = logging.getLogger(__name__)


class ExtractionConflictError(ValueError):
    """Raised when two records share an identity but carry different payloads."""


def save_raw_html(
    html: str,
    *,
    paths: DataPaths,
    year: int,
    month: int,
) -> Path:
    """Save raw archive HTML to disk."""
    paths.raw_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = paths.raw_html_path(
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
    *,
    paths: DataPaths,
) -> str:
    """Load previously downloaded raw archive HTML."""
    path = paths.raw_html_path(
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
    paths: DataPaths,
    session: requests.Session,
    force: bool = False,
) -> Path:
    """Download and persist one monthly archive page.

    Existing files are reused unless force is enabled.
    """
    path = paths.raw_html_path(
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
        paths=paths,
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
    paths: DataPaths,
    session: requests.Session,
    force: bool = False,
) -> list[Extraction]:
    """Download, cache and parse one monthly archive."""
    path = download_month(
        year,
        month,
        paths=paths,
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
    """Remove duplicated extractions and sort chronologically.

    Exact duplicates are collapsed. Records sharing a contest number and an
    extraction date but carrying different drawn values are a data-integrity
    error and raise ExtractionConflictError instead of silently overwriting
    each other.
    """
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

        previous_extraction = unique.get(key)

        if previous_extraction is not None and previous_extraction != extraction:
            raise ExtractionConflictError(
                f"Contest {extraction.contest_number} on "
                f"{extraction.extraction_date.isoformat()} has conflicting "
                f"payloads: {previous_extraction.describe_payload()} "
                f"vs {extraction.describe_payload()}"
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
    output_path: Path,
) -> Path:
    """Save extractions to a CSV file."""
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
    paths: DataPaths,
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
                    paths=paths,
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
