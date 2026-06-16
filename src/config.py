"""Load and validate project configuration."""

import os
from pathlib import Path

import yaml

from src.data.store import database_url


def load_config(config_path: str | None = None) -> dict:
    """Load configuration from YAML file.

    Args:
        config_path: Path to config file. Defaults to config/config.yaml
                     relative to project root.

    Returns:
        Configuration dictionary.
    """
    if config_path is None:
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config" / "config.yaml"

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Override FRED API key from environment if set
    fred_key = os.environ.get("FRED_API_KEY")
    if fred_key:
        config["data"]["fred_api_key"] = fred_key

    # Expose resolved DB URL for scripts/services
    config["database_url"] = database_url(config)

    return config
