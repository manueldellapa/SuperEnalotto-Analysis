"""Constants used by the SuperEnalotto scraper and data models."""

from __future__ import annotations

from pathlib import Path
from typing import Final

# -----------------------------------------------------------------------------
# Project paths
# -----------------------------------------------------------------------------

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]

DATA_DIRECTORY: Final[Path] = PROJECT_ROOT / "data"
RAW_DATA_DIRECTORY: Final[Path] = DATA_DIRECTORY / "raw"
PROCESSED_DATA_DIRECTORY: Final[Path] = DATA_DIRECTORY / "processed"


# -----------------------------------------------------------------------------
# SuperEnalotto website
# -----------------------------------------------------------------------------

BASE_URL: Final[str] = "https://www.superenalotto.it"

ARCHIVE_URL_TEMPLATE: Final[str] = BASE_URL + "/archivio-estrazioni/{year}/{month}"

HTTP_TIMEOUT_SECONDS: Final[int] = 30

HTTP_RETRIES: Final[int] = 4
HTTP_BACKOFF_FACTOR: Final[float] = 1.0

HTTP_RETRY_STATUS_CODES: Final[tuple[int, ...]] = (
    429,
    500,
    502,
    503,
    504,
)

HTTP_HEADERS: Final[dict[str, str]] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
}


# -----------------------------------------------------------------------------
# Calendar
# -----------------------------------------------------------------------------

MONTHS: Final[tuple[str, ...]] = (
    "gennaio",
    "febbraio",
    "marzo",
    "aprile",
    "maggio",
    "giugno",
    "luglio",
    "agosto",
    "settembre",
    "ottobre",
    "novembre",
    "dicembre",
)

MONTH_NUMBER_TO_NAME: Final[dict[int, str]] = {
    index: month for index, month in enumerate(MONTHS, start=1)
}

MONTH_NAME_TO_NUMBER: Final[dict[str, int]] = {
    month: index for index, month in MONTH_NUMBER_TO_NAME.items()
}


# -----------------------------------------------------------------------------
# SuperEnalotto rules
# -----------------------------------------------------------------------------

MIN_ARCHIVE_YEAR: Final[int] = 1997  # SuperEnalotto's first year of operation

MIN_NUMBER: Final[int] = 1
MAX_NUMBER: Final[int] = 90

MAIN_NUMBERS_COUNT: Final[int] = 6

VALID_NUMBER_RANGE: Final[range] = range(
    MIN_NUMBER,
    MAX_NUMBER + 1,
)


# -----------------------------------------------------------------------------
# Dataset
# -----------------------------------------------------------------------------

RAW_FILE_NAME_TEMPLATE: Final[str] = "{year}-{month:02d}.html"

EXTRACTIONS_FILE_NAME: Final[str] = "extractions.csv"
