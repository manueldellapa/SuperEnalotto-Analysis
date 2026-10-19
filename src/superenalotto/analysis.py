"""Pure descriptive statistics for already validated, deduplicated extractions."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Literal

from .constants import MIN_NUMBER, VALID_NUMBER_RANGE
from .models import Extraction

type Category = Literal["main", "jolly", "superstar"]


@dataclass(frozen=True, slots=True)
class Frequency:
    """A number's count and unrounded percentage of contests containing it."""

    number: int
    count: int
    presence_percent: float | None


@dataclass(frozen=True, slots=True)
class FrequencyReport:
    """Statistics over the entire supplied dataset, ordered numerically."""

    category: Category
    extraction_count: int
    first_date: date | None
    last_date: date | None
    frequencies: tuple[Frequency, ...]


def calculate_frequencies(
    extractions: Sequence[Extraction], category: Category = "main"
) -> FrequencyReport:
    """Count one category in a single pass over valid, unique extractions.

    Callers must validate and deduplicate before calling this pure function.
    Main-number positions are pooled; categories never contribute to each other.
    """
    if category not in ("main", "jolly", "superstar"):
        raise ValueError(f"Unknown category: {category}")
    counts = [0] * len(VALID_NUMBER_RANGE)
    first_date: date | None = None
    last_date: date | None = None
    for extraction in extractions:
        values: tuple[int, ...]
        if category == "main":
            values = extraction.numbers
        elif category == "jolly":
            values = (extraction.jolly,)
        else:
            values = (extraction.superstar,)
        for number in values:
            counts[number - MIN_NUMBER] += 1
        day = extraction.extraction_date
        first_date = day if first_date is None else min(first_date, day)
        last_date = day if last_date is None else max(last_date, day)
    total = len(extractions)
    return FrequencyReport(
        category=category,
        extraction_count=total,
        first_date=first_date,
        last_date=last_date,
        frequencies=tuple(
            Frequency(number, count, 100 * count / total if total else None)
            for number, count in zip(VALID_NUMBER_RANGE, counts, strict=True)
        ),
    )
