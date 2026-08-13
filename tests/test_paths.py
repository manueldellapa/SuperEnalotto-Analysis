"""Tests for the configurable data directory layout."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from superenalotto import paths as paths_module
from superenalotto.constants import PROJECT_ROOT
from superenalotto.paths import DataPaths, default_data_directory


def test_default_data_directory_uses_the_source_checkout() -> None:
    assert default_data_directory() == PROJECT_ROOT / "data"


def test_default_data_directory_falls_back_to_cwd_outside_a_checkout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed_root = tmp_path / "site-packages"
    installed_root.mkdir()

    working_directory = tmp_path / "workspace"
    working_directory.mkdir()

    monkeypatch.setattr(
        paths_module,
        "PROJECT_ROOT",
        installed_root,
    )

    monkeypatch.chdir(working_directory)

    assert default_data_directory() == working_directory / "data"


def test_data_paths_derive_subdirectories_from_the_root(
    tmp_path: Path,
) -> None:
    paths = DataPaths.from_root(tmp_path)

    assert paths.root == tmp_path
    assert paths.raw_directory == tmp_path / "raw"
    assert paths.processed_directory == tmp_path / "processed"


def test_data_paths_derive_dataset_files_from_the_root(
    tmp_path: Path,
) -> None:
    paths = DataPaths.from_root(tmp_path)

    assert paths.extractions_csv == tmp_path / "processed" / "extractions.csv"

    assert (
        paths.partial_extractions_csv
        == tmp_path / "processed" / "extractions.partial.csv"
    )


def test_data_paths_build_raw_html_path(
    tmp_path: Path,
) -> None:
    paths = DataPaths.from_root(tmp_path)

    assert (
        paths.raw_html_path(
            2026,
            7,
        )
        == tmp_path / "raw" / "2026-07.html"
    )


def test_data_paths_accept_a_string_root(
    tmp_path: Path,
) -> None:
    paths = DataPaths.from_root(str(tmp_path))

    assert paths.root == tmp_path


def test_data_paths_expand_a_user_relative_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "HOME",
        str(tmp_path),
    )

    paths = DataPaths.from_root("~/lotto-data")

    assert paths.root == tmp_path / "lotto-data"


def test_data_paths_default_matches_the_default_data_directory() -> None:
    assert DataPaths.default().root == default_data_directory()


def test_data_paths_are_immutable(
    tmp_path: Path,
) -> None:
    paths = DataPaths.from_root(tmp_path)

    with pytest.raises(dataclasses.FrozenInstanceError):
        paths.root = tmp_path / "elsewhere"  # type: ignore[misc]
