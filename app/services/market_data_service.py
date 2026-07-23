"""Market data service — fetches and caches market prices.

Handles fetching current prices from the provider, caching to
the price repository, and serving cached data on failure.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.config import config
from app.providers.base import MarketDataProvider, PriceHistory, PriceQuote
from app.repositories.price_repository import PriceRepository


class MarketDataService:
    """Service for fetching and caching market data."""

    def __init__(
        self,
        provider: MarketDataProvider,
        price_repo: Optional[PriceRepository] = None,
    ) -> None:
        self._provider = provider
        self._price_repo = price_repo

    def fetch_current_prices(
        self, tickers: list[str]
    ) -> dict[str, PriceQuote]:
        """Fetch current prices for multiple tickers.

        Falls back to cached data if the provider fails.

        Args:
            tickers: List of ticker symbols.

        Returns:
            Dictionary mapping ticker to PriceQuote.
        """
        if not tickers:
            return {}

        try:
            prices = self._provider.get_current_prices(tickers)
            if prices:
                return prices
        except Exception:
            pass

        # Fall back to cached data
        if self._price_repo:
            return self._get_cached_prices(tickers)
        return {}

    def fetch_price_history(
        self, ticker: str, period: str = "1M"
    ) -> Optional[PriceHistory]:
        """Fetch price history for a ticker, caching the result.

        Args:
            ticker: Stock ticker symbol.
            period: Time range (1D, 1W, 1M, 3M, 1Y).

        Returns:
            PriceHistory if available, None otherwise.
        """
        try:
            history = self._provider.get_price_history(ticker, period)
            if history and self._price_repo:
                self._price_repo.save_price_points(history)
            return history
        except Exception:
            # Fall back to cached data
            if self._price_repo:
                return self._get_cached_history(ticker)
            return None

    def validate_ticker(self, ticker: str) -> bool:
        """Validate a ticker symbol against the market data provider.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            True if valid, False otherwise.
        """
        try:
            return self._provider.validate_ticker(ticker)
        except Exception:
            return False

    def get_last_update_time(self, ticker: str) -> Optional[datetime]:
        """Get the timestamp of the last price fetch for a ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Datetime of last fetch if available, None otherwise.
        """
        if self._price_repo:
            return self._price_repo.get_last_fetch_time(ticker)
        return None

    def _get_cached_prices(
        self, tickers: list[str]
    ) -> dict[str, PriceQuote]:
        """Retrieve cached prices from the price repository.

        Args:
            tickers: List of ticker symbols.

        Returns:
            Dictionary mapping ticker to PriceQuote from cache.
        """
        if not self._price_repo:
            return {}

        results: dict[str, PriceQuote] = {}
        for ticker in tickers:
            latest = self._price_repo.get_latest_price(ticker)
            if latest:
                results[ticker] = PriceQuote(
                    ticker=ticker,
                    price=latest.close,
                    currency=config.base_currency,
                    timestamp=latest.fetched_at,
                )
        return results

    def _get_cached_history(self, ticker: str) -> Optional[PriceHistory]:
        """Retrieve cached price history from the repository.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            PriceHistory from cache, or None.
        """
        if not self._price_repo:
            return None

        points = self._price_repo.get_history_by_ticker(ticker, days=365)
        if not points:
            return None

        return PriceHistory(
            ticker=ticker,
            dates=[p.date for p in points],
            opens=[p.open for p in points],
            highs=[p.high for p in points],
            lows=[p.low for p in points],
            closes=[p.close for p in points],
            volumes=[p.volume for p in points],
        )