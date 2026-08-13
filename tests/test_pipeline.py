"""Tests for the SuperEnalotto download and persistence pipeline."""

from __future__ import annotations

import csv
import logging
from datetime import date
from pathlib import Path

import pytest
import requests

from superenalotto import pipeline
from superenalotto.models import Extraction
from superenalotto.paths import DataPaths
from superenalotto.scraper import ScrapingError
from tests.support import freeze_today, make_extraction


def test_save_and_load_raw_html(
    tmp_path: Path,
) -> None:
    paths = DataPaths.from_root(tmp_path)

    html = "<html><body>SuperEnalotto</body></html>"

    path = pipeline.save_raw_html(
        html,
        paths=paths,
        year=2026,
        month=7,
    )

    assert path == tmp_path / "raw" / "2026-07.html"
    assert path.exists()

    loaded_html = pipeline.load_raw_html(
        2026,
        7,
        paths=paths,
    )

    assert loaded_html == html


def test_save_raw_html_creates_a_missing_data_directory(
    tmp_path: Path,
) -> None:
    paths = DataPaths.from_root(tmp_path / "custom" / "nested")

    path = pipeline.save_raw_html(
        "<html>archive</html>",
        paths=paths,
        year=2026,
        month=7,
    )

    assert path == tmp_path / "custom" / "nested" / "raw" / "2026-07.html"
    assert path.exists()


