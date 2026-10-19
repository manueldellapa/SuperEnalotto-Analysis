"""Shared helpers for the test suite."""

from __future__ import annotations

from datetime import date
from types import ModuleType
from typing import Self

import pytest

from superenalotto.models import Extraction


def freeze_today(
    monkeypatch: pytest.MonkeyPatch,
    module: ModuleType,
    today_value: date,
) -> None:
    """Pin the current date seen by a module that calls date.today()."""

    class FrozenDate(date):
        @classmethod
        def today(cls) -> Self:
            return cls(
                today_value.year,
                today_value.month,
                today_value.day,
            )

    monkeypatch.setattr(
        module,
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


def analysis_extractions() -> list[Extraction]:
    """Return the three unique synthetic contests specified by PRD US-002."""
    return [
        make_extraction(
            1, date(2023, 12, 30), numbers=(1, 2, 3, 4, 5, 6), jolly=7, superstar=1
        ),
        make_extraction(
            1, date(2024, 1, 2), numbers=(1, 2, 7, 8, 9, 10), jolly=3, superstar=3
        ),
        make_extraction(
            2, date(2024, 2, 29), numbers=(1, 11, 12, 13, 14, 15), jolly=2, superstar=1
        ),
    ]
