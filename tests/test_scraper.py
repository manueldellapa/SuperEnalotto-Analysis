from datetime import date

import pytest
import requests
from requests.adapters import HTTPAdapter

from superenalotto import scraper
from superenalotto.constants import (
    HTTP_BACKOFF_FACTOR,
    HTTP_RETRIES,
    HTTP_RETRY_STATUS_CODES,
)
from superenalotto.models import Extraction
from superenalotto.scraper import (
    ScrapingError,
    build_archive_url,
    create_http_session,
    parse_archive_page,
)

SINGLE_EXTRACTION_HTML = """
<!DOCTYPE html>
<html lang="it">
<body>
    <table>
        <thead>
            <tr>
                <th>Concorso</th>
                <th>Combinazione vincente</th>
                <th>Jolly</th>
                <th>SuperStar</th>
                <th>Dettagli</th>
            </tr>
        </thead>

        <tbody>
            <tr>
                <td>
                    <span>Concorso</span>
                    <span>Nº 105</span>
                    <span>del 2 Luglio 2026</span>
                </td>

                <td>
                    <span>4</span>
                    <span>17</span>
                    <span>19</span>
                    <span>23</span>
                    <span>47</span>
                    <span>59</span>
                </td>

                <td>
                    <span>51</span>
                </td>

                <td>
                    <span>82</span>
                </td>

                <td>
                    <a href="#">Dettagli</a>
                </td>
            </tr>
        </tbody>
    </table>
</body>
</html>
"""


MULTIPLE_EXTRACTIONS_HTML = """
<!DOCTYPE html>
<html lang="it">
<body>
    <table>
        <tbody>
            <tr>
                <td>Concorso Nº 106 del 3 Luglio 2026</td>
                <td>22 26 30 40 68 86</td>
                <td>72</td>
                <td>48</td>
                <td>Dettagli</td>
            </tr>

            <tr>
                <td>Concorso Nº 105 del 2 Luglio 2026</td>
                <td>4 17 19 23 47 59</td>
                <td>51</td>
                <td>82</td>
                <td>Dettagli</td>
            </tr>
        </tbody>
    </table>
</body>
</html>
"""


def test_build_archive_url() -> None:
    assert (
        build_archive_url(2026, 7)
        == "https://www.superenalotto.it/archivio-estrazioni/2026/luglio"
    )


@pytest.mark.parametrize(
    "month",
    [
        0,
        13,
        -1,
    ],
)
def test_build_archive_url_rejects_invalid_month(
    month: int,
) -> None:
    with pytest.raises(ValueError):
        build_archive_url(2026, month)


def test_parse_archive_page_single_extraction() -> None:
    extractions = parse_archive_page(SINGLE_EXTRACTION_HTML)

    assert extractions == [
        Extraction(
            contest_number=105,
            extraction_date=date(2026, 7, 2),
            numbers=(4, 17, 19, 23, 47, 59),
            jolly=51,
            superstar=82,
        )
    ]


def test_parse_archive_page_multiple_extractions() -> None:
    extractions = parse_archive_page(MULTIPLE_EXTRACTIONS_HTML)

    assert len(extractions) == 2

    assert extractions[0].contest_number == 105
    assert extractions[1].contest_number == 106


def test_parse_archive_page_sorts_by_date() -> None:
    extractions = parse_archive_page(MULTIPLE_EXTRACTIONS_HTML)

    assert [extraction.extraction_date for extraction in extractions] == [
        date(2026, 7, 2),
        date(2026, 7, 3),
    ]


def test_parse_archive_page_rejects_empty_page() -> None:
    with pytest.raises(
        ScrapingError,
        match="No SuperEnalotto contests found",
    ):
        parse_archive_page("<html><body></body></html>")


def test_parse_archive_page_rejects_invalid_main_numbers() -> None:
    html = """
    <table>
        <tr>
            <td>Concorso Nº 105 del 2 Luglio 2026</td>
            <td>4 17 19 23 47</td>
            <td>51</td>
            <td>82</td>
            <td>Dettagli</td>
        </tr>
    </table>
    """

    with pytest.raises(
        ScrapingError,
        match="expected 6 main numbers",
    ):
        parse_archive_page(html)


