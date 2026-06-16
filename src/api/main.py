"""FastAPI service for TailCast dashboard data."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.api.dashboard_data import load_dashboard_data
from src.config import load_config
from src.data.db import build_store

ROOT_DIR = Path(__file__).resolve().parents[2]

app = FastAPI(title="TailCast API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_CACHE: dict | None = None


def _get_data(force_refresh: bool = False) -> dict:
    global _CACHE
    if _CACHE is None or force_refresh:
        _CACHE = load_dashboard_data(ROOT_DIR)
    return _CACHE


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/health/db")
def health_db() -> dict:
    config = load_config()
    if not config.get("database_url"):
        return {"status": "disabled", "postgresql": False, "message": "DATABASE_URL not configured"}

    store = build_store(config, init_schema=False)
    if store is None:
        return {"status": "unavailable", "postgresql": False, "message": "PostgreSQL unreachable"}

    try:
        with store.engine.connect() as conn:
            ohlcv = conn.execute(text("SELECT COUNT(*) FROM ohlcv_daily")).scalar()
            macro = conn.execute(text("SELECT COUNT(*) FROM macro_series")).scalar()
        return {
            "status": "ok",
            "postgresql": True,
            "tables": {"ohlcv_daily": int(ohlcv), "macro_series": int(macro)},
        }
    except Exception as exc:
        return {"status": "error", "postgresql": False, "message": str(exc)}


@app.get("/api/dashboard/thresholds")
def dashboard_thresholds() -> dict:
    data = _get_data()
    return {"thresholds": data["thresholds"]}


@app.get("/api/dashboard/data")
def dashboard_data() -> dict:
    return _get_data()


@app.get("/api/dashboard/data/{threshold}")
def dashboard_data_by_threshold(threshold: int) -> dict:
    data = _get_data()
    key = str(threshold)
    if key not in data["dataByThreshold"]:
        raise HTTPException(status_code=404, detail=f"Threshold {threshold} not found")
    return {
        "threshold": threshold,
        "data": data["dataByThreshold"][key],
    }


@app.post("/api/dashboard/refresh")
def refresh_dashboard() -> dict:
    data = _get_data(force_refresh=True)
    return {"refreshed": True, "thresholds": data["thresholds"]}
