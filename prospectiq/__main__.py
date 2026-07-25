"""Enables ``python -m prospectiq``."""

from __future__ import annotations

import sys

from prospectiq.cli import main

if __name__ == "__main__":
    sys.exit(main())
