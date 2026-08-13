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
