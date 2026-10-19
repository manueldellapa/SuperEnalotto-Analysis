"""M0 CLI composition, errors, deterministic output and read-only guarantees."""

from dataclasses import replace
from pathlib import Path

import pytest
import requests

from superenalotto import analysis_cli, pipeline
from superenalotto import paths as paths_module
from superenalotto.models import Extraction
from superenalotto.paths import DataPaths
from tests.support import analysis_extractions


def table(output: str) -> list[list[str]]:
    return [line.split() for line in output.splitlines() if line and line[0].isdigit()]


@pytest.mark.parametrize(
    ("category", "first", "second", "total"),
    [
        ("main", "1 3 100.00", "2 2 66.67", 18),
        ("jolly", "1 0 0.00", "2 1 33.33", 3),
        ("superstar", "1 2 66.67", "2 0 0.00", 3),
    ],
)
def test_cli_report_and_read_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    category: str,
    first: str,
    second: str,
    total: int,
) -> None:
    paths = DataPaths.from_root(tmp_path)
    extractions = analysis_extractions()
    pipeline.save_extractions_csv(
        [*extractions, extractions[0]], output_path=paths.extractions_csv
    )
    paths.partial_extractions_csv.write_bytes(b"not a valid CSV")
    paths.raw_directory.mkdir()
    paths.raw_html_path(2024, 1).write_bytes(b"cached")
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    before_entries = sorted(tmp_path.rglob("*"))

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("Analysis must not use HTTP")

    monkeypatch.setattr(pipeline, "create_http_session", forbidden)
    monkeypatch.setattr(requests.sessions.Session, "request", forbidden)
    original_load = pipeline.load_extractions_csv
    reads = 0

    def load_once(*, paths: DataPaths) -> list[Extraction]:
        nonlocal reads
        reads += 1
        return original_load(paths=paths)

    monkeypatch.setattr(analysis_cli, "load_extractions_csv", load_once)
    args = ["--data-dir", str(tmp_path), "--category", category]
    assert analysis_cli.main(args) == 0
    output = capsys.readouterr()
    assert output.err == ""
    assert reads == 1
    assert {p: p.read_bytes() for p in before} == before
    assert sorted(tmp_path.rglob("*")) == before_entries
    assert str(paths.extractions_csv) in output.out
    assert f"Category: {category}" in output.out
    assert "Requested start: unbounded\nRequested end: unbounded" in output.out
    assert "Source dates: 2023-12-30 .. 2024-02-29" in output.out
    assert "Selected dates: 2023-12-30 .. 2024-02-29" in output.out
    assert "N = 3" in output.out
    assert "coverage is not certified" in output.out
    assert "descriptive, not predictions" in output.out
    rows = table(output.out)
    assert len(rows) == 90
    assert rows[0] == first.split()
    assert rows[1] == second.split()
    assert rows[-1] == ["90", "0", "0.00"]
    assert sum(int(row[1]) for row in rows) == total
    if category == "main":
        assert rows[2] == ["3", "1", "33.33"]
    # Same source path, different CSV row ordering: identical report.
    pipeline.save_extractions_csv(
        list(reversed(extractions)), output_path=paths.extractions_csv
    )
    reordered = paths.extractions_csv.read_bytes()
    assert analysis_cli.main(args) == 0
    assert capsys.readouterr().out == output.out
    assert paths.extractions_csv.read_bytes() == reordered
    # Restore the original fixture to compare the complete data tree.
    paths.extractions_csv.write_bytes(before[paths.extractions_csv])
    assert {p: p.read_bytes() for p in before} == before
    assert sorted(tmp_path.rglob("*")) == before_entries


def test_cli_empty(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    paths = DataPaths.from_root(tmp_path)
    pipeline.save_extractions_csv([], output_path=paths.extractions_csv)
    assert analysis_cli.main(["--data-dir", str(tmp_path)]) == 0
    output = capsys.readouterr()
    assert output.err == ""
    assert "Category: main" in output.out
    assert "N = 0" in output.out
    assert "Source dates: N/A .. N/A" in output.out
    assert "Selected dates: N/A .. N/A" in output.out
    assert "No extractions in selected period" in output.out
    assert table(output.out) == [[str(n), "0", "N/A"] for n in range(1, 91)]


@pytest.mark.parametrize(
    ("args", "code"),
    [
        (["--help"], 0),
        (["--category", "other"], 2),
        (["--unknown"], 2),
        (["--start-date", "2024-01-01"], 2),
        (["--end-date", "2024-01-01"], 2),
        (["--order", "number"], 2),
        (["--top", "1"], 2),
    ],
)
def test_cli_parser(args: list[str], code: int) -> None:
    with pytest.raises(SystemExit) as error:
        analysis_cli.main(args)
    assert error.value.code == code


@pytest.mark.parametrize(
    "failure", ["missing", "invalid", "conflict", "unreadable", "utf8"]
)
def test_cli_errors_preserve_data(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    paths = DataPaths.from_root(tmp_path)
    rows = analysis_extractions()
    pipeline.save_extractions_csv(rows, output_path=paths.partial_extractions_csv)
    if failure == "invalid":
        paths.extractions_csv.write_text("wrong\n", encoding="utf-8")
    elif failure == "conflict":
        pipeline.save_extractions_csv(
            [*rows, replace(rows[0], superstar=90)], output_path=paths.extractions_csv
        )
    elif failure == "utf8":
        paths.extractions_csv.write_bytes(b"\xff")
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    entries = sorted(tmp_path.rglob("*"))
    if failure == "unreadable":

        def deny_read(*args: object, **kwargs: object) -> None:
            raise PermissionError("read denied")

        monkeypatch.setattr(Path, "open", deny_read)
    assert analysis_cli.main(["--data-dir", str(tmp_path)]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "Error:" in output.err
    assert str(paths.extractions_csv) in output.err
    assert "Traceback" not in output.err
    monkeypatch.undo()
    assert {p: p.read_bytes() for p in before} == before
    assert sorted(tmp_path.rglob("*")) == entries


def test_cli_missing_root(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = tmp_path / "absent"
    assert analysis_cli.main(["--data-dir", str(root)]) == 1
    assert capsys.readouterr().out == ""
    assert not root.exists()


@pytest.mark.parametrize("installed", [False, True])
def test_cli_default_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    installed: bool,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    if not installed:
        (project / "pyproject.toml").touch()
    monkeypatch.setattr(paths_module, "PROJECT_ROOT", project)
    monkeypatch.chdir(tmp_path)
    paths = DataPaths.default()
    pipeline.save_extractions_csv(
        analysis_extractions(), output_path=paths.extractions_csv
    )
    assert analysis_cli.main([]) == 0
    assert f"Source: {paths.extractions_csv}" in capsys.readouterr().out


def test_cli_two_explicit_roots(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for index, rows in enumerate([analysis_extractions(), []]):
        paths = DataPaths.from_root(tmp_path / str(index))
        pipeline.save_extractions_csv(rows, output_path=paths.extractions_csv)
        assert analysis_cli.main(["--data-dir", str(paths.root)]) == 0
        output = capsys.readouterr().out
        assert f"Source: {paths.extractions_csv}" in output
        assert f"N = {len(rows)}" in output
