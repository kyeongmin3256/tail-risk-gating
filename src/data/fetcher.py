"""Fetch market data from Yahoo Finance and FRED.

All data sources are free and reproducible. No paid APIs required.

Usage:
    from src.data.fetcher import DataFetcher
    fetcher = DataFetcher(config)
    raw_data = fetcher.fetch_all()
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
import yfinance as yf

if TYPE_CHECKING:
    from src.data.store import MarketDataStore

logger = logging.getLogger(__name__)


class DataFetcher:
    """Downloads and caches raw market data from free sources."""

    def __init__(
        self,
        config: dict,
        cache_dir: str | Path = "data/raw",
        store: MarketDataStore | None = None,
    ):
        """Initialize fetcher with config.

        Args:
            config: Project configuration dict.
            cache_dir: Directory to cache downloaded CSVs.
            store: Optional PostgreSQL-backed market data store.
        """
        self.config = config
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.store = store

        self.start_date = config["data"]["start_date"]
        self.end_date = config["data"].get("end_date") or datetime.today().strftime(
            "%Y-%m-%d"
        )

    def fetch_yahoo(self, ticker: str, name: str) -> pd.DataFrame:
        """Fetch daily OHLCV data from Yahoo Finance.

        Args:
            ticker: Yahoo Finance ticker symbol.
            name: Human-readable name for logging and caching.

        Returns:
            DataFrame with Date index and OHLCV columns.
        """
        cache_path = self.cache_dir / f"{name}.csv"

        logger.info(f"Fetching {name} ({ticker}) from Yahoo Finance...")
        df = yf.download(
            ticker,
            start=self.start_date,
            end=self.end_date,
            auto_adjust=True,
            progress=False,
        )

        if df.empty:
            raise ValueError(f"No data returned for {ticker}. Check ticker symbol.")

        # Flatten multi-level columns if present (yfinance sometimes returns multi-index)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.index.name = "date"
        df.to_csv(cache_path)
        if self.store is not None:
            self.store.upsert_ohlcv(name, ticker, df)
        logger.info(f"  Saved {len(df)} rows to {cache_path}")

        return df

    def fetch_fred(self, series_id: str, name: str) -> pd.Series:
        """Fetch economic data from FRED.

        Uses fredapi if API key is available, otherwise falls back to
        FRED's public CSV endpoint (no key required, but less reliable).

        Args:
            series_id: FRED series identifier (e.g., 'DGS10').
            name: Human-readable name for logging and caching.

        Returns:
            Series with Date index and values.
        """
        cache_path = self.cache_dir / f"{name}.csv"

        api_key = self.config["data"].get("fred_api_key")

        if api_key:
            logger.info(f"Fetching {name} ({series_id}) from FRED API...")
            from fredapi import Fred

            fred = Fred(api_key=api_key)
            series = fred.get_series(
                series_id,
                observation_start=self.start_date,
                observation_end=self.end_date,
            )
        else:
            # Fallback: FRED public CSV (no API key needed)
            logger.info(
                f"Fetching {name} ({series_id}) from FRED public CSV "
                f"(no API key set)..."
            )
            url = (
                f"https://fred.stlouisfed.org/graph/fredgraph.csv"
                f"?id={series_id}"
                f"&cosd={self.start_date}"
                f"&coed={self.end_date}"
            )
            df = pd.read_csv(url)

            # FRED usually returns DATE, but be defensive in case of schema drift.
            date_col = next((c for c in df.columns if c.upper() == "DATE"), None)
            if date_col is None:
                raise ValueError(
                    f"FRED response for {series_id} missing DATE column. "
                    f"Columns: {list(df.columns)}"
                )

            value_col = series_id if series_id in df.columns else None
            if value_col is None:
                candidates = [c for c in df.columns if c != date_col]
                if not candidates:
                    raise ValueError(
                        f"FRED response for {series_id} missing value column. "
                        f"Columns: {list(df.columns)}"
                    )
                value_col = candidates[0]

            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            df = df.set_index(date_col)
            series = df[value_col]
            # FRED uses '.' for missing values
            series = pd.to_numeric(series, errors="coerce")

        series.index.name = "date"
        series.name = name
        series.to_csv(cache_path)
        if self.store is not None:
            self.store.upsert_macro_series(name, series_id, series)
        logger.info(f"  Saved {len(series)} rows to {cache_path}")

        return series

    def fetch_all(self) -> dict[str, pd.DataFrame | pd.Series]:
        """Fetch all data sources defined in config.

        Returns:
            Dictionary mapping data names to DataFrames/Series.
        """
        data = {}

        # Yahoo Finance tickers
        tickers = self.config["data"]["tickers"]
        for name, ticker in tickers.items():
            try:
                data[name] = self.fetch_yahoo(ticker, name)
            except Exception as e:
                logger.warning(f"Failed to fetch {name} ({ticker}): {e}")

        # FRED series
        fred_series = self.config["data"]["fred_series"]
        for name, series_id in fred_series.items():
            try:
                data[name] = self.fetch_fred(series_id, name)
            except Exception as e:
                logger.warning(f"Failed to fetch {name} ({series_id}): {e}")

        logger.info(f"Fetched {len(data)} data sources successfully.")
        if self.store is not None and data:
            row_count = sum(len(v) for v in data.values())
            self.store.record_ingestion("fetch_all", len(data), row_count)
        return data

    def load_cached(self, prefer_db: bool = True) -> dict[str, pd.DataFrame | pd.Series]:
        """Load cached data, preferring PostgreSQL when available."""
        if prefer_db and self.store is not None and self.store.has_data():
            try:
                data = self.store.load_all()
                if data:
                    return data
            except Exception as exc:
                logger.warning("Failed loading from PostgreSQL, using CSV cache: %s", exc)

        return self._load_csv_cache()

    def _load_csv_cache(self) -> dict[str, pd.DataFrame | pd.Series]:
        """Load previously cached data from disk."""
        data = {}
        for csv_path in sorted(self.cache_dir.glob("*.csv")):
            name = csv_path.stem
            df = pd.read_csv(csv_path, parse_dates=["date"], index_col="date")
            if len(df.columns) == 1:
                data[name] = df.iloc[:, 0]
            else:
                data[name] = df
            logger.info(f"Loaded {name} from cache ({len(df)} rows)")

        return data
