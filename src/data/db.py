"""Helpers to wire PostgreSQL into the data pipeline."""

from __future__ import annotations

import logging

from src.data.store import MarketDataStore

logger = logging.getLogger(__name__)


def build_store(config: dict, *, init_schema: bool = True) -> MarketDataStore | None:
    """Create a store from config and optionally initialize schema."""
    store = MarketDataStore.from_config(config)
    if store is None:
        return None
    if not store.ping():
        logger.warning("PostgreSQL configured but unreachable; falling back to CSV cache.")
        return None
    if init_schema:
        store.init_schema()
    return store
