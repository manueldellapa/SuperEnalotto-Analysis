"""Tests for the historical SuperEnalotto download script."""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Self

import pytest
import requests

from scripts import download_extractions
from superenalotto.models import Extraction
from superenalotto.scraper import ScrapingError


def freeze_today(
    monkeypatch: pytest.MonkeyPatch,
    today_value: date,
) -> None:
    """Pin the current date seen by the download script."""

    class FrozenDate(date):
        @classmethod
        def today(cls) -> Self:
            return cls(
                today_value.year,
                today_value.month,
                today_value.day,
            )

    monkeypatch.setattr(
        download_extractions,
        "date",
        FrozenDate,
    )


def make_extraction(
    contest_number: int,
    extraction_date: date,
    *,
    numbers: tuple[int, int, int, int, int, int] = (4, 17, 19, 23, 47, 59),
    jolly: int = 51,
    superstar: int = 82,
) -> Extraction:
    """Create a valid extraction for tests."""
    return Extraction(
        contest_number=contest_number,
        extraction_date=extraction_date,
        numbers=numbers,
        jolly=jolly,
        superstar=superstar,
    )


def test_build_raw_file_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        download_extractions,
        "RAW_DATA_DIRECTORY",
        tmp_path,
    )

    path = download_extractions.build_raw_file_path(
        2026,
        7,
    )

    assert path == tmp_path / "2026-07.html"


def test_save_and_load_raw_html(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        download_extractions,
        "RAW_DATA_DIRECTORY",
        tmp_path,
    )

    html = "<html><body>SuperEnalotto</body></html>"

    path = download_extractions.save_raw_html(
        html,
        year=2026,
        month=7,
    )

    assert path == tmp_path / "2026-07.html"
    assert path.exists()

    loaded_html = download_extractions.load_raw_html(
        2026,
        7,
    )

    assert loaded_html == html


def test_save_raw_html_preserves_existing_file_on_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        download_extractions,
        "RAW_DATA_DIRECTORY",
        tmp_path,
    )

    existing_file = tmp_path / "2026-07.html"
    existing_file.write_text(
        "<html>good</html>",
        encoding="utf-8",
    )

    def broken_write_text(*args: object, **kwargs: object) -> int:
        raise OSError("simulated disk failure")

    monkeypatch.setattr(
        Path,
        "write_text",
        broken_write_text,
    )

    with pytest.raises(OSError):
        download_extractions.save_raw_html(
            "<html>new</html>",
            year=2026,
            month=7,
        )

    assert (
        existing_file.read_text(
            encoding="utf-8",
        )
        == "<html>good</html>"
    )


def test_download_month_uses_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        download_extractions,
        "RAW_DATA_DIRECTORY",
        tmp_path,
    )

    cached_file = tmp_path / "2026-07.html"
    cached_file.write_text(
        "<html>cached</html>",
        encoding="utf-8",
    )

    called = False

    def fake_download_archive_page(
        year: int,
        month: int,
        *,
        session: requests.Session | None = None,
    ) -> str:
        nonlocal called
        called = True

        return "<html>downloaded</html>"

    monkeypatch.setattr(
        download_extractions,
        "download_archive_page",
        fake_download_archive_page,
    )

    with requests.Session() as session:
        result = download_extractions.download_month(
            2026,
            7,
            session=session,
        )

    assert result == cached_file
    assert called is False

    assert (
        cached_file.read_text(
            encoding="utf-8",
        )
        == "<html>cached</html>"
    )


def test_download_month_force_redownloads_cached_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        download_extractions,
        "RAW_DATA_DIRECTORY",
        tmp_path,
    )

    cached_file = tmp_path / "2026-07.html"
    cached_file.write_text(
        "<html>old</html>",
        encoding="utf-8",
    )

    def fake_download_archive_page(
        year: int,
        month: int,
        *,
        session: requests.Session | None = None,
    ) -> str:
        assert year == 2026
        assert month == 7
        assert session is not None

        return "<html>new</html>"

    monkeypatch.setattr(
        download_extractions,
        "download_archive_page",
        fake_download_archive_page,
    )

    with requests.Session() as session:
        result = download_extractions.download_month(
            2026,
            7,
            session=session,
            force=True,
        )

    assert result == cached_file

    assert (
        cached_file.read_text(
            encoding="utf-8",
        )
        == "<html>new</html>"
    )


