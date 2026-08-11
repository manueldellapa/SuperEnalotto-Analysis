from datetime import date, datetime

import pytest

from superenalotto.models import Extraction
from superenalotto.validators import (
    validate_contest_number,
    validate_extraction,
    validate_extraction_date,
    validate_jolly,
    validate_number,
    validate_numbers,
    validate_superstar,
)


def test_validate_number_accepts_valid_number() -> None:
    validate_number(1)
    validate_number(45)
    validate_number(90)


@pytest.mark.parametrize(
    "number",
    [
        0,
        -1,
        91,
        100,
    ],
)
def test_validate_number_rejects_out_of_range(number: int) -> None:
    with pytest.raises(ValueError):
        validate_number(number)


@pytest.mark.parametrize(
    "number",
    [
        True,
        False,
        1.5,
        "10",
        None,
    ],
)
def test_validate_number_rejects_invalid_type(number: object) -> None:
    with pytest.raises(TypeError):
        validate_number(number)  # type: ignore[arg-type]


def test_validate_numbers_accepts_valid_sequence() -> None:
    validate_numbers((4, 17, 19, 23, 47, 59))


def test_validate_numbers_accepts_list() -> None:
    validate_numbers([4, 17, 19, 23, 47, 59])


def test_validate_numbers_accepts_generator() -> None:
    numbers = (number for number in (4, 17, 19, 23, 47, 59))

    validate_numbers(numbers)


@pytest.mark.parametrize(
    "numbers",
    [
        (),
        (1,),
        (1, 2, 3, 4, 5),
        (1, 2, 3, 4, 5, 6, 7),
    ],
)
def test_validate_numbers_rejects_invalid_length(
    numbers: tuple[int, ...],
) -> None:
    with pytest.raises(ValueError):
        validate_numbers(numbers)


def test_validate_numbers_rejects_duplicates() -> None:
    with pytest.raises(
        ValueError,
        match="must be unique",
    ):
        validate_numbers((4, 17, 19, 23, 47, 47))


def test_validate_numbers_rejects_out_of_range_number() -> None:
    with pytest.raises(
        ValueError,
        match="number_6",
    ):
        validate_numbers((4, 17, 19, 23, 47, 91))


def test_validate_jolly_accepts_valid_number() -> None:
    validate_jolly(51)


def test_validate_jolly_rejects_invalid_number() -> None:
    with pytest.raises(ValueError):
        validate_jolly(91)


def test_validate_superstar_accepts_valid_number() -> None:
    validate_superstar(82)


def test_validate_superstar_rejects_invalid_number() -> None:
    with pytest.raises(ValueError):
        validate_superstar(0)


def test_validate_contest_number_accepts_positive_integer() -> None:
    validate_contest_number(105)


@pytest.mark.parametrize(
    "contest_number",
    [
        0,
        -1,
        -100,
    ],
)
def test_validate_contest_number_rejects_non_positive(
    contest_number: int,
) -> None:
    with pytest.raises(ValueError):
        validate_contest_number(contest_number)


@pytest.mark.parametrize(
    "contest_number",
    [
        True,
        1.5,
        "105",
        None,
    ],
)
def test_validate_contest_number_rejects_invalid_type(
    contest_number: object,
) -> None:
    with pytest.raises(TypeError):
        validate_contest_number(contest_number)  # type: ignore[arg-type]


def test_validate_extraction_date_accepts_date() -> None:
    validate_extraction_date(date(2026, 7, 2))


@pytest.mark.parametrize(
    "value",
    [
        "2026-07-02",
        20260702,
        None,
    ],
)
def test_validate_extraction_date_rejects_invalid_type(
    value: object,
) -> None:
    with pytest.raises(TypeError):
        validate_extraction_date(value)  # type: ignore[arg-type]


def test_validate_extraction_date_rejects_datetime_instance() -> None:
    with pytest.raises(TypeError):
        validate_extraction_date(datetime(2026, 7, 2, 12, 30))


def test_validate_extraction_accepts_valid_extraction() -> None:
    extraction = Extraction(
        contest_number=105,
        extraction_date=date(2026, 7, 2),
        numbers=(4, 17, 19, 23, 47, 59),
        jolly=51,
        superstar=82,
    )

    validate_extraction(extraction)


def test_validate_extraction_rejects_invalid_object() -> None:
    with pytest.raises(TypeError):
        validate_extraction(object())  # type: ignore[arg-type]
