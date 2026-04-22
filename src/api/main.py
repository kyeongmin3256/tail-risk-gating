"""FastAPI service for TailCast dashboard data."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.api.dashboard_data import load_dashboard_data

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