def test_process_month_parses_cached_html(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        download_extractions,
        "RAW_DATA_DIRECTORY",
        tmp_path,
    )

    extraction = make_extraction(
        105,
        date(2026, 7, 2),
    )

    def fake_download_month(
        year: int,
        month: int,
        *,
        session: requests.Session,
        force: bool = False,
    ) -> Path:
        assert year == 2026
        assert month == 7

        path = tmp_path / "2026-07.html"
        path.write_text(
            "<html>archive</html>",
            encoding="utf-8",
        )

        return path

    def fake_parse_archive_page(
        html: str,
    ) -> list[Extraction]:
        assert html == "<html>archive</html>"

        return [extraction]

    monkeypatch.setattr(
        download_extractions,
        "download_month",
        fake_download_month,
    )

    monkeypatch.setattr(
        download_extractions,
        "parse_archive_page",
        fake_parse_archive_page,
    )

    with requests.Session() as session:
        result = download_extractions.process_month(
            2026,
            7,
            session=session,
        )

    assert result == [extraction]


def test_process_month_rejects_extractions_outside_requested_month(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        download_extractions,
        "RAW_DATA_DIRECTORY",
        tmp_path,
    )

    wrong_month_extraction = make_extraction(
        105,
        date(2026, 8, 2),
    )

    def fake_download_month(
        year: int,
        month: int,
        *,
        session: requests.Session,
        force: bool = False,
    ) -> Path:
        path = tmp_path / "2026-07.html"
        path.write_text(
            "<html>archive</html>",
            encoding="utf-8",
        )

        return path

    def fake_parse_archive_page(
        html: str,
    ) -> list[Extraction]:
        return [wrong_month_extraction]

    monkeypatch.setattr(
        download_extractions,
        "download_month",
        fake_download_month,
    )

    monkeypatch.setattr(
        download_extractions,
        "parse_archive_page",
        fake_parse_archive_page,
    )

    with (
        requests.Session() as session,
        pytest.raises(
            ScrapingError,
            match="outside requested",
        ),
    ):
        download_extractions.process_month(
            2026,
            7,
            session=session,
        )


CONFLICTING_ROWS_HTML = """
<table>
    <tr>
        <td>Concorso Nº 105 del 2 Luglio 2026</td>
        <td>4 17 19 23 47 59</td>
        <td>51</td>
        <td>82</td>
        <td>Dettagli</td>
    </tr>

    <tr>
        <td>Concorso Nº 105 del 2 Luglio 2026</td>
        <td>1 2 3 4 5 6</td>
        <td>51</td>
        <td>82</td>
        <td>Dettagli</td>
    </tr>
</table>
"""


def test_process_month_rejects_conflicting_rows_in_archive_page(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        download_extractions,
        "RAW_DATA_DIRECTORY",
        tmp_path,
    )

    def fake_download_month(
        year: int,
        month: int,
        *,
        session: requests.Session,
        force: bool = False,
    ) -> Path:
        path = tmp_path / "2026-07.html"
        path.write_text(
            CONFLICTING_ROWS_HTML,
            encoding="utf-8",
        )

        return path

    monkeypatch.setattr(
        download_extractions,
        "download_month",
        fake_download_month,
    )

    with (
        requests.Session() as session,
        pytest.raises(
            ScrapingError,
            match="conflicting payloads",
        ),
    ):
        download_extractions.process_month(
            2026,
            7,
            session=session,
        )


def test_download_interval_reports_conflicting_rows_as_month_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        download_extractions,
        "RAW_DATA_DIRECTORY",
        tmp_path,
    )

    def fake_download_month(
        year: int,
        month: int,
        *,
        session: requests.Session,
        force: bool = False,
    ) -> Path:
        path = tmp_path / "2026-07.html"
        path.write_text(
            CONFLICTING_ROWS_HTML,
            encoding="utf-8",
        )

        return path

    monkeypatch.setattr(
        download_extractions,
        "download_month",
        fake_download_month,
    )

    extractions, failures = download_extractions.download_interval(
        2026,
        7,
        2026,
        7,
    )

    assert extractions == []
    assert len(failures) == 1

    year, month, error = failures[0]

    assert (year, month) == (2026, 7)
    assert "conflicting payloads" in error


