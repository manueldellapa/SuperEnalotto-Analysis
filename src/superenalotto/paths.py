"""Filesystem layout for cached archive pages and generated datasets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Self

from .constants import (
    DATA_DIRECTORY_NAME,
    EXTRACTIONS_FILE_NAME,
    PARTIAL_EXTRACTIONS_FILE_NAME,
    PROCESSED_DIRECTORY_NAME,
    PROJECT_ROOT,
    RAW_DIRECTORY_NAME,
    RAW_FILE_NAME_TEMPLATE,
)


def default_data_directory() -> Path:
    """Return the data root to use when none was requested explicitly.

    A source checkout keeps its data beside the code, which is where this
    project has always written it. Once the package is installed somewhere
    else, its location says nothing about where the user wants their data, so
    fall back to a "data" directory under the current working directory.
    """
    if (PROJECT_ROOT / "pyproject.toml").is_file():
        return PROJECT_ROOT / DATA_DIRECTORY_NAME

    return Path.cwd() / DATA_DIRECTORY_NAME


@dataclass(frozen=True, slots=True)
class DataPaths:
    """Every path a run reads or writes, all derived from one root.

    Passed explicitly through the pipeline rather than read from module-level
    state, so two runs in one process can target different directories.
    """

    root: Path

    @classmethod
    def from_root(
        cls,
        root: Path | str,
    ) -> Self:
        """Build the layout for an explicitly chosen data root."""
        return cls(
            root=Path(root).expanduser(),
        )

    @classmethod
    def default(cls) -> Self:
        """Build the layout used when no data root was requested."""
        return cls.from_root(
            default_data_directory(),
        )

    @property
    def raw_directory(self) -> Path:
        """Directory holding one cached HTML archive page per month."""
        return self.root / RAW_DIRECTORY_NAME

    @property
    def processed_directory(self) -> Path:
        """Directory holding the generated CSV datasets."""
        return self.root / PROCESSED_DIRECTORY_NAME

    @property
    def extractions_csv(self) -> Path:
        """The canonical dataset, written only by a fully successful run."""
        return self.processed_directory / EXTRACTIONS_FILE_NAME

    @property
    def partial_extractions_csv(self) -> Path:
        """The dataset written instead when a run had failed months."""
        return self.processed_directory / PARTIAL_EXTRACTIONS_FILE_NAME

    def raw_html_path(
        self,
        year: int,
        month: int,
    ) -> Path:
        """Return the cached HTML path for a given year and month."""
        filename = RAW_FILE_NAME_TEMPLATE.format(
            year=year,
            month=month,
        )

        return self.raw_directory / filename
