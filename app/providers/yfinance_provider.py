"""yfinance market data provider implementation.

Uses the yfinance library to fetch market data from Yahoo Finance.
No API key required for basic usage.
"""

from __future__ import annotations

from datetime import datetime

import yfinance as yf

from app.data.four_fund_universe import FundEntry, get_all_funds
from app.models.fund_profile import FundProfile
from app.models.investment_option import ExchangeRate
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

    def get_current_price(self, ticker: str) -> PriceQuote | None:
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
    ) -> PriceHistory | None:
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

    def get_trend_data(self, ticker: str) -> TrendData | None:
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

    def get_price_history_5y(self, ticker: str) -> PriceHistory | None:
        """Fetch 5-year historical price data for a ticker via yfinance.

        Supports European exchange-suffixed tickers (e.g., SAP.DE, ASML.AS).
        Returns all available data if less than 5 years exists.

        Args:
            ticker: Stock ticker symbol (supports exchange suffixes).

        Returns:
            PriceHistory spanning up to 5 years, or None if unavailable.
        """
        try:
            hist = yf.Ticker(ticker).history(period="5y")
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

    def get_exchange_rate(
        self, source_currency: str, target_currency: str
    ) -> ExchangeRate | None:
        """Fetch exchange rate between two currencies via yfinance.

        Uses Yahoo Finance FX tickers (e.g., GBPEUR=X for GBP to EUR).

        Args:
            source_currency: Source currency code (e.g., "GBP").
            target_currency: Target currency code (e.g., "EUR").

        Returns:
            ExchangeRate if available, None otherwise.
        """
        if source_currency == target_currency:
            return ExchangeRate(
                source_currency=source_currency,
                target_currency=target_currency,
                rate=1.0,
                timestamp=datetime.utcnow(),
            )

        try:
            fx_ticker = f"{source_currency}{target_currency}=X"
            info = yf.Ticker(fx_ticker).info
            rate = info.get("regularMarketPrice")
            if rate is None:
                return None

            return ExchangeRate(
                source_currency=source_currency,
                target_currency=target_currency,
                rate=float(rate),
                timestamp=datetime.utcnow(),
            )
        except Exception:
            return None

    def get_fund_info(self, ticker: str) -> FundProfile | None:
        """Fetch extended fund metadata (TER, AUM, returns) via yfinance.

        Retrieves ETF-specific fields from yfinance's info dict:
        annualReportExpenseRatio, totalAssets, ytdReturn,
        threeYearAverageReturn, fiveYearAverageReturn, inceptionDate.

        Falls back to the curated FundEntry for static metadata
        (category, replication, distribution) when yfinance doesn't
        provide those fields.

        Args:
            ticker: ETF ticker symbol (e.g., "EUNL.DE").

        Returns:
            FundProfile if data is available, None otherwise.
        """
        try:
            info = yf.Ticker(ticker).info
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            if price is None:
                return None

            # Look up static metadata from the curated universe
            entry = self._find_fund_entry(ticker)
            if entry is None:
                return None

            # TER: yfinance returns as a decimal (e.g., 0.0012 for 0.12%)
            # European ETFs often don't have TER in yfinance, so fall back
            # to the curated TER from the FundEntry
            ter_raw = info.get("annualReportExpenseRatio")
            ter = float(ter_raw * 100) if ter_raw is not None else entry.ter

            # AUM: yfinance returns totalAssets in the fund's currency
            aum = float(info.get("totalAssets", 0) or 0)

            # Returns: yfinance returns as decimals (e.g., 0.08 for 8%)
            return_1y_raw = info.get("ytdReturn")
            return_1y = (
                float(return_1y_raw * 100) if return_1y_raw is not None else None
            )
            return_3y_raw = info.get("threeYearAverageReturn")
            return_3y = (
                float(return_3y_raw * 100) if return_3y_raw is not None else None
            )
            return_5y_raw = info.get("fiveYearAverageReturn")
            return_5y = (
                float(return_5y_raw * 100) if return_5y_raw is not None else None
            )

            # Inception date
            inception_date = None
            inception_raw = info.get("inceptionDate")
            if inception_raw is not None:
                try:
                    inception_date = datetime.fromtimestamp(inception_raw)
                except (ValueError, TypeError, OSError):
                    inception_date = None

            currency = info.get("currency", "EUR")

            return FundProfile(
                ticker=ticker,
                name=entry.name,
                category=entry.category,
                fund_family=entry.fund_family,
                ter=round(ter, 4),
                aum=aum,
                inception_date=inception_date,
                replication=entry.replication,
                distribution=entry.distribution,
                return_1y=round(return_1y, 2) if return_1y is not None else None,
                return_3y=round(return_3y, 2) if return_3y is not None else None,
                return_5y=round(return_5y, 2) if return_5y is not None else None,
                currency=currency,
                current_price=float(price),
                is_available=True,
            )
        except Exception:
            return None

    @staticmethod
    def _find_fund_entry(ticker: str) -> FundEntry | None:
        """Look up a FundEntry from the curated universe by ticker.

        Args:
            ticker: ETF ticker symbol.

        Returns:
            FundEntry if found, None otherwise.
        """
        for entry in get_all_funds():
            if entry.ticker == ticker:
                return entry
        return None
