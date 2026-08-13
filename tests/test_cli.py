"""Tests for the packaged SuperEnalotto downloader command-line interface."""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from datetime import date
from pathlib import Path

import pytest

from superenalotto import cli
from superenalotto.models import Extraction
from superenalotto.paths import DataPaths, default_data_directory
from superenalotto.pipeline import ExtractionConflictError
from tests.support import freeze_today, make_extraction


def build_fake_download_interval(
    extractions: list[Extraction],
    failures: list[tuple[int, int, str]],
    *,
    seen_paths: list[DataPaths] | None = None,
) -> object:
    """Build a download_interval stub returning a fixed outcome."""

    def fake_download_interval(
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        *,
        paths: DataPaths,
        force: bool = False,
    ) -> tuple[list[Extraction], list[tuple[int, int, str]]]:
        if seen_paths is not None:
            seen_paths.append(paths)

        return extractions, failures

    return fake_download_interval


def test_build_argument_parser_defaults() -> None:
    parser = cli.build_argument_parser()

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
    assert args.data_dir is None
    assert args.force is False
    assert args.verbose is False


def test_build_argument_parser_parses_full_arguments() -> None:
    parser = cli.build_argument_parser()

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
            "--data-dir",
            "/tmp/lotto",
            "--force",
            "--verbose",
        ]
    )

    assert args.start_year == 2024
    assert args.start_month == 3
    assert args.end_year == 2026
    assert args.end_month == 7
    assert args.data_dir == Path("/tmp/lotto")
    assert args.force is True
    assert args.verbose is True


def test_resolve_interval_single_month() -> None:
    args = argparse.Namespace(
        start_year=2026,
        start_month=7,
        end_year=None,
        end_month=None,
    )

    assert cli.resolve_interval(args) == (
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
        cli,
        date(2026, 6, 15),
    )

    args = argparse.Namespace(
        start_year=2024,
        start_month=7,
        end_year=2025,
        end_month=None,
    )

    assert cli.resolve_interval(args) == (
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
        cli,
        date(2026, 6, 15),
    )

    args = argparse.Namespace(
        start_year=2024,
        start_month=7,
        end_year=2026,
        end_month=None,
    )

    assert cli.resolve_interval(args) == (
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
        cli,
        date(2026, 6, 15),
    )

    args = argparse.Namespace(
        start_year=2026,
        start_month=1,
        end_year=2026,
        end_month=3,
    )

    assert cli.resolve_interval(args) == (
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

    assert cli.resolve_interval(args) == (
        2024,
        2,
        2026,
        7,
    )


def test_resolve_data_paths_falls_back_to_the_default_root() -> None:
    args = argparse.Namespace(
        data_dir=None,
    )

    assert cli.resolve_data_paths(args).root == default_data_directory()


def test_resolve_data_paths_uses_an_explicit_root(
    tmp_path: Path,
) -> None:
    args = argparse.Namespace(
        data_dir=tmp_path / "custom",
    )

    paths = cli.resolve_data_paths(args)

    assert paths.root == tmp_path / "custom"
    assert paths.raw_directory == tmp_path / "custom" / "raw"
    assert paths.processed_directory == tmp_path / "custom" / "processed"


def test_main_returns_zero_on_full_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "superenalotto-download",
            "--start-year",
            "2026",
            "--start-month",
            "7",
            "--end-month",
            "7",
            "--data-dir",
            str(tmp_path),
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
        paths: DataPaths,
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
        cli,
        "download_interval",
        fake_download_interval,
    )

    exit_code = cli.main()

    assert exit_code == 0
    assert (tmp_path / "processed" / "extractions.csv").exists()


def test_main_writes_into_a_custom_data_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_dir = tmp_path / "somewhere" / "else"

    seen_paths: list[DataPaths] = []

    extraction = make_extraction(
        105,
        date(2026, 7, 2),
    )

    monkeypatch.setattr(
        cli,
        "download_interval",
        build_fake_download_interval(
            [extraction],
            [],
            seen_paths=seen_paths,
        ),
    )

    exit_code = cli.main(
        [
            "--start-year",
            "2026",
            "--start-month",
            "7",
            "--end-month",
            "7",
            "--data-dir",
            str(data_dir),
        ]
    )

    assert exit_code == 0
    assert seen_paths == [DataPaths.from_root(data_dir)]

    csv_path = data_dir / "processed" / "extractions.csv"

    assert csv_path.exists()

    with csv_path.open(
        encoding="utf-8",
        newline="",
    ) as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert len(rows) == 1
    assert rows[0]["contest_number"] == "105"