def test_deduplicate_extractions() -> None:
    first = make_extraction(
        105,
        date(2026, 7, 2),
    )

    second = make_extraction(
        106,
        date(2026, 7, 3),
    )

    result = download_extractions.deduplicate_extractions(
        [
            second,
            first,
            first,
        ]
    )

    assert result == [
        first,
        second,
    ]


def test_deduplicate_extractions_warns_on_conflicting_dates(
    caplog: pytest.LogCaptureFixture,
) -> None:
    first = make_extraction(
        105,
        date(2026, 7, 2),
    )

    conflicting = make_extraction(
        105,
        date(2026, 7, 3),
    )

    with caplog.at_level(logging.WARNING):
        download_extractions.deduplicate_extractions(
            [
                first,
                conflicting,
            ]
        )

    assert "conflicting dates" in caplog.text


def test_deduplicate_extractions_collapses_equal_duplicates() -> None:
    first = make_extraction(
        105,
        date(2026, 7, 2),
    )

    identical = make_extraction(
        105,
        date(2026, 7, 2),
    )

    assert first is not identical

    result = download_extractions.deduplicate_extractions(
        [
            first,
            identical,
        ]
    )

    assert result == [first]


def test_deduplicate_extractions_raises_on_conflicting_numbers() -> None:
    first = make_extraction(
        105,
        date(2026, 7, 2),
    )

    conflicting = make_extraction(
        105,
        date(2026, 7, 2),
        numbers=(1, 2, 3, 4, 5, 6),
    )

    with pytest.raises(
        download_extractions.ExtractionConflictError,
        match="conflicting payloads",
    ) as exc_info:
        download_extractions.deduplicate_extractions(
            [
                first,
                conflicting,
            ]
        )

    message = str(exc_info.value)

    assert "Contest 105 on 2026-07-02" in message
    assert "numbers=[4, 17, 19, 23, 47, 59]" in message
    assert "numbers=[1, 2, 3, 4, 5, 6]" in message


@pytest.mark.parametrize(
    "conflicting",
    [
        make_extraction(
            105,
            date(2026, 7, 2),
            numbers=(1, 2, 3, 4, 5, 6),
        ),
        make_extraction(
            105,
            date(2026, 7, 2),
            jolly=7,
        ),
        make_extraction(
            105,
            date(2026, 7, 2),
            superstar=9,
        ),
    ],
)
def test_deduplicate_extractions_raises_on_any_conflicting_field(
    conflicting: Extraction,
) -> None:
    first = make_extraction(
        105,
        date(2026, 7, 2),
    )

    with pytest.raises(download_extractions.ExtractionConflictError):
        download_extractions.deduplicate_extractions(
            [
                first,
                conflicting,
            ]
        )


def test_deduplicate_extractions_allows_same_payload_on_different_contests() -> None:
    first = make_extraction(
        105,
        date(2026, 7, 2),
    )

    second = make_extraction(
        106,
        date(2026, 7, 4),
    )

    result = download_extractions.deduplicate_extractions(
        [
            first,
            second,
        ]
    )

    assert result == [
        first,
        second,
    ]


