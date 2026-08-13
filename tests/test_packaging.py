"""Tests for the packaged console-script entry point."""

from __future__ import annotations

import importlib
import inspect
import tomllib
from pathlib import Path
from typing import Any

from scripts import download_extractions
from superenalotto import cli

PYPROJECT_PATH = Path(__file__).resolve().parents[1] / "pyproject.toml"

CONSOLE_SCRIPT_NAME = "superenalotto-download"


def load_project_scripts() -> dict[str, str]:
    """Return the [project.scripts] table declared in pyproject.toml."""
    with PYPROJECT_PATH.open("rb") as pyproject_file:
        pyproject: dict[str, Any] = tomllib.load(pyproject_file)

    scripts: dict[str, str] = pyproject["project"]["scripts"]

    return scripts


def test_pyproject_declares_the_downloader_console_script() -> None:
    assert load_project_scripts() == {
        CONSOLE_SCRIPT_NAME: "superenalotto.cli:main",
    }


def test_declared_entry_point_resolves_to_a_callable() -> None:
    module_name, _, attribute_name = load_project_scripts()[
        CONSOLE_SCRIPT_NAME
    ].partition(":")

    entry_point = getattr(
        importlib.import_module(module_name),
        attribute_name,
    )

    assert entry_point is cli.main
    assert callable(entry_point)


def test_entry_point_runs_without_arguments() -> None:
    """The generated console script calls main() with no arguments."""
    signature = inspect.signature(cli.main)

    assert all(
        parameter.default is not inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )


def test_script_launcher_delegates_to_the_packaged_cli() -> None:
    assert download_extractions.main is cli.main