def test_main_returns_one_on_partial_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli,
        "download_interval",
        build_fake_download_interval(
            [],
            [(2026, 7, "boom")],
        ),
    )

    exit_code = cli.main(
        [
            "--start-year",
            "2026",
            "--start-month",
            "7",
            "--end-month",
            "7",
            "--data-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 1


def test_main_returns_one_on_invalid_interval(
    tmp_path: Path,
) -> None:
    exit_code = cli.main(
        [
            "--start-year",
            "9999",
            "--data-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 1


def test_main_preserves_canonical_csv_on_conflicting_payloads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    paths = DataPaths.from_root(tmp_path)

    paths.processed_directory.mkdir(
        parents=True,
    )

    canonical_csv = paths.extractions_csv
    canonical_csv.write_text(
        "contest_number\n1\n2\n3\n",
        encoding="utf-8",
    )

    def fake_download_interval(
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        *,
        paths: DataPaths,
        force: bool = False,
    ) -> tuple[list[Extraction], list[tuple[int, int, str]]]:
        raise ExtractionConflictError(
            "Contest 105 on 2026-07-02 has conflicting payloads"
        )

    monkeypatch.setattr(
        cli,
        "download_interval",
        fake_download_interval,
    )

    with caplog.at_level(logging.ERROR):
        exit_code = cli.main(
            [
                "--start-year",
                "2026",
                "--start-month",
                "7",
                "--end-month",
                "7",
                "--data-dir",
                str(tmp_path),
            ]
        )

    assert exit_code == 1
    assert "Data integrity error" in caplog.text
    assert "conflicting payloads" in caplog.text

    assert canonical_csv.read_text(encoding="utf-8") == "contest_number\n1\n2\n3\n"
    assert not paths.partial_extractions_csv.exists()


def test_main_preserves_canonical_csv_on_partial_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    paths = DataPaths.from_root(tmp_path)

    paths.processed_directory.mkdir(
        parents=True,
    )

    existing_csv = paths.extractions_csv
    existing_csv.write_text(
        "contest_number\n1\n2\n3\n",
        encoding="utf-8",
    )

    extraction = make_extraction(
        105,
        date(2026, 7, 2),
    )

    monkeypatch.setattr(
        cli,
        "download_interval",
        build_fake_download_interval(
            [extraction],
            [(2026, 7, "boom")],
        ),
    )

    with caplog.at_level(logging.WARNING):
        exit_code = cli.main(
            [
                "--start-year",
                "2026",
                "--start-month",
                "7",
                "--end-month",
                "7",
                "--data-dir",
                str(tmp_path),
            ]
        )

    assert exit_code == 1

    assert (
        existing_csv.read_text(
            encoding="utf-8",
        )
        == "contest_number\n1\n2\n3\n"
    )

    partial_csv = paths.partial_extractions_csv

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
    paths = DataPaths.from_root(tmp_path)

    extraction = make_extraction(
        105,
        date(2026, 7, 2),
    )

    monkeypatch.setattr(
        cli,
        "download_interval",
        build_fake_download_interval(
            [extraction],
            [(2026, 7, "boom")],
        ),
    )

    with caplog.at_level(logging.WARNING):
        exit_code = cli.main(
            [
                "--start-year",
                "2026",
                "--start-month",
                "7",
                "--end-month",
                "7",
                "--data-dir",
                str(tmp_path),
            ]
        )

    assert exit_code == 1
    assert not paths.extractions_csv.exists()
    assert paths.partial_extractions_csv.exists()
    assert "unwritten" in caplog.text


def test_main_removes_stale_partial_csv_on_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = DataPaths.from_root(tmp_path)

    paths.processed_directory.mkdir(
        parents=True,
    )

    stale_partial = paths.partial_extractions_csv
    stale_partial.write_text(
        "contest_number\n999\n",
        encoding="utf-8",
    )

    extraction = make_extraction(
        105,
        date(2026, 7, 2),
    )

    monkeypatch.setattr(
        cli,
        "download_interval",
        build_fake_download_interval(
            [extraction],
            [],
        ),
    )

    exit_code = cli.main(
        [
            "--start-year",
            "2026",
            "--start-month",
            "7",
            "--end-month",
            "7",
            "--data-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    assert paths.extractions_csv.exists()
    assert not stale_partial.exists()


def test_main_keeps_partial_csv_when_run_has_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = DataPaths.from_root(tmp_path)

    extraction = make_extraction(
        105,
        date(2026, 7, 2),
    )

    monkeypatch.setattr(
        cli,
        "download_interval",
        build_fake_download_interval(
            [extraction],
            [(2026, 7, "boom")],
        ),
    )

    exit_code = cli.main(
        [
            "--start-year",
            "2026",
            "--start-month",
            "7",
            "--end-month",
            "7",
            "--data-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 1
    assert paths.partial_extractions_csv.exists()


def test_main_returns_one_on_unexpected_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def exploding_download_interval(
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        *,
        paths: DataPaths,
        force: bool = False,
    ) -> tuple[list[Extraction], list[tuple[int, int, str]]]:
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(
        cli,
        "download_interval",
        exploding_download_interval,
    )

    with caplog.at_level(logging.ERROR):
        exit_code = cli.main(
            [
                "--start-year",
                "2026",
                "--data-dir",
                str(tmp_path),
            ]
        )

    assert exit_code == 1
    assert "Unexpected error" in caplog.text