def test_save_extractions_csv(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "extractions.csv"

    extraction = make_extraction(
        105,
        date(2026, 7, 2),
    )

    result = download_extractions.save_extractions_csv(
        [extraction],
        output_path=output_path,
    )

    assert result == output_path
    assert output_path.exists()

    with output_path.open(
        encoding="utf-8",
        newline="",
    ) as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert rows == [
        {
            "contest_number": "105",
            "extraction_date": "2026-07-02",
            "number_1": "4",
            "number_2": "17",
            "number_3": "19",
            "number_4": "23",
            "number_5": "47",
            "number_6": "59",
            "jolly": "51",
            "superstar": "82",
        }
    ]


def test_save_extractions_csv_preserves_existing_file_on_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "extractions.csv"

    output_path.write_text(
        "contest_number\n999\n",
        encoding="utf-8",
    )

    def broken_writerows(*args: object, **kwargs: object) -> None:
        raise OSError("simulated disk failure")

    monkeypatch.setattr(
        csv.DictWriter,
        "writerows",
        broken_writerows,
    )

    extraction = make_extraction(
        105,
        date(2026, 7, 2),
    )

    with pytest.raises(OSError):
        download_extractions.save_extractions_csv(
            [extraction],
            output_path=output_path,
        )

    assert (
        output_path.read_text(
            encoding="utf-8",
        )
        == "contest_number\n999\n"
    )


def test_iter_year_months_single_month() -> None:
    result = list(
        download_extractions.iter_year_months(
            2026,
            7,
            2026,
            7,
        )
    )

    assert result == [
        (2026, 7),
    ]


def test_iter_year_months_same_year() -> None:
    result = list(
        download_extractions.iter_year_months(
            2026,
            7,
            2026,
            9,
        )
    )

    assert result == [
        (2026, 7),
        (2026, 8),
        (2026, 9),
    ]


def test_iter_year_months_crosses_year_boundary() -> None:
    result = list(
        download_extractions.iter_year_months(
            2025,
            11,
            2026,
            2,
        )
    )

    assert result == [
        (2025, 11),
        (2025, 12),
        (2026, 1),
        (2026, 2),
    ]


@pytest.mark.parametrize(
    ("start_month", "end_month"),
    [
        (0, 12),
        (13, 12),
        (1, 0),
        (1, 13),
    ],
)
def test_validate_interval_rejects_invalid_months(
    start_month: int,
    end_month: int,
) -> None:
    with pytest.raises(ValueError):
        download_extractions.validate_interval(
            2025,
            start_month,
            2026,
            end_month,
        )


def test_validate_interval_rejects_reversed_interval() -> None:
    with pytest.raises(
        ValueError,
        match="must not be after",
    ):
        download_extractions.validate_interval(
            2026,
            7,
            2025,
            12,
        )


def test_validate_interval_accepts_valid_interval() -> None:
    download_extractions.validate_interval(
        2024,
        1,
        2026,
        7,
    )


def test_validate_interval_rejects_implausible_start_year() -> None:
    with pytest.raises(
        ValueError,
        match="start year must be between",
    ):
        download_extractions.validate_interval(
            1,
            1,
            9999,
            12,
        )


def test_validate_interval_rejects_future_end_year() -> None:
    with pytest.raises(
        ValueError,
        match="end year must be between",
    ):
        download_extractions.validate_interval(
            2024,
            1,
            2200,
            12,
        )


def test_validate_interval_accepts_current_month(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    freeze_today(
        monkeypatch,
        date(2026, 6, 15),
    )

    download_extractions.validate_interval(
        2026,
        1,
        2026,
        6,
    )


def test_validate_interval_accepts_december_of_past_year(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    freeze_today(
        monkeypatch,
        date(2026, 6, 15),
    )

    download_extractions.validate_interval(
        2025,
        1,
        2025,
        12,
    )


def test_validate_interval_rejects_future_end_month(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    freeze_today(
        monkeypatch,
        date(2026, 6, 15),
    )

    with pytest.raises(
        ValueError,
        match="end year/month must not be in the future",
    ):
        download_extractions.validate_interval(
            2026,
            1,
            2026,
            7,
        )


def test_validate_interval_rejects_future_start_month(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    freeze_today(
        monkeypatch,
        date(2026, 6, 15),
    )

    with pytest.raises(
        ValueError,
        match="start year/month must not be in the future",
    ):
        download_extractions.validate_interval(
            2026,
            7,
            2026,
            9,
        )


def test_validate_interval_rejects_future_month_in_december(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    freeze_today(
        monkeypatch,
        date(2026, 12, 15),
    )

    download_extractions.validate_interval(
        2026,
        1,
        2026,
        12,
    )

    with pytest.raises(
        ValueError,
        match="end year must be between",
    ):
        download_extractions.validate_interval(
            2026,
            1,
            2027,
            1,
        )


def test_resolve_interval_single_month() -> None:
    args = argparse.Namespace(
        start_year=2026,
        start_month=7,
        end_year=None,
        end_month=None,
    )

    assert download_extractions.resolve_interval(args) == (
        2026,
        7,
        2026,
        7,
    )


def test_resolve_interval_defaults_end_month_to_december_for_past_year(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    freeze_today(
        monkeypatch,
        date(2026, 6, 15),
    )

    args = argparse.Namespace(
        start_year=2024,
        start_month=7,
        end_year=2025,
        end_month=None,
    )

    assert download_extractions.resolve_interval(args) == (
        2024,
        7,
        2025,
        12,
    )


def test_resolve_interval_defaults_end_month_to_current_month(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    freeze_today(
        monkeypatch,
        date(2026, 6, 15),
    )

    args = argparse.Namespace(
        start_year=2024,
        start_month=7,
        end_year=2026,
        end_month=None,
    )

    assert download_extractions.resolve_interval(args) == (
        2024,
        7,
        2026,
        6,
    )


def test_resolve_interval_explicit_end_month_wins_for_current_year(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    freeze_today(
        monkeypatch,
        date(2026, 6, 15),
    )

    args = argparse.Namespace(
        start_year=2026,
        start_month=1,
        end_year=2026,
        end_month=3,
    )

    assert download_extractions.resolve_interval(args) == (
        2026,
        1,
        2026,
        3,
    )


def test_resolve_interval_explicit_range() -> None:
    args = argparse.Namespace(
        start_year=2024,
        start_month=2,
        end_year=2026,
        end_month=7,
    )

    assert download_extractions.resolve_interval(args) == (
        2024,
        2,
        2026,
        7,
    )


def test_download_interval_collects_extractions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    january = make_extraction(
        1,
        date(2024, 1, 2),
    )

    february = make_extraction(
        2,
        date(2024, 2, 1),
    )

    def fake_process_month(
        year: int,
        month: int,
        *,
        session: requests.Session,
        force: bool = False,
    ) -> list[Extraction]:
        assert year == 2024

        if month == 1:
            return [january]

        if month == 2:
            return [february]

        raise AssertionError(f"Unexpected month: {month}")

    monkeypatch.setattr(
        download_extractions,
        "process_month",
        fake_process_month,
    )

    extractions, failures = download_extractions.download_interval(
        2024,
        1,
        2024,
        2,
    )

    assert extractions == [
        january,
        february,
    ]

    assert failures == []


def test_download_interval_raises_on_conflicting_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    january = make_extraction(
        1,
        date(2024, 1, 2),
    )

    conflicting_january = make_extraction(
        1,
        date(2024, 1, 2),
        jolly=7,
    )

    def fake_process_month(
        year: int,
        month: int,
        *,
        session: requests.Session,
        force: bool = False,
    ) -> list[Extraction]:
        if month == 1:
            return [january]

        return [conflicting_january]

    monkeypatch.setattr(
        download_extractions,
        "process_month",
        fake_process_month,
    )

    with pytest.raises(
        download_extractions.ExtractionConflictError,
        match="conflicting payloads",
    ):
        download_extractions.download_interval(
            2024,
            1,
            2024,
            2,
        )


def test_download_interval_continues_after_failed_month(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    january = make_extraction(
        1,
        date(2024, 1, 2),
    )

    march = make_extraction(
        3,
        date(2024, 3, 2),
    )

    processed_months: list[int] = []

    def fake_process_month(
        year: int,
        month: int,
        *,
        session: requests.Session,
        force: bool = False,
    ) -> list[Extraction]:
        processed_months.append(month)

        if month == 1:
            return [january]

        if month == 2:
            raise requests.ReadTimeout("simulated timeout")

        if month == 3:
            return [march]

        raise AssertionError(f"Unexpected month: {month}")

    monkeypatch.setattr(
        download_extractions,
        "process_month",
        fake_process_month,
    )

    extractions, failures = download_extractions.download_interval(
        2024,
        1,
        2024,
        3,
    )

    assert processed_months == [
        1,
        2,
        3,
    ]

    assert extractions == [
        january,
        march,
    ]

    assert len(failures) == 1

    year, month, error = failures[0]

    assert year == 2024
    assert month == 2
    assert "simulated timeout" in error


def test_download_interval_handles_scraping_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_process_month(
        year: int,
        month: int,
        *,
        session: requests.Session,
        force: bool = False,
    ) -> list[Extraction]:
        raise ScrapingError("invalid archive")

    monkeypatch.setattr(
        download_extractions,
        "process_month",
        fake_process_month,
    )

    extractions, failures = download_extractions.download_interval(
        2024,
        1,
        2024,
        1,
    )

    assert extractions == []
    assert len(failures) == 1

    assert failures[0] == (
        2024,
        1,
        "invalid archive",
    )


def test_build_argument_parser_defaults() -> None:
    parser = download_extractions.build_argument_parser()

    args = parser.parse_args(
        [
            "--start-year",
            "2024",
        ]
    )

    assert args.start_year == 2024
    assert args.start_month == 1
    assert args.end_year is None
    assert args.end_month is None
    assert args.force is False
    assert args.verbose is False


def test_build_argument_parser_parses_full_arguments() -> None:
    parser = download_extractions.build_argument_parser()

    args = parser.parse_args(
        [
            "--start-year",
            "2024",
            "--start-month",
            "3",
            "--end-year",
            "2026",
            "--end-month",
            "7",
            "--force",
            "--verbose",
        ]
    )

    assert args.start_year == 2024
    assert args.start_month == 3
    assert args.end_year == 2026
    assert args.end_month == 7
    assert args.force is True
    assert args.verbose is True


def test_main_returns_zero_on_full_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        download_extractions,
        "PROCESSED_DATA_DIRECTORY",
        tmp_path,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "download_extractions.py",
            "--start-year",
            "2026",
            "--start-month",
            "7",
            "--end-month",
            "7",
        ],
    )

    extraction = make_extraction(
        105,
        date(2026, 7, 2),
    )

    def fake_download_interval(
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        *,
        force: bool = False,
    ) -> tuple[list[Extraction], list[tuple[int, int, str]]]:
        assert (
            start_year,
            start_month,
            end_year,
            end_month,
        ) == (2026, 7, 2026, 7)

        return [extraction], []

    monkeypatch.setattr(
        download_extractions,
        "download_interval",
        fake_download_interval,
    )

    exit_code = download_extractions.main()

    assert exit_code == 0
    assert (tmp_path / "extractions.csv").exists()


def test_main_returns_one_on_partial_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        download_extractions,
        "PROCESSED_DATA_DIRECTORY",
        tmp_path,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "download_extractions.py",
            "--start-year",
            "2026",
            "--start-month",
            "7",
            "--end-month",
            "7",
        ],
    )

    def fake_download_interval(
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        *,
        force: bool = False,
    ) -> tuple[list[Extraction], list[tuple[int, int, str]]]:
        return [], [(2026, 7, "boom")]

    monkeypatch.setattr(
        download_extractions,
        "download_interval",
        fake_download_interval,
    )

    exit_code = download_extractions.main()

    assert exit_code == 1


def test_main_returns_one_on_invalid_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "download_extractions.py",
            "--start-year",
            "9999",
        ],
    )

    exit_code = download_extractions.main()

    assert exit_code == 1


def test_main_preserves_canonical_csv_on_conflicting_payloads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        download_extractions,
        "PROCESSED_DATA_DIRECTORY",
        tmp_path,
    )

    canonical_csv = tmp_path / "extractions.csv"
    canonical_csv.write_text(
        "contest_number\n1\n2\n3\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "download_extractions.py",
            "--start-year",
            "2026",
            "--start-month",
            "7",
            "--end-month",
            "7",
        ],
    )

    def fake_download_interval(
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        *,
        force: bool = False,
    ) -> tuple[list[Extraction], list[tuple[int, int, str]]]:
        raise download_extractions.ExtractionConflictError(
            "Contest 105 on 2026-07-02 has conflicting payloads"
        )

    monkeypatch.setattr(
        download_extractions,
        "download_interval",
        fake_download_interval,
    )

    with caplog.at_level(logging.ERROR):
        exit_code = download_extractions.main()

    assert exit_code == 1
    assert "Data integrity error" in caplog.text
    assert "conflicting payloads" in caplog.text

    assert canonical_csv.read_text(encoding="utf-8") == "contest_number\n1\n2\n3\n"
    assert not (tmp_path / "extractions.partial.csv").exists()


def test_main_preserves_canonical_csv_on_partial_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        download_extractions,
        "PROCESSED_DATA_DIRECTORY",
        tmp_path,
    )

    existing_csv = tmp_path / "extractions.csv"
    existing_csv.write_text(
        "contest_number\n1\n2\n3\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "download_extractions.py",
            "--start-year",
            "2026",
            "--start-month",
            "7",
            "--end-month",
            "7",
        ],
    )

    extraction = make_extraction(
        105,
        date(2026, 7, 2),
    )

    def fake_download_interval(
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        *,
        force: bool = False,
    ) -> tuple[list[Extraction], list[tuple[int, int, str]]]:
        return [extraction], [(2026, 7, "boom")]

    monkeypatch.setattr(
        download_extractions,
        "download_interval",
        fake_download_interval,
    )

    with caplog.at_level(logging.WARNING):
        exit_code = download_extractions.main()

    assert exit_code == 1

    assert (
        existing_csv.read_text(
            encoding="utf-8",
        )
        == "contest_number\n1\n2\n3\n"
    )

    partial_csv = tmp_path / "extractions.partial.csv"

    assert partial_csv.exists()

    with partial_csv.open(
        encoding="utf-8",
        newline="",
    ) as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert len(rows) == 1
    assert rows[0]["contest_number"] == "105"

    assert "Preserved" in caplog.text


