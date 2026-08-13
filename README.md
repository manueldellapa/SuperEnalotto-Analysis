# SuperEnalotto Analysis

A Python toolkit for downloading, parsing, validating, and consolidating
historical SuperEnalotto extraction data from the official archive.

> [!NOTE]
> This project is not affiliated with, endorsed by, or sponsored by
> SuperEnalotto or its operators.

## Features

- Download historical SuperEnalotto archive pages
- Cache raw HTML pages locally
- Parse extraction results
- Validate extracted data
- Deduplicate extraction records and reject conflicting duplicates
- Export consolidated results to CSV
- Retry failed HTTP requests with configurable backoff
- Unit tests with pytest
- Static type checking with mypy
- Linting with Ruff

## Requirements

- Python 3.14.x
- `uv` — required to install from `uv.lock`; `pip` can install the project but
  only from the version ranges, not the lockfile

The supported Python version is defined in `pyproject.toml`:

```text
>=3.14,<3.15
```

`.python-version` pins the exact interpreter (3.14.4) that `uv venv` resolves.

## Setup

A fresh checkout has no virtual environment. Create one, then install from the
lockfile:

```bash
uv venv
uv sync --locked --all-extras
source .venv/bin/activate
```

`uv.lock` pins every dependency, transitives included, with hashes.
`uv sync --locked` installs exactly those versions and fails if the lockfile
has drifted from `pyproject.toml`, so a local environment matches CI.

> [!IMPORTANT]
> `uv pip install -e ".[dev]"` does **not** read `uv.lock`. It is the
> pip-compatible interface and resolves from the ranges in `pyproject.toml`,
> which is how two machines end up on different versions. Use `uv sync`.

### Updating dependencies

After changing a dependency in `pyproject.toml`, refresh the lockfile and
commit it in the same change — CI rejects a stale lockfile:

```bash
uv lock
```

To move dependencies to newer versions within the ranges already declared:

```bash
uv lock --upgrade
```

Dependabot also opens a monthly pull request against `uv.lock`, so the pins do
not age unattended. See `.github/dependabot.yml`.

## Usage

The downloader walks an inclusive interval of months, one archive page per
month, and consolidates everything it parses into a single CSV.

```bash
python scripts/download_extractions.py --start-year 2024
```

The examples below assume the virtual environment is active. Otherwise prefix
them with `uv run` or call `.venv/bin/python` directly.

### Options

| Option | Default | Description |
| --- | --- | --- |
| `--start-year` | *required* | First year to download. |
| `--start-month` | `1` | First month to download (1–12). |
| `--end-year` | `--start-year` | Last year to download. |
| `--end-month` | *see below* | Last month to download (1–12). |
| `--force` | off | Re-download archive pages even when already cached. |
| `--verbose` | off | Enable debug-level logging. |

`--end-month` cascades when omitted: it follows `--start-month` if `--end-year`
was also omitted, becomes the current month if `--end-year` is the current
year, and otherwise defaults to `12`.

