#!/usr/bin/env python3
"""Import existing CSV raw cache into PostgreSQL."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.data.db import build_store
from src.data.fetcher import DataFetcher

YAHOO_NAMES = {
    "spy",
    "vix",
    "vvix",
    "vix9d",
    "vix3m",
    "skew",
    "hyg",
    "ief",
    "dxy",
}


def main() -> None:
    config = load_config()
    store = build_store(config)
    if store is None:
        raise SystemExit("PostgreSQL is not configured or unreachable.")

    fetcher = DataFetcher(config, store=store)
    raw = fetcher._load_csv_cache()
    if not raw:
        raise SystemExit("No CSV cache found under data/raw/.")

    tickers = config["data"]["tickers"]
    fred_series = config["data"]["fred_series"]
    row_count = 0

    for name, payload in raw.items():
        if name in tickers:
            if isinstance(payload, pd.Series):
                frame = payload.to_frame(name="Close")
            else:
                frame = payload
            row_count += store.upsert_ohlcv(name, tickers[name], frame)
        elif name in fred_series:
            series = payload if isinstance(payload, pd.Series) else payload.iloc[:, 0]
            row_count += store.upsert_macro_series(name, fred_series[name], series)
        elif name in YAHOO_NAMES:
            frame = payload if isinstance(payload, pd.DataFrame) else payload.to_frame(name="Close")
            row_count += store.upsert_ohlcv(name, tickers.get(name, name), frame)
        else:
            print(f"skip unknown instrument: {name}")

    store.record_ingestion("csv_import", len(raw), row_count)
    print(f"Imported {len(raw)} instruments ({row_count} rows) into PostgreSQL.")


if __name__ == "__main__":
    main()