def test_main_writes_partial_csv_when_canonical_is_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        download_extractions,
        "PROCESSED_DATA_DIRECTORY",
        tmp_path,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "download_extractions.py",
            "--start-year",
            "2026",
            "--start-month",
            "7",
            "--end-month",
            "7",
        ],
    )

    extraction = make_extraction(
        105,
        date(2026, 7, 2),
    )

    def fake_download_interval(
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        *,
        force: bool = False,
    ) -> tuple[list[Extraction], list[tuple[int, int, str]]]:
        return [extraction], [(2026, 7, "boom")]

    monkeypatch.setattr(
        download_extractions,
        "download_interval",
        fake_download_interval,
    )

    with caplog.at_level(logging.WARNING):
        exit_code = download_extractions.main()

    assert exit_code == 1
    assert not (tmp_path / "extractions.csv").exists()
    assert (tmp_path / "extractions.partial.csv").exists()
    assert "unwritten" in caplog.text


def test_remove_partial_extractions_csv_deletes_existing_file(
    tmp_path: Path,
) -> None:
    partial_csv = tmp_path / "extractions.partial.csv"
    partial_csv.write_text(
        "contest_number\n1\n",
        encoding="utf-8",
    )

    assert download_extractions.remove_partial_extractions_csv(partial_csv) is True
    assert not partial_csv.exists()


