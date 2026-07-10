"""yfinance market data provider implementation.

Uses the yfinance library to fetch market data from Yahoo Finance.
No API key required for basic usage.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import yfinance as yf

from app.providers.base import (
    MarketDataProvider,
    PriceHistory,
    PriceQuote,
    TrendData,
)

# Map period strings to yfinance period format
_PERIOD_MAP: dict[str, str] = {
    "1D": "1d",
    "1W": "5d",
    "1M": "1mo",
    "3M": "3mo",
    "1Y": "1y",
}


class YFinanceProvider(MarketDataProvider):
    """Market data provider using the yfinance library."""

    def get_current_price(self, ticker: str) -> Optional[PriceQuote]:
        """Fetch the current price for a single ticker via yfinance."""
        try:
            info = yf.Ticker(ticker).info
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            if price is None:
                return None
            currency = info.get("currency", "USD")
            return PriceQuote(
                ticker=ticker,
                price=float(price),
                currency=currency,
                timestamp=datetime.utcnow(),
            )
        except Exception:
            return None

    def get_current_prices(self, tickers: list[str]) -> dict[str, PriceQuote]:
        """Fetch current prices for multiple tickers via yfinance."""
        results: dict[str, PriceQuote] = {}
        for ticker in tickers:
            quote = self.get_current_price(ticker)
            if quote is not None:
                results[ticker] = quote
        return results

    def get_price_history(
        self, ticker: str, period: str = "1M"
    ) -> Optional[PriceHistory]:
        """Fetch historical price data for a ticker via yfinance."""
        try:
            yf_period = _PERIOD_MAP.get(period, "1mo")
            hist = yf.Ticker(ticker).history(period=yf_period)
            if hist.empty:
                return None

            dates = [idx.to_pydatetime() for idx in hist.index]
            return PriceHistory(
                ticker=ticker,
                dates=dates,
                opens=hist["Open"].tolist(),
                highs=hist["High"].tolist(),
                lows=hist["Low"].tolist(),
                closes=hist["Close"].tolist(),
                volumes=[int(v) for v in hist["Volume"].tolist()],
            )
        except Exception:
            return None

    def validate_ticker(self, ticker: str) -> bool:
        """Validate whether a ticker symbol exists on Yahoo Finance."""
        try:
            info = yf.Ticker(ticker).info
            return info.get("regularMarketPrice") is not None
        except Exception:
            return False

    def get_trend_data(self, ticker: str) -> Optional[TrendData]:
        """Fetch trend information for a ticker via yfinance."""
        try:
            hist = yf.Ticker(ticker).history(period="1mo")
            if hist.empty:
                return None

            closes = hist["Close"].tolist()
            if len(closes) < 2:
                return None

            change_percent = ((closes[-1] - closes[0]) / closes[0]) * 100

            if change_percent > 2.0:
                direction = "up"
            elif change_percent < -2.0:
                direction = "down"
            else:
                direction = "flat"

            info = yf.Ticker(ticker).info
            sector = info.get("sector", "Unknown")

            confidence = min(abs(change_percent) / 10.0, 1.0)

            return TrendData(
                ticker=ticker,
                trend_direction=direction,
                change_percent=round(change_percent, 2),
                sector=sector,
                confidence_score=round(confidence, 2),
            )
        except Exception:
            return None

    def get_top_gainers(self, limit: int = 10) -> list[TrendData]:
        """Fetch top gaining stocks. Uses a curated list for demonstration.

        In production, this would query a market screener API.
        """
        # Curated list of popular tickers to check for trends
        popular_tickers = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
            "JPM", "V", "JNJ", "WMT", "PG", "UNH", "HD", "MA",
        ]
        results: list[TrendData] = []
        for ticker in popular_tickers[:limit]:
            trend = self.get_trend_data(ticker)
            if trend is not None:
                results.append(trend)

        # Sort by change_percent descending
        results.sort(key=lambda t: t.change_percent, reverse=True)
        return results[:limit]