The interval is validated before any request is made. Months must be 1–12,
years must fall between 1997 (SuperEnalotto's first year) and the current year,
start must not be after end, and neither endpoint may be in the future.

### Examples

A single month:

```bash
python scripts/download_extractions.py --start-year 2024 --start-month 3 --end-month 3
```

One full year:

```bash
python scripts/download_extractions.py --start-year 2024
```

An interval spanning several years:

```bash
python scripts/download_extractions.py --start-year 2020 --start-month 6 --end-year 2024 --end-month 12
```

Everything from the first available year to today:

```bash
python scripts/download_extractions.py --start-year 1997 --end-year 2026
```

Refresh pages already on disk, with verbose logging:

```bash
python scripts/download_extractions.py --start-year 2024 --force --verbose
```

## Output

There is no `data/` directory in a fresh checkout; it is created on the first
run. Both subdirectories are gitignored.

```text
data/
├── raw/                        one cached HTML page per month
│   ├── 2024-01.html
│   └── 2024-02.html
└── processed/
    └── extractions.csv         the consolidated dataset
```

### `data/raw/`

One archive page per month, named `{year}-{month:02d}.html`. Cached pages are
reused on later runs unless `--force` is passed, which makes re-runs cheap and
lets an interrupted download resume without re-fetching what it already has.

Rebuilding the CSV from cached pages costs no network traffic, so widening an
interval later is inexpensive.

### `data/processed/extractions.csv`

The consolidated dataset: deduplicated, validated, and sorted by extraction
date and then contest number.

> [!WARNING]
> **The CSV is a full overwrite, not a merge.** Each run rewrites the file from
> only the interval it just downloaded. Re-running with a narrower interval
> shrinks a previously complete dataset rather than adding to it. To rebuild
> the full history, re-run across the whole range — cached pages make this
> cheap.

If any month fails, the canonical file is left untouched and the partial
results are written to `data/processed/extractions.partial.csv` instead, so a
half-finished run never replaces good data. A later fully successful run
removes that stale partial file.

### CSV schema

| Column | Type | Description |
| --- | --- | --- |
| `contest_number` | integer | Contest number, as published (`Concorso N° 105`). Always positive. |
| `extraction_date` | date | Extraction date in ISO format, `YYYY-MM-DD`. |
| `number_1` … `number_6` | integer | The six main drawn numbers, 1–90, unique within a row, in the order the archive publishes them. |
| `jolly` | integer | The Jolly number, 1–90. |
| `superstar` | integer | The SuperStar number, 1–90. |

Every row is validated before it reaches the CSV: numbers must be integers in
range, the six main numbers must be distinct, the contest number must be
positive, and the date must be a real calendar date. A row that fails any of
these checks fails the month rather than being written out.

Rows are unique by `(contest_number, extraction_date)`. Duplicate records
collapse only when their drawn values are identical — two records claiming the
same contest and date with *different* results are treated as a data-integrity
error rather than resolved silently.

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Every month in the interval was downloaded and parsed. |
| `1` | At least one month failed, the interval was invalid, two records contradicted each other, or an unexpected error occurred. |

A month that fails does not abort the run: the error is recorded and the
remaining months still download, with every failure reported at the end.
Contradictory records are the exception — they stop the run and no CSV is
written at all.

## Development

```bash
# Run the full test suite
python -m pytest

# Run a single test file or a single test
python -m pytest tests/test_scraper.py
python -m pytest tests/test_validators.py::test_validate_number_accepts_valid_number

# Coverage
python -m pytest --cov=superenalotto --cov-report=term-missing

# Lint (add --fix to apply fixes and sort imports)
python -m ruff check .

# Type-check (strict mode)
python -m mypy src scripts tests
```

No test performs real HTTP requests: the suite substitutes behavior with
`monkeypatch` and parses sample archive HTML embedded in the test files.

CI runs on pushes to `main` and pull requests targeting `main`, and gates on
exactly the three commands above — `ruff check`, `mypy`, and `pytest` — against
the locked dependency set. Keeping all three clean locally is what keeps a pull
request green.

## Project structure

```text
.
├── src/superenalotto/          the installable library
│   ├── constants.py            paths, URLs, HTTP policy, game rules
│   ├── models.py               the Extraction domain entity and CSV schema
│   ├── validators.py           field validation
│   └── scraper.py              HTTP client and HTML parsing
├── scripts/
│   └── download_extractions.py the CLI: filesystem, CSV, orchestration
├── tests/                      mirrors src/superenalotto one-to-one
├── pyproject.toml              project metadata, dependencies, tool config
└── uv.lock                     the pinned dependency set
```

The split is deliberate. The library holds pure parsing, validation, and domain
logic and performs no filesystem work, which keeps it unit-testable without
touching disk. The script owns all file and CSV I/O. Only `src/` is installed
as a package; `scripts/` is a plain script directory that imports it.

## License

Released under the MIT License. See [LICENSE](LICENSE).
