"""Known-result tests for the pure M0 statistics contract."""

from dataclasses import replace

import pytest

from superenalotto.analysis import Category, calculate_frequencies
from tests.support import analysis_extractions


@pytest.mark.parametrize(
    ("category", "expected", "total", "percent_total"),
    [
        ("main", {1: 3, 2: 2, **dict.fromkeys(range(3, 16), 1)}, 18, 600),
        ("jolly", {2: 1, 3: 1, 7: 1}, 3, 100),
        ("superstar", {1: 2, 3: 1}, 3, 100),
    ],
)
def test_frequencies(
    category: Category, expected: dict[int, int], total: int, percent_total: int
) -> None:
    extractions = analysis_extractions()
    report = calculate_frequencies(extractions, category)
    assert report.category == category
    assert report.extraction_count == 3
    assert report.first_date == extractions[0].extraction_date
    assert report.last_date == extractions[-1].extraction_date
    assert [row.number for row in report.frequencies] == list(range(1, 91))
    assert {row.number: row.count for row in report.frequencies} == {
        number: expected.get(number, 0) for number in range(1, 91)
    }
    assert sum(row.count for row in report.frequencies) == total
    assert sum(row.presence_percent or 0 for row in report.frequencies) == (
        pytest.approx(percent_total)
    )
    for row in report.frequencies:
        assert row.presence_percent == pytest.approx(100 * row.count / 3)
    shuffled = [
        replace(row, numbers=row.numbers[::-1]) for row in reversed(extractions)
    ]
    assert calculate_frequencies(shuffled, category) == report


@pytest.mark.parametrize("category", ["main", "jolly", "superstar"])
def test_empty_frequencies(category: Category) -> None:
    report = calculate_frequencies([], category)
    assert report.extraction_count == 0
    assert report.first_date is report.last_date is None
    assert len(report.frequencies) == 90
    assert all(
        row.count == 0 and row.presence_percent is None for row in report.frequencies
    )