def test_remove_partial_extractions_csv_ignores_missing_file(
    tmp_path: Path,
) -> None:
    partial_csv = tmp_path / "extractions.partial.csv"

    assert download_extractions.remove_partial_extractions_csv(partial_csv) is False


def test_remove_partial_extractions_csv_warns_on_failed_removal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    partial_csv = tmp_path / "extractions.partial.csv"
    partial_csv.write_text(
        "contest_number\n1\n",
        encoding="utf-8",
    )

    def broken_unlink(*args: object, **kwargs: object) -> None:
        raise OSError("simulated permission failure")

    monkeypatch.setattr(
        Path,
        "unlink",
        broken_unlink,
    )

    with caplog.at_level(logging.WARNING):
        removed = download_extractions.remove_partial_extractions_csv(partial_csv)

    assert removed is False
    assert partial_csv.exists()
    assert "Could not remove stale partial CSV" in caplog.text


def test_main_removes_stale_partial_csv_on_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        download_extractions,
        "PROCESSED_DATA_DIRECTORY",
        tmp_path,
    )

    stale_partial = tmp_path / "extractions.partial.csv"
    stale_partial.write_text(
        "contest_number\n999\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "download_extractions.py",
            "--start-year",
            "2026",
            "--start-month",
            "7",
            "--end-month",
            "7",
        ],
    )

    extraction = make_extraction(
        105,
        date(2026, 7, 2),
    )

    def fake_download_interval(
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        *,
        force: bool = False,
    ) -> tuple[list[Extraction], list[tuple[int, int, str]]]:
        return [extraction], []

    monkeypatch.setattr(
        download_extractions,
        "download_interval",
        fake_download_interval,
    )

    exit_code = download_extractions.main()

    assert exit_code == 0
    assert (tmp_path / "extractions.csv").exists()
    assert not stale_partial.exists()


def test_main_keeps_partial_csv_when_run_has_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        download_extractions,
        "PROCESSED_DATA_DIRECTORY",
        tmp_path,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "download_extractions.py",
            "--start-year",
            "2026",
            "--start-month",
            "7",
            "--end-month",
            "7",
        ],
    )

    extraction = make_extraction(
        105,
        date(2026, 7, 2),
    )

    def fake_download_interval(
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        *,
        force: bool = False,
    ) -> tuple[list[Extraction], list[tuple[int, int, str]]]:
        return [extraction], [(2026, 7, "boom")]

    monkeypatch.setattr(
        download_extractions,
        "download_interval",
        fake_download_interval,
    )

    exit_code = download_extractions.main()

    assert exit_code == 1
    assert (tmp_path / "extractions.partial.csv").exists()
