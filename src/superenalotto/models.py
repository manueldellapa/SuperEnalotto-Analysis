"""Domain models for SuperEnalotto extractions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class Extraction:
    """Represent a single SuperEnalotto extraction."""

    contest_number: int
    extraction_date: date
    numbers: tuple[int, int, int, int, int, int]
    jolly: int
    superstar: int

    CSV_FIELDNAMES: ClassVar[tuple[str, ...]] = (
        "contest_number",
        "extraction_date",
        "number_1",
        "number_2",
        "number_3",
        "number_4",
        "number_5",
        "number_6",
        "jolly",
        "superstar",
    )

    def as_dict(self) -> dict[str, object]:
        """Return the extraction as a serializable dictionary."""
        return {
            "contest_number": self.contest_number,
            "extraction_date": self.extraction_date.isoformat(),
            "number_1": self.numbers[0],
            "number_2": self.numbers[1],
            "number_3": self.numbers[2],
            "number_4": self.numbers[3],
            "number_5": self.numbers[4],
            "number_6": self.numbers[5],
            "jolly": self.jolly,
            "superstar": self.superstar,
        }
