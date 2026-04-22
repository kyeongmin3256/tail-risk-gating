"""Tests for FRED CSV fallback parsing robustness."""

import pandas as pd
import pytest

from src.data.fetcher import DataFetcher


@pytest.fixture
def minimal_config():
    return {
        "data": {
            "start_date": "2020-01-01",
            "end_date": "2020-01-10",
            "fred_api_key": None,
        }
    }


def test_fetch_fred_parses_standard_date_and_numeric_values(monkeypatch, tmp_path, minimal_config):
    fetcher = DataFetcher(minimal_config, cache_dir=tmp_path)

    def fake_read_csv(url, *args, **kwargs):
        return pd.DataFrame(
            {
                "DATE": ["2020-01-01", "2020-01-02", "2020-01-03"],
                "DGS10": ["1.50", ".", "1.55"],
            }
        )

    monkeypatch.setattr(pd, "read_csv", fake_read_csv)
    series = fetcher.fetch_fred("DGS10", "treasury_10y")

    assert series.index.name == "date"
    assert series.name == "treasury_10y"
    assert isinstance(series.index, pd.DatetimeIndex)
    assert series.iloc[0] == pytest.approx(1.50)
    assert pd.isna(series.iloc[1])  # '.' -> NaN
    assert series.iloc[2] == pytest.approx(1.55)
    assert (tmp_path / "treasury_10y.csv").exists()


def test_fetch_fred_accepts_lowercase_date_column(monkeypatch, tmp_path, minimal_config):
    fetcher = DataFetcher(minimal_config, cache_dir=tmp_path)

    def fake_read_csv(url, *args, **kwargs):
        return pd.DataFrame(
            {
                "date": ["2020-01-01", "2020-01-02"],
                "DGS2": ["1.20", "1.21"],
            }
        )

    monkeypatch.setattr(pd, "read_csv", fake_read_csv)
    series = fetcher.fetch_fred("DGS2", "treasury_2y")

    assert series.index.name == "date"
    assert list(series.values) == pytest.approx([1.20, 1.21])


def test_fetch_fred_raises_when_date_column_missing(monkeypatch, tmp_path, minimal_config):
    fetcher = DataFetcher(minimal_config, cache_dir=tmp_path)

    def fake_read_csv(url, *args, **kwargs):
        return pd.DataFrame({"DGS10": ["1.5", "1.6"]})

    monkeypatch.setattr(pd, "read_csv", fake_read_csv)

    with pytest.raises(ValueError, match="missing DATE column"):
        fetcher.fetch_fred("DGS10", "treasury_10y")


def test_fetch_fred_falls_back_to_first_value_column(monkeypatch, tmp_path, minimal_config):
    fetcher = DataFetcher(minimal_config, cache_dir=tmp_path)

    def fake_read_csv(url, *args, **kwargs):
        # Simulate schema drift where value column name differs from series_id.
        return pd.DataFrame(
            {
                "DATE": ["2020-01-01", "2020-01-02"],
                "VALUE": ["2.0", "2.1"],
            }
        )

    monkeypatch.setattr(pd, "read_csv", fake_read_csv)
    series = fetcher.fetch_fred("UNEXPECTED_SERIES", "some_series")

    assert list(series.values) == pytest.approx([2.0, 2.1])