def test_save_raw_html_preserves_existing_file_on_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = DataPaths.from_root(tmp_path)

    paths.raw_directory.mkdir(
        parents=True,
    )

    existing_file = paths.raw_html_path(
        2026,
        7,
    )

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
        pipeline.save_raw_html(
            "<html>new</html>",
            paths=paths,
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
    paths = DataPaths.from_root(tmp_path)

    paths.raw_directory.mkdir(
        parents=True,
    )

    cached_file = paths.raw_html_path(
        2026,
        7,
    )

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
        pipeline,
        "download_archive_page",
        fake_download_archive_page,
    )

    with requests.Session() as session:
        result = pipeline.download_month(
            2026,
            7,
            paths=paths,
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
    paths = DataPaths.from_root(tmp_path)

    paths.raw_directory.mkdir(
        parents=True,
    )

    cached_file = paths.raw_html_path(
        2026,
        7,
    )

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
        pipeline,
        "download_archive_page",
        fake_download_archive_page,
    )

    with requests.Session() as session:
        result = pipeline.download_month(
            2026,
            7,
            paths=paths,
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


def test_download_month_writes_into_a_custom_data_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = DataPaths.from_root(tmp_path / "elsewhere")

    def fake_download_archive_page(
        year: int,
        month: int,
        *,
        session: requests.Session | None = None,
    ) -> str:
        return "<html>downloaded</html>"

    monkeypatch.setattr(
        pipeline,
        "download_archive_page",
        fake_download_archive_page,
    )

    with requests.Session() as session:
        result = pipeline.download_month(
            2026,
            7,
            paths=paths,
            session=session,
        )

    assert result == tmp_path / "elsewhere" / "raw" / "2026-07.html"

    assert (
        result.read_text(
            encoding="utf-8",
        )
        == "<html>downloaded</html>"
    )


def test_process_month_parses_cached_html(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = DataPaths.from_root(tmp_path)

    extraction = make_extraction(
        105,
        date(2026, 7, 2),
    )

    def fake_download_month(
        year: int,
        month: int,
        *,
        paths: DataPaths,
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
        pipeline,
        "download_month",
        fake_download_month,
    )

    monkeypatch.setattr(
        pipeline,
        "parse_archive_page",
        fake_parse_archive_page,
    )

    with requests.Session() as session:
        result = pipeline.process_month(
            2026,
            7,
            paths=paths,
            session=session,
        )

    assert result == [extraction]


def test_process_month_rejects_extractions_outside_requested_month(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = DataPaths.from_root(tmp_path)

    wrong_month_extraction = make_extraction(
        105,
        date(2026, 8, 2),
    )

    def fake_download_month(
        year: int,
        month: int,
        *,
        paths: DataPaths,
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
        pipeline,
        "download_month",
        fake_download_month,
    )

    monkeypatch.setattr(
        pipeline,
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
        pipeline.process_month(
            2026,
            7,
            paths=paths,
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
    paths = DataPaths.from_root(tmp_path)

    def fake_download_month(
        year: int,
        month: int,
        *,
        paths: DataPaths,
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
        pipeline,
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
        pipeline.process_month(
            2026,
            7,
            paths=paths,
            session=session,
        )


def test_download_interval_reports_conflicting_rows_as_month_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = DataPaths.from_root(tmp_path)

    def fake_download_month(
        year: int,
        month: int,
        *,
        paths: DataPaths,
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
        pipeline,
        "download_month",
        fake_download_month,
    )

    extractions, failures = pipeline.download_interval(
        2026,
        7,
        2026,
        7,
        paths=paths,
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

    result = pipeline.deduplicate_extractions(
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
        pipeline.deduplicate_extractions(
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

    result = pipeline.deduplicate_extractions(
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
        pipeline.ExtractionConflictError,
        match="conflicting payloads",
    ) as exc_info:
        pipeline.deduplicate_extractions(
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

    with pytest.raises(pipeline.ExtractionConflictError):
        pipeline.deduplicate_extractions(
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

    result = pipeline.deduplicate_extractions(
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

    result = pipeline.save_extractions_csv(
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


def test_save_extractions_csv_creates_a_missing_output_directory(
    tmp_path: Path,
) -> None:
    paths = DataPaths.from_root(tmp_path / "custom")

    extraction = make_extraction(
        105,
        date(2026, 7, 2),
    )

    result = pipeline.save_extractions_csv(
        [extraction],
        output_path=paths.extractions_csv,
    )

    assert result == tmp_path / "custom" / "processed" / "extractions.csv"
    assert result.exists()


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
        pipeline.save_extractions_csv(
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
        pipeline.iter_year_months(
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
        pipeline.iter_year_months(
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
        pipeline.iter_year_months(
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
        pipeline.validate_interval(
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
        pipeline.validate_interval(
            2026,
            7,
            2025,
            12,
        )


def test_validate_interval_accepts_valid_interval() -> None:
    pipeline.validate_interval(
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
        pipeline.validate_interval(
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
        pipeline.validate_interval(
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
        pipeline,
        date(2026, 6, 15),
    )

    pipeline.validate_interval(
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
        pipeline,
        date(2026, 6, 15),
    )

    pipeline.validate_interval(
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
        pipeline,
        date(2026, 6, 15),
    )

    with pytest.raises(
        ValueError,
        match="end year/month must not be in the future",
    ):
        pipeline.validate_interval(
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
        pipeline,
        date(2026, 6, 15),
    )

    with pytest.raises(
        ValueError,
        match="start year/month must not be in the future",
    ):
        pipeline.validate_interval(
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
        pipeline,
        date(2026, 12, 15),
    )

    pipeline.validate_interval(
        2026,
        1,
        2026,
        12,
    )

    with pytest.raises(
        ValueError,
        match="end year must be between",
    ):
        pipeline.validate_interval(
            2026,
            1,
            2027,
            1,
        )


def test_download_interval_collects_extractions(
    tmp_path: Path,
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
        paths: DataPaths,
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
        pipeline,
        "process_month",
        fake_process_month,
    )

    extractions, failures = pipeline.download_interval(
        2024,
        1,
        2024,
        2,
        paths=DataPaths.from_root(tmp_path),
    )

    assert extractions == [
        january,
        february,
    ]

    assert failures == []


def test_download_interval_forwards_the_configured_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_paths = DataPaths.from_root(tmp_path / "custom")

    seen_paths: list[DataPaths] = []

    def fake_process_month(
        year: int,
        month: int,
        *,
        paths: DataPaths,
        session: requests.Session,
        force: bool = False,
    ) -> list[Extraction]:
        seen_paths.append(paths)

        return []

    monkeypatch.setattr(
        pipeline,
        "process_month",
        fake_process_month,
    )

    pipeline.download_interval(
        2024,
        1,
        2024,
        2,
        paths=expected_paths,
    )

    assert seen_paths == [
        expected_paths,
        expected_paths,
    ]


def test_download_interval_raises_on_conflicting_payloads(
    tmp_path: Path,
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
        paths: DataPaths,
        session: requests.Session,
        force: bool = False,
    ) -> list[Extraction]:
        if month == 1:
            return [january]

        return [conflicting_january]

    monkeypatch.setattr(
        pipeline,
        "process_month",
        fake_process_month,
    )

    with pytest.raises(
        pipeline.ExtractionConflictError,
        match="conflicting payloads",
    ):
        pipeline.download_interval(
            2024,
            1,
            2024,
            2,
            paths=DataPaths.from_root(tmp_path),
        )


def test_download_interval_continues_after_failed_month(
    tmp_path: Path,
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
        paths: DataPaths,
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
        pipeline,
        "process_month",
        fake_process_month,
    )

    extractions, failures = pipeline.download_interval(
        2024,
        1,
        2024,
        3,
        paths=DataPaths.from_root(tmp_path),
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
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_process_month(
        year: int,
        month: int,
        *,
        paths: DataPaths,
        session: requests.Session,
        force: bool = False,
    ) -> list[Extraction]:
        raise ScrapingError("invalid archive")

    monkeypatch.setattr(
        pipeline,
        "process_month",
        fake_process_month,
    )

    extractions, failures = pipeline.download_interval(
        2024,
        1,
        2024,
        1,
        paths=DataPaths.from_root(tmp_path),
    )

    assert extractions == []
    assert len(failures) == 1

    assert failures[0] == (
        2024,
        1,
        "invalid archive",
    )


def test_count_csv_rows_returns_none_for_missing_file(
    tmp_path: Path,
) -> None:
    assert pipeline.count_csv_rows(tmp_path / "absent.csv") is None


def test_count_csv_rows_excludes_the_header(
    tmp_path: Path,
) -> None:
    path = tmp_path / "extractions.csv"

    path.write_text(
        "contest_number\n1\n2\n3\n",
        encoding="utf-8",
    )

    assert pipeline.count_csv_rows(path) == 3


def test_remove_partial_extractions_csv_deletes_existing_file(
    tmp_path: Path,
) -> None:
    partial_csv = tmp_path / "extractions.partial.csv"
    partial_csv.write_text(
        "contest_number\n1\n",
        encoding="utf-8",
    )

    assert pipeline.remove_partial_extractions_csv(partial_csv) is True
    assert not partial_csv.exists()


def test_remove_partial_extractions_csv_ignores_missing_file(
    tmp_path: Path,
) -> None:
    partial_csv = tmp_path / "extractions.partial.csv"

    assert pipeline.remove_partial_extractions_csv(partial_csv) is False


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
        removed = pipeline.remove_partial_extractions_csv(partial_csv)

    assert removed is False
    assert partial_csv.exists()
    assert "Could not remove stale partial CSV" in caplog.text