def test_parse_archive_page_rejects_invalid_jolly() -> None:
    html = """
    <table>
        <tr>
            <td>Concorso Nº 105 del 2 Luglio 2026</td>
            <td>4 17 19 23 47 59</td>
            <td>51 52</td>
            <td>82</td>
            <td>Dettagli</td>
        </tr>
    </table>
    """

    with pytest.raises(
        ScrapingError,
        match="expected 1 Jolly number",
    ):
        parse_archive_page(html)


def test_parse_archive_page_rejects_invalid_superstar() -> None:
    html = """
    <table>
        <tr>
            <td>Concorso Nº 105 del 2 Luglio 2026</td>
            <td>4 17 19 23 47 59</td>
            <td>51</td>
            <td></td>
            <td>Dettagli</td>
        </tr>
    </table>
    """

    with pytest.raises(
        ScrapingError,
        match="expected 1 SuperStar number",
    ):
        parse_archive_page(html)


def test_parse_archive_page_rejects_semantically_invalid_row() -> None:
    html = """
    <table>
        <tr>
            <td>Concorso Nº 105 del 2 Luglio 2026</td>
            <td>4 17 19 23 47 47</td>
            <td>51</td>
            <td>82</td>
            <td>Dettagli</td>
        </tr>
    </table>
    """

    with pytest.raises(
        ScrapingError,
        match="Contest 105",
    ):
        parse_archive_page(html)


TWO_TABLES_HTML = """
<!DOCTYPE html>
<html lang="it">
<body>
    <table class="superenalotto-extraction-archive__details__table">
        <tbody>
            <tr>
                <td>Concorso Nº 105 del 2 Luglio 2026</td>
                <td>4 17 19 23 47 59</td>
                <td>51</td>
                <td>82</td>
                <td>Dettagli</td>
            </tr>
        </tbody>
    </table>

    <table>
        <tbody>
            <tr>
                <td>Concorso Nº 999 del 9 Luglio 2026</td>
                <td>1 2 3 4 5 6</td>
                <td>7</td>
                <td>8</td>
                <td>Dettagli</td>
            </tr>
        </tbody>
    </table>
</body>
</html>
"""


def test_parse_archive_page_ignores_rows_outside_results_table() -> None:
    extractions = parse_archive_page(TWO_TABLES_HTML)

    assert len(extractions) == 1
    assert extractions[0].contest_number == 105


def test_parse_archive_page_accepts_period_abbreviation() -> None:
    html = """
    <table>
        <tr>
            <td>Concorso N.105 del 2 Luglio 2026</td>
            <td>4 17 19 23 47 59</td>
            <td>51</td>
            <td>82</td>
            <td>Dettagli</td>
        </tr>
    </table>
    """

    extractions = parse_archive_page(html)

    assert len(extractions) == 1
    assert extractions[0].contest_number == 105


def test_create_http_session_configures_retries() -> None:
    session = create_http_session()

    try:
        adapter = session.get_adapter("https://")

        assert isinstance(adapter, HTTPAdapter)

        retry = adapter.max_retries

        assert retry.total == HTTP_RETRIES
        assert retry.connect == HTTP_RETRIES
        assert retry.read == HTTP_RETRIES
        assert retry.status == HTTP_RETRIES
        assert retry.backoff_factor == HTTP_BACKOFF_FACTOR
        assert retry.status_forcelist == HTTP_RETRY_STATUS_CODES
    finally:
        session.close()


def test_get_month_extractions_composes_download_and_parse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_download_archive_page(
        year: int,
        month: int,
        *,
        session: requests.Session | None = None,
    ) -> str:
        assert year == 2026
        assert month == 7

        return SINGLE_EXTRACTION_HTML

    monkeypatch.setattr(
        scraper,
        "download_archive_page",
        fake_download_archive_page,
    )

    extractions = scraper.get_month_extractions(
        2026,
        7,
    )

    assert len(extractions) == 1
    assert extractions[0].contest_number == 105


def test_parse_archive_page_removes_duplicate_extractions() -> None:
    html = """
    <table>
        <tr>
            <td>Concorso Nº 105 del 2 Luglio 2026</td>
            <td>4 17 19 23 47 59</td>
            <td>51</td>
            <td>82</td>
            <td>Dettagli</td>
        </tr>

        <tr>
            <td>Concorso Nº 105 del 2 Luglio 2026</td>
            <td>4 17 19 23 47 59</td>
            <td>51</td>
            <td>82</td>
            <td>Dettagli</td>
        </tr>
    </table>
    """

    extractions = parse_archive_page(html)

    assert len(extractions) == 1
    assert extractions[0].contest_number == 105
