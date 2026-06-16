#!/usr/bin/env python3
"""Initialize PostgreSQL schema for TailCast market data."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.data.db import build_store


def main() -> None:
    config = load_config()
    store = build_store(config)
    if store is None:
        raise SystemExit("PostgreSQL is not configured or unreachable.")
    print("PostgreSQL schema initialized.")


if __name__ == "__main__":
    main()
