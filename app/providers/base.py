"""Abstract market data provider interface.

Defines the contract that all market data providers must implement.
Uses the Strategy pattern to allow swapping API backends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from app.models.fund_profile import FundProfile
from app.models.investment_option import ExchangeRate

# Optional callback invoked as progress_callback(completed, total) during
# bulk fetch operations. Providers that parallelize should call it from the
# main thread (e.g. inside the as_completed loop) so the UI can update a
# progress bar.
ProgressCallback = Callable[[int, int], None]


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
    def get_current_price(self, ticker: str) -> PriceQuote | None:
        """Fetch the current price for a single ticker.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL").

        Returns:
            PriceQuote if successful, None if ticker is invalid or data unavailable.
        """

    @abstractmethod
    def get_current_prices(
        self,
        tickers: list[str],
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, PriceQuote]:
        """Fetch current prices for multiple tickers.

        Implementations should parallelize network requests and, when a
        ``progress_callback`` is supplied, invoke it as
        ``progress_callback(completed, total)`` as each ticker completes so
        the caller can surface feedback to the user.

        Args:
            tickers: List of stock ticker symbols.
            progress_callback: Optional callback ``(completed, total)`` for
                progress reporting. Defaults to None (no reporting).

        Returns:
            Dictionary mapping ticker to PriceQuote. Invalid tickers are omitted.
        """

    @abstractmethod
    def get_price_history(
        self, ticker: str, period: str = "1M"
    ) -> PriceHistory | None:
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
    def get_trend_data(self, ticker: str) -> TrendData | None:
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

    @abstractmethod
    def get_price_history_5y(self, ticker: str) -> PriceHistory | None:
        """Fetch 5-year historical price data for a ticker.

        Args:
            ticker: Stock ticker symbol (supports exchange suffixes).

        Returns:
            PriceHistory spanning up to 5 years if available, None otherwise.
        """

    @abstractmethod
    def get_exchange_rate(
        self, source_currency: str, target_currency: str
    ) -> ExchangeRate | None:
        """Fetch the exchange rate between two currencies.

        Args:
            source_currency: Source currency code (e.g., "GBP").
            target_currency: Target currency code (e.g., "EUR").

        Returns:
            ExchangeRate if available, None otherwise.
        """

    @abstractmethod
    def get_fund_info(self, ticker: str) -> FundProfile | None:
        """Fetch extended fund metadata (TER, AUM, returns) for an ETF ticker.

        Args:
            ticker: ETF ticker symbol (e.g., "EUNL.DE").

        Returns:
            FundProfile if data is available, None otherwise.
        """
