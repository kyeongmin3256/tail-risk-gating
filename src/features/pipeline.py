"""Feature pipeline - combines all feature modules into a single feature matrix.

This is the main entry point for feature engineering. It takes raw data
from the fetcher and produces a clean, aligned feature DataFrame ready
for model training.

CRITICAL: All features use ONLY past data as of each row's date.
No future information leaks into any feature computation.

Usage:
    from src.features.pipeline import FeaturePipeline
    pipeline = FeaturePipeline(config)
    features = pipeline.build(raw_data)
"""

import logging

import pandas as pd

from src.features.calendar import build_calendar_features
from src.features.market_structure import build_market_structure_features
from src.features.momentum import build_momentum_features
from src.features.volatility import build_volatility_features

logger = logging.getLogger(__name__)


class FeaturePipeline:
    """Builds the complete feature matrix from raw data sources."""

    def __init__(self, config: dict):
        """Initialize with project config.

        Args:
            config: Project configuration dictionary.
        """
        self.config = config
        self.feature_config = config["features"]

    def _extract_series(
        self, raw_data: dict, key: str, column: str = "Close"
    ) -> pd.Series | None:
        """Safely extract a series from raw data dict.

        Args:
            raw_data: Dictionary from DataFetcher.fetch_all().
            key: Key name in the dictionary.
            column: Column to extract if value is a DataFrame.

        Returns:
            Series or None if not available.
        """
        data = raw_data.get(key)
        if data is None:
            logger.warning(f"Data source '{key}' not available.")
            return None

        if isinstance(data, pd.DataFrame):
            if column in data.columns:
                return data[column]
            else:
                logger.warning(f"Column '{column}' not found in '{key}'.")
                return None

        return data

    def build(self, raw_data: dict) -> pd.DataFrame:
        """Build complete feature matrix from raw data.

        Args:
            raw_data: Dictionary from DataFetcher.fetch_all() or load_cached().

        Returns:
            DataFrame with all features, indexed by date.
            Rows with NaN (from rolling computations) are NOT dropped —
            the caller decides how to handle them.
        """
        logger.info("Building feature matrix...")

        # Extract base series
        spy_close = self._extract_series(raw_data, "spy", "Close")
        spy_volume = self._extract_series(raw_data, "spy", "Volume")
        vix = self._extract_series(raw_data, "vix", "Close")
        vvix = self._extract_series(raw_data, "vvix", "Close")
        skew = self._extract_series(raw_data, "skew", "Close")
        vix3m = self._extract_series(raw_data, "vix3m", "Close")
        vix9d = self._extract_series(raw_data, "vix9d", "Close")
        hyg_close = self._extract_series(raw_data, "hyg", "Close")
        ief_close = self._extract_series(raw_data, "ief", "Close")
        dxy_close = self._extract_series(raw_data, "dxy", "Close")
        treasury_2y = self._extract_series(raw_data, "treasury_2y")
        treasury_10y = self._extract_series(raw_data, "treasury_10y")

        if spy_close is None or vix is None:
            raise ValueError("SPY and VIX data are required at minimum.")

        # Build feature groups
        all_features = []

        # 1. Volatility features
        if all(s is not None for s in [vix, vvix, skew, vix3m]):
            vol_features = build_volatility_features(
                spy_close=spy_close,
                vix=vix,
                vvix=vvix,
                skew=skew,
                vix3m=vix3m,
                vix9d=vix9d,
                rvol_windows=self.feature_config["realized_vol_windows"],
            )
            all_features.append(vol_features)
            logger.info(f"  Volatility features: {vol_features.shape[1]} columns")
        else:
            logger.warning("  Skipping some volatility features (missing data).")

        # 2. Market structure features
        if all(s is not None for s in [hyg_close, ief_close, treasury_2y, treasury_10y, dxy_close]):
            mkt_features = build_market_structure_features(
                hyg_close=hyg_close,
                ief_close=ief_close,
                treasury_2y=treasury_2y,
                treasury_10y=treasury_10y,
                dxy_close=dxy_close,
                credit_window=self.feature_config["credit_spread_window"],
            )
            all_features.append(mkt_features)
            logger.info(f"  Market structure features: {mkt_features.shape[1]} columns")
        else:
            logger.warning("  Skipping some market structure features (missing data).")

        # 3. Momentum features
        if spy_close is not None and spy_volume is not None:
            mom_features = build_momentum_features(
                spy_close=spy_close,
                spy_volume=spy_volume,
                ret_windows=self.feature_config["momentum_windows"],
                ma_window=self.feature_config["ma_window"],
                volume_ma_window=self.feature_config["volume_ma_window"],
                drawdown_window=self.feature_config["drawdown_window"],
            )
            all_features.append(mom_features)
            logger.info(f"  Momentum features: {mom_features.shape[1]} columns")

        # 4. Calendar features
        cal_features = build_calendar_features(spy_close.index)
        all_features.append(cal_features)
        logger.info(f"  Calendar features: {cal_features.shape[1]} columns")

        # Combine all features
        features = pd.concat(all_features, axis=1)

        # Align on common dates (inner join)
        features = features.loc[features.index.dropna()]

        logger.info(
            f"Feature matrix built: {features.shape[0]} rows × {features.shape[1]} columns"
        )
        logger.info(f"Date range: {features.index.min()} to {features.index.max()}")
        logger.info(f"NaN summary:\n{features.isna().sum().to_string()}")

        return features
