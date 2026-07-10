"""Application configuration loader.

Reads environment variables from .env file and exposes
configuration settings for the application.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load .env from data/ directory
_env_path = os.path.join(os.path.dirname(__file__), "..", "data", ".env")
load_dotenv(os.path.abspath(_env_path))


@dataclass(frozen=True)
class AppConfig:
    """Immutable application configuration."""

    api_key: str
    db_path: str
    base_currency: str
    market_data_provider: str


def get_config() -> AppConfig:
    """Load and return the application configuration from environment."""
    return AppConfig(
        api_key=os.getenv("MARKET_DATA_API_KEY", ""),
        db_path=os.getenv("DB_PATH", "data/portfolio.db"),
        base_currency=os.getenv("BASE_CURRENCY", "USD"),
        market_data_provider=os.getenv("MARKET_DATA_PROVIDER", "yfinance"),
    )


# Global config instance
config = get_config()