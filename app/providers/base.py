"""Abstract market data provider interface.

Defines the contract that all market data providers must implement.
Uses the Strategy pattern to allow swapping API backends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class PriceQuote:
    """Current price quote for a ticker."""

    ticker: str
    price: float
    currency: str
    timestamp: datetime


@dataclass(frozen=True)
class PriceHistory:
    """Historical price data for a ticker."""

    ticker: str
    dates: list[datetime]
    opens: list[float]
    highs: list[float]
    lows: list[float]
    closes: list[float]
    volumes: list[int]


@dataclass(frozen=True)
class TrendData:
    """Trend information for a ticker."""

    ticker: str
    trend_direction: str  # "up", "down", "flat"
    change_percent: float
    sector: str
    confidence_score: float


class MarketDataProvider(ABC):
    """Abstract base class for market data providers.

    Concrete implementations (yfinance, alpha_vantage, etc.) must
    implement all abstract methods to provide market data.
    """

    @abstractmethod
    def get_current_price(self, ticker: str) -> Optional[PriceQuote]:
        """Fetch the current price for a single ticker.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL").

        Returns:
            PriceQuote if successful, None if ticker is invalid or data unavailable.
        """

    @abstractmethod
    def get_current_prices(self, tickers: list[str]) -> dict[str, PriceQuote]:
        """Fetch current prices for multiple tickers.

        Args:
            tickers: List of stock ticker symbols.

        Returns:
            Dictionary mapping ticker to PriceQuote. Invalid tickers are omitted.
        """

    @abstractmethod
    def get_price_history(
        self, ticker: str, period: str = "1M"
    ) -> Optional[PriceHistory]:
        """Fetch historical price data for a ticker.

        Args:
            ticker: Stock ticker symbol.
            period: Time range — one of "1D", "1W", "1M", "3M", "1Y".

        Returns:
            PriceHistory if data available, None otherwise.
        """

    @abstractmethod
    def validate_ticker(self, ticker: str) -> bool:
        """Validate whether a ticker symbol exists on the exchange.

        Args:
            ticker: Stock ticker symbol to validate.

        Returns:
            True if the ticker is valid, False otherwise.
        """

    @abstractmethod
    def get_trend_data(self, ticker: str) -> Optional[TrendData]:
        """Fetch trend information for a ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            TrendData if available, None otherwise.
        """

    @abstractmethod
    def get_top_gainers(self, limit: int = 10) -> list[TrendData]:
        """Fetch top gaining stocks in the current market.

        Args:
            limit: Maximum number of gainers to return.

        Returns:
            List of TrendData for top gaining stocks.
        """