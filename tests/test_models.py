from datetime import date

from superenalotto.models import Extraction


def test_extraction_creation() -> None:
    extraction = Extraction(
        contest_number=105,
        extraction_date=date(2026, 7, 2),
        numbers=(4, 17, 19, 23, 47, 59),
        jolly=51,
        superstar=82,
    )

    assert extraction.contest_number == 105
    assert extraction.extraction_date == date(2026, 7, 2)
    assert extraction.numbers == (4, 17, 19, 23, 47, 59)
    assert extraction.jolly == 51
    assert extraction.superstar == 82


def test_extraction_as_dict() -> None:
    extraction = Extraction(
        contest_number=105,
        extraction_date=date(2026, 7, 2),
        numbers=(4, 17, 19, 23, 47, 59),
        jolly=51,
        superstar=82,
    )

    assert extraction.as_dict() == {
        "contest_number": 105,
        "extraction_date": "2026-07-02",
        "number_1": 4,
        "number_2": 17,
        "number_3": 19,
        "number_4": 23,
        "number_5": 47,
        "number_6": 59,
        "jolly": 51,
        "superstar": 82,
    }


def test_extraction_csv_fieldnames_match_as_dict_keys() -> None:
    extraction = Extraction(
        contest_number=105,
        extraction_date=date(2026, 7, 2),
        numbers=(4, 17, 19, 23, 47, 59),
        jolly=51,
        superstar=82,
    )

    assert set(Extraction.CSV_FIELDNAMES) == set(extraction.as_dict().keys())


def test_extraction_is_hashable() -> None:
    extraction = Extraction(
        contest_number=105,
        extraction_date=date(2026, 7, 2),
        numbers=(4, 17, 19, 23, 47, 59),
        jolly=51,
        superstar=82,
    )

    assert extraction in {extraction}
