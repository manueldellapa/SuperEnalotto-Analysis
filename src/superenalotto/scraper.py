"""HTTP client and HTML parser for the official SuperEnalotto archive."""

from __future__ import annotations

import re
from datetime import date
from typing import Final

import requests
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from .constants import (
    ARCHIVE_URL_TEMPLATE,
    HTTP_BACKOFF_FACTOR,
    HTTP_HEADERS,
    HTTP_RETRIES,
    HTTP_RETRY_STATUS_CODES,
    HTTP_TIMEOUT_SECONDS,
    MONTH_NAME_TO_NUMBER,
    MONTH_NUMBER_TO_NAME,
)
from .models import Extraction
from .validators import validate_extraction

_CONTEST_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:Concorso\s*)?"
    r"N(?:[º°]|\.)?\s*"
    r"(?P<contest>\d+)\s+"
    r"del\s+"
    r"(?P<day>\d{1,2})\s+"
    r"(?P<month>[A-Za-zÀ-ÿ]+)\s+"
    r"(?P<year>\d{4})",
    flags=re.IGNORECASE,
)

_RESULTS_TABLE_CLASS: Final[str] = "superenalotto-extraction-archive__details__table"


class ScrapingError(RuntimeError):
    """Raised when a SuperEnalotto page cannot be parsed correctly."""


def create_http_session() -> requests.Session:
    """Create an HTTP session configured with retries and backoff."""
    retry = Retry(
        total=HTTP_RETRIES,
        connect=HTTP_RETRIES,
        read=HTTP_RETRIES,
        status=HTTP_RETRIES,
        backoff_factor=HTTP_BACKOFF_FACTOR,
        status_forcelist=HTTP_RETRY_STATUS_CODES,
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
    )

    adapter = HTTPAdapter(
        max_retries=retry,
    )

    session = requests.Session()

    session.headers.update(HTTP_HEADERS)

    session.mount(
        "https://",
        adapter,
    )

    session.mount(
        "http://",
        adapter,
    )

    return session


def build_archive_url(year: int, month: int) -> str:
    """Build the URL for a monthly SuperEnalotto archive page."""
    try:
        month_name = MONTH_NUMBER_TO_NAME[month]
    except KeyError as exc:
        raise ValueError(f"month must be between 1 and 12, got {month}") from exc

    return ARCHIVE_URL_TEMPLATE.format(
        year=year,
        month=month_name,
    )


def download_archive_page(
    year: int,
    month: int,
    *,
    session: requests.Session | None = None,
) -> str:
    """Download a monthly SuperEnalotto archive page."""
    url = build_archive_url(
        year,
        month,
    )

    owns_session = session is None
    client = session or create_http_session()

    try:
        response = client.get(
            url,
            timeout=HTTP_TIMEOUT_SECONDS,
        )

        response.raise_for_status()

        return response.text
    finally:
        if owns_session:
            client.close()


def _parse_month_name(month_name: str) -> int:
    """Convert an Italian month name to its numeric representation."""
    normalized_month = month_name.strip().lower()

    try:
        return MONTH_NAME_TO_NUMBER[normalized_month]
    except KeyError as exc:
        raise ScrapingError(f"Unknown Italian month name: {month_name!r}") from exc


def _parse_contest_header(text: str) -> tuple[int, date]:
    """Parse contest number and extraction date."""
    normalized_text = " ".join(text.split())

    match = _CONTEST_PATTERN.search(normalized_text)

    if match is None:
        raise ScrapingError(f"Unable to parse contest header: {normalized_text!r}")

    contest_number = int(match.group("contest"))
    day = int(match.group("day"))
    month = _parse_month_name(match.group("month"))
    year = int(match.group("year"))

    try:
        extraction_date = date(
            year,
            month,
            day,
        )
    except ValueError as exc:
        raise ScrapingError(f"Invalid extraction date: {normalized_text!r}") from exc

    return contest_number, extraction_date


def _extract_integers(element: Tag) -> list[int]:
    """Extract integer values from a DOM element."""
    text = element.get_text(
        " ",
        strip=True,
    )

    return [int(value) for value in re.findall(r"\b\d+\b", text)]


def _parse_table_row(row: Tag) -> Extraction | None:
    """Parse a SuperEnalotto archive table row.

    Expected columns:

        Concorso
        Combinazione vincente
        Jolly
        SuperStar
        Dettagli
    """
    cells = row.find_all("td", recursive=False)

    if len(cells) < 4:
        return None

    contest_text = cells[0].get_text(
        " ",
        strip=True,
    )

    if _CONTEST_PATTERN.search(contest_text) is None:
        return None

    contest_number, extraction_date = _parse_contest_header(contest_text)

    numbers = _extract_integers(cells[1])

    if len(numbers) != 6:
        raise ScrapingError(
            f"Contest {contest_number}: expected 6 main numbers, found {numbers!r}"
        )

    jolly_values = _extract_integers(cells[2])

    if len(jolly_values) != 1:
        raise ScrapingError(
            f"Contest {contest_number}: expected 1 Jolly number, found {jolly_values!r}"
        )

    superstar_values = _extract_integers(cells[3])

    if len(superstar_values) != 1:
        raise ScrapingError(
            f"Contest {contest_number}: "
            f"expected 1 SuperStar number, found {superstar_values!r}"
        )

    extraction = Extraction(
        contest_number=contest_number,
        extraction_date=extraction_date,
        numbers=(
            numbers[0],
            numbers[1],
            numbers[2],
            numbers[3],
            numbers[4],
            numbers[5],
        ),
        jolly=jolly_values[0],
        superstar=superstar_values[0],
    )

    try:
        validate_extraction(extraction)
    except (TypeError, ValueError) as exc:
        raise ScrapingError(
            f"Contest {contest_number}: invalid extraction data: {exc}"
        ) from exc

    return extraction


def parse_archive_page(html: str) -> list[Extraction]:
    """Parse all SuperEnalotto extractions from a monthly archive page."""
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    results_table = soup.find(
        "table",
        class_=_RESULTS_TABLE_CLASS,
    )

    if isinstance(results_table, Tag):
        rows = results_table.find_all("tr")
    else:
        rows = soup.find_all("tr")

    extractions: list[Extraction] = []
    seen: set[tuple[int, date]] = set()

    for row in rows:
        if not isinstance(row, Tag):
            continue

        extraction = _parse_table_row(row)

        if extraction is None:
            continue

        identity = (
            extraction.contest_number,
            extraction.extraction_date,
        )

        if identity in seen:
            continue

        seen.add(identity)
        extractions.append(extraction)

    if not extractions:
        raise ScrapingError("No SuperEnalotto contests found in archive table")

    extractions.sort(key=lambda extraction: extraction.extraction_date)

    return extractions


def get_month_extractions(
    year: int,
    month: int,
    *,
    session: requests.Session | None = None,
) -> list[Extraction]:
    """Download and parse all extractions for a given month."""
    html = download_archive_page(
        year,
        month,
        session=session,
    )

    return parse_archive_page(html)
