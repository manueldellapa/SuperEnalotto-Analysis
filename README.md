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
- Deduplicate extraction records
- Export consolidated results to CSV
- Retry failed HTTP requests with configurable backoff
- Unit tests with pytest
- Static type checking with mypy
- Linting with Ruff

## Requirements

- Python 3.14.x
- `uv` or `pip`

The supported Python version is defined in `pyproject.toml`:

```text
>=3.14,<3.15