"""Validation utilities for SuperEnalotto extraction data."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from .constants import (
    MAIN_NUMBERS_COUNT,
    MAX_NUMBER,
    MIN_NUMBER,
    VALID_NUMBER_RANGE,
)
from .models import Extraction


def validate_number(number: int, *, field_name: str = "number") -> None:
    """Validate a single SuperEnalotto number.

    Args:
        number: Number to validate.
        field_name: Human-readable field name used in error messages.

    Raises:
        TypeError: If the value is not an integer.
        ValueError: If the value is outside the valid SuperEnalotto range.
    """
    if not isinstance(number, int) or isinstance(number, bool):
        raise TypeError(f"{field_name} must be an integer, got {type(number).__name__}")

    if number not in VALID_NUMBER_RANGE:
        raise ValueError(
            f"{field_name} must be between {MIN_NUMBER} and {MAX_NUMBER}, got {number}"
        )


def validate_numbers(numbers: Iterable[int]) -> None:
    """Validate the six main numbers of a SuperEnalotto extraction.

    Args:
        numbers: Main extraction numbers.

    Raises:
        TypeError: If one of the values is not an integer.
        ValueError: If the amount of numbers is invalid, a number is outside
            the allowed range, or duplicate numbers are present.
    """
    values = tuple(numbers)

    if len(values) != MAIN_NUMBERS_COUNT:
        raise ValueError(
            f"Expected exactly {MAIN_NUMBERS_COUNT} main numbers, got {len(values)}"
        )

    for index, number in enumerate(values, start=1):
        validate_number(
            number,
            field_name=f"number_{index}",
        )

    if len(set(values)) != MAIN_NUMBERS_COUNT:
        raise ValueError("Main extraction numbers must be unique")


def validate_jolly(jolly: int) -> None:
    """Validate the Jolly number."""
    validate_number(
        jolly,
        field_name="jolly",
    )


def validate_superstar(superstar: int) -> None:
    """Validate the SuperStar number."""
    validate_number(
        superstar,
        field_name="superstar",
    )


def validate_contest_number(contest_number: int) -> None:
    """Validate the contest identifier.

    Args:
        contest_number: Contest number to validate.

    Raises:
        TypeError: If the contest number is not an integer.
        ValueError: If the contest number is not positive.
    """
    if not isinstance(contest_number, int) or isinstance(contest_number, bool):
        raise TypeError(
            f"contest_number must be an integer, got {type(contest_number).__name__}"
        )

    if contest_number <= 0:
        raise ValueError(f"contest_number must be positive, got {contest_number}")


def validate_extraction_date(extraction_date: date) -> None:
    """Validate the extraction date."""
    if type(extraction_date) is not date:
        raise TypeError(
            "extraction_date must be a date instance, "
            f"got {type(extraction_date).__name__}"
        )


def validate_extraction(extraction: Extraction) -> None:
    """Validate a complete SuperEnalotto extraction.

    Args:
        extraction: Extraction to validate.

    Raises:
        TypeError: If one of the fields has an invalid type.
        ValueError: If one of the fields contains an invalid value.
    """
    if not isinstance(extraction, Extraction):
        raise TypeError(
            "extraction must be an Extraction instance, "
            f"got {type(extraction).__name__}"
        )

    validate_contest_number(extraction.contest_number)
    validate_extraction_date(extraction.extraction_date)
    validate_numbers(extraction.numbers)
    validate_jolly(extraction.jolly)
    validate_superstar(extraction.superstar)
