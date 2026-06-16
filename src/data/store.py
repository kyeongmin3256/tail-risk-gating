"""PostgreSQL persistence for raw market data."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

OHLCV_TABLE = "ohlcv_daily"
MACRO_TABLE = "macro_series"
META_TABLE = "ingestion_runs"


def database_url(config: dict) -> str | None:
    """Resolve SQLAlchemy database URL from env or config."""
    env_url = os.environ.get("DATABASE_URL")
    if env_url:
        return env_url

    db = config.get("database")
    if not db:
        return None

    host = os.environ.get("POSTGRES_HOST", db.get("host", "localhost"))
    port = int(os.environ.get("POSTGRES_PORT", db.get("port", 5432)))
    name = os.environ.get("POSTGRES_DB", db.get("name", "tailrisk"))
    user = os.environ.get("POSTGRES_USER", db.get("user", "tailrisk"))
    password = os.environ.get("POSTGRES_PASSWORD", db.get("password", "tailrisk"))
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"


class MarketDataStore:
    """Persist and load Yahoo/FRED raw inputs in PostgreSQL."""

    def __init__(self, engine: Engine):
        self.engine = engine

    @classmethod
    def from_config(cls, config: dict) -> MarketDataStore | None:
        url = database_url(config)
        if not url:
            return None
        return cls(create_engine(url, pool_pre_ping=True))

    def ping(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            logger.warning("PostgreSQL unavailable: %s", exc)
            return False

    def init_schema(self) -> None:
        ddl = f"""
        CREATE TABLE IF NOT EXISTS {OHLCV_TABLE} (
            instrument TEXT NOT NULL,
            source_symbol TEXT NOT NULL,
            date DATE NOT NULL,
            open DOUBLE PRECISION,
            high DOUBLE PRECISION,
            low DOUBLE PRECISION,
            close DOUBLE PRECISION,
            volume DOUBLE PRECISION,
            PRIMARY KEY (instrument, date)
        );

        CREATE TABLE IF NOT EXISTS {MACRO_TABLE} (
            instrument TEXT NOT NULL,
            source_symbol TEXT NOT NULL,
            date DATE NOT NULL,
            value DOUBLE PRECISION,
            PRIMARY KEY (instrument, date)
        );

        CREATE TABLE IF NOT EXISTS {META_TABLE} (
            id BIGSERIAL PRIMARY KEY,
            run_type TEXT NOT NULL,
            instrument_count INTEGER NOT NULL,
            row_count INTEGER NOT NULL,
            started_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_ohlcv_date ON {OHLCV_TABLE}(date);
        CREATE INDEX IF NOT EXISTS idx_macro_date ON {MACRO_TABLE}(date);
        """
        with self.engine.begin() as conn:
            conn.execute(text(ddl))

    def has_data(self) -> bool:
        with self.engine.connect() as conn:
            ohlcv = conn.execute(text(f"SELECT COUNT(*) FROM {OHLCV_TABLE}")).scalar_one()
            macro = conn.execute(text(f"SELECT COUNT(*) FROM {MACRO_TABLE}")).scalar_one()
        return int(ohlcv) + int(macro) > 0

    def upsert_ohlcv(self, instrument: str, source_symbol: str, frame: pd.DataFrame) -> int:
        df = frame.copy()
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df.index = df.index.normalize()

        rows: list[dict[str, Any]] = []
        for dt, row in df.iterrows():
            rows.append(
                {
                    "instrument": instrument,
                    "source_symbol": source_symbol,
                    "date": dt.date(),
                    "open": _float_or_none(row.get("Open")),
                    "high": _float_or_none(row.get("High")),
                    "low": _float_or_none(row.get("Low")),
                    "close": _float_or_none(row.get("Close")),
                    "volume": _float_or_none(row.get("Volume")),
                }
            )

        if not rows:
            return 0

        sql = text(
            f"""
            INSERT INTO {OHLCV_TABLE}
                (instrument, source_symbol, date, open, high, low, close, volume)
            VALUES
                (:instrument, :source_symbol, :date, :open, :high, :low, :close, :volume)
            ON CONFLICT (instrument, date) DO UPDATE SET
                source_symbol = EXCLUDED.source_symbol,
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume
            """
        )
        with self.engine.begin() as conn:
            conn.execute(sql, rows)
        return len(rows)

    def upsert_macro_series(self, instrument: str, source_symbol: str, series: pd.Series) -> int:
        s = series.copy()
        if not isinstance(s.index, pd.DatetimeIndex):
            s.index = pd.to_datetime(s.index)
        s = s.sort_index()
        s.index = s.index.normalize()

        rows = [
            {
                "instrument": instrument,
                "source_symbol": source_symbol,
                "date": dt.date(),
                "value": _float_or_none(val),
            }
            for dt, val in s.items()
            if pd.notna(val)
        ]
        if not rows:
            return 0

        sql = text(
            f"""
            INSERT INTO {MACRO_TABLE}
                (instrument, source_symbol, date, value)
            VALUES
                (:instrument, :source_symbol, :date, :value)
            ON CONFLICT (instrument, date) DO UPDATE SET
                source_symbol = EXCLUDED.source_symbol,
                value = EXCLUDED.value
            """
        )
        with self.engine.begin() as conn:
            conn.execute(sql, rows)
        return len(rows)

    def record_ingestion(self, run_type: str, instrument_count: int, row_count: int) -> None:
        sql = text(
            f"""
            INSERT INTO {META_TABLE} (run_type, instrument_count, row_count, started_at)
            VALUES (:run_type, :instrument_count, :row_count, :started_at)
            """
        )
        with self.engine.begin() as conn:
            conn.execute(
                sql,
                {
                    "run_type": run_type,
                    "instrument_count": instrument_count,
                    "row_count": row_count,
                    "started_at": datetime.now(timezone.utc),
                },
            )

    def load_all(self) -> dict[str, pd.DataFrame | pd.Series]:
        data: dict[str, pd.DataFrame | pd.Series] = {}

        with self.engine.connect() as conn:
            ohlcv_names = conn.execute(
                text(f"SELECT DISTINCT instrument FROM {OHLCV_TABLE} ORDER BY instrument")
            ).scalars()
            for name in ohlcv_names:
                frame = pd.read_sql(
                    text(
                        f"""
                        SELECT date, open, high, low, close, volume
                        FROM {OHLCV_TABLE}
                        WHERE instrument = :instrument
                        ORDER BY date
                        """
                    ),
                    conn,
                    params={"instrument": name},
                    parse_dates=["date"],
                )
                frame = frame.set_index("date")
                frame.columns = ["Open", "High", "Low", "Close", "Volume"]
                data[name] = frame
                logger.info("Loaded %s OHLCV from PostgreSQL (%s rows)", name, len(frame))

            macro_names = conn.execute(
                text(f"SELECT DISTINCT instrument FROM {MACRO_TABLE} ORDER BY instrument")
            ).scalars()
            for name in macro_names:
                frame = pd.read_sql(
                    text(
                        f"""
                        SELECT date, value
                        FROM {MACRO_TABLE}
                        WHERE instrument = :instrument
                        ORDER BY date
                        """
                    ),
                    conn,
                    params={"instrument": name},
                    parse_dates=["date"],
                )
                series = frame.set_index("date")["value"]
                series.name = name
                data[name] = series
                logger.info("Loaded %s macro series from PostgreSQL (%s rows)", name, len(series))

        return data


def _float_or_none(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)
