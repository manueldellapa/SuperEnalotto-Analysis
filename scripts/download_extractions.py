"""Backwards-compatible launcher for the packaged downloader CLI.

The implementation moved into ``superenalotto.cli``, which is installed as the
``superenalotto-download`` console script. This file only keeps the historical
``python scripts/download_extractions.py`` invocation working.
"""

from __future__ import annotations

import sys

from superenalotto.cli import main

__all__ = ["main"]

if __name__ == "__main__":
    sys.exit(main())
