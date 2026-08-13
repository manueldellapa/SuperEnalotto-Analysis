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
