"""Tests for PostgreSQL store helpers."""

from src.config import load_config
from src.data.store import database_url


def test_database_url_from_config():
    config = load_config()
    url = database_url(config)
    assert url is not None
    assert "postgresql+psycopg2://" in url
    assert "tailrisk" in url


def test_database_url_env_override(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://user:pass@host:5432/db")
    config = load_config()
    assert database_url(config) == "postgresql+psycopg2://user:pass@host:5432/db"


def test_build_store_skips_when_unreachable(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from src.data.db import build_store

    config = load_config()
    config["database"]["host"] = "127.0.0.1"
    config["database"]["port"] = 1
    store = build_store(config)
    assert store is None
