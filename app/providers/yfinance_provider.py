"""yfinance market data provider implementation.

Uses the yfinance library to fetch market data from Yahoo Finance.
No API key required for basic usage.
"""

from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import yfinance as yf

from app.config import config
from app.data.four_fund_universe import FundEntry, get_all_funds
from app.models.fund_profile import FundProfile
from app.models.investment_option import ExchangeRate
from app.providers.base import (
    MarketDataProvider,
    PriceHistory,
    PriceQuote,
    ProgressCallback,
    TrendData,
)
from app.utils.currency import convert_amount


def _safe_float(value: object) -> float | None:
    """Convert a value to float, returning None for NaN/missing data.

    yfinance sometimes returns float('nan') instead of None for fields
    like threeYearAverageReturn/fiveYearAverageReturn. A NaN passes the
    `is not None` check but formats as "+nan%" — normalize it to None.

    Args:
        value: Raw value from yfinance info dict.

    Returns:
        Float value, or None if value is None or NaN.
    """
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


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

    def __init__(self) -> None:
        # In-memory cache of FX rates keyed by "SOURCE->TARGET" (uppercase).
        # Both successful rates and None lookups are cached to avoid redundant
        # HTTP requests for repeated currency pairs within a session.
        self._fx_cache: dict[str, ExchangeRate | None] = {}

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

    def get_current_prices(
        self,
        tickers: list[str],
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, PriceQuote]:
        """Fetch current prices for multiple tickers via yfinance.

        Prices are fetched concurrently with a thread pool (8 workers) so
        that, for example, the ~47 European tickers load in a few seconds
        rather than ~47 sequential HTTP round-trips. When a
        ``progress_callback`` is provided it is invoked as
        ``progress_callback(completed, total)`` from the main thread as each
        ticker resolves, enabling the UI to render a live progress bar.

        Args:
            tickers: List of stock ticker symbols.
            progress_callback: Optional ``(completed, total)`` progress hook.

        Returns:
            Dictionary mapping ticker to PriceQuote. Invalid tickers are omitted.
        """
        if not tickers:
            return {}

        results: dict[str, PriceQuote] = {}
        total = len(tickers)
        completed = 0

        # ThreadPoolExecutor is safe here: each task is an independent
        # yfinance HTTP call with no shared mutable state.
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_ticker = {
                executor.submit(self.get_current_price, ticker): ticker
                for ticker in tickers
            }

            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    quote = future.result()
                    if quote is not None:
                        results[ticker] = quote
                except Exception:
                    # Individual ticker failures are silently skipped so a
                    # single bad ticker never aborts the whole batch.
                    pass
                completed += 1
                if progress_callback is not None:
                    progress_callback(completed, total)

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
        Results are cached per currency pair for the life of the provider
        instance so that converting a large batch of prices (or many OHLC
        points) does not issue one HTTP request per conversion.

        Args:
            source_currency: Source currency code (e.g., "GBP").
            target_currency: Target currency code (e.g., "EUR").

        Returns:
            ExchangeRate if available, None otherwise.
        """
        src = source_currency.upper()
        target = target_currency.upper()

        if src == target:
            return ExchangeRate(
                source_currency=src,
                target_currency=target,
                rate=1.0,
                timestamp=datetime.utcnow(),
            )

        cache_key = f"{src}->{target}"
        if cache_key in self._fx_cache:
            return self._fx_cache[cache_key]

        rate = self._fetch_exchange_rate(src, target)
        self._fx_cache[cache_key] = rate
        return rate

    def clear_fx_cache(self) -> None:
        """Clear the in-memory FX rate cache.

        Useful when the user explicitly refreshes data and wants fresh
        conversion rates rather than the session-cached values.
        """
        self._fx_cache.clear()

    def _fetch_exchange_rate(self, src: str, target: str) -> ExchangeRate | None:
        """Perform a single (uncached) FX lookup via yfinance.

        Args:
            src: Upper-case source currency code.
            target: Upper-case target currency code.

        Returns:
            ExchangeRate if available, None otherwise.
        """
        try:
            fx_ticker = f"{src}{target}=X"
            info = yf.Ticker(fx_ticker).info
            rate = info.get("regularMarketPrice")
            if rate is None:
                return None

            return ExchangeRate(
                source_currency=src,
                target_currency=target,
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
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            price = _safe_float(info.get("currentPrice"))
            if price is None:
                price = _safe_float(info.get("regularMarketPrice"))
            if price is None:
                return None

            # Look up static metadata from the curated universe
            entry = self._find_fund_entry(ticker)
            if entry is None:
                return None

            # TER: yfinance returns as a decimal (e.g., 0.0012 for 0.12%)
            # European ETFs often don't have TER in yfinance, so fall back
            # to the curated TER from the FundEntry
            ter_raw = _safe_float(info.get("annualReportExpenseRatio"))
            ter = ter_raw * 100 if ter_raw is not None else entry.ter

            # AUM: use totalAssets when available, otherwise estimate from
            # fund operations metadata for UCITS tickers where Yahoo omits
            # totalAssets in the summary info payload.
            aum = self._extract_aum(info, ticker_obj, ticker)

            # Returns: yfinance returns as decimals (e.g., 0.08 for 8%).
            # Use _safe_float to normalize NaN (which yfinance sometimes
            # returns instead of None) to None, preventing "+nan%" in the UI.
            return_1y_raw = _safe_float(info.get("ytdReturn"))
            return_1y = round(return_1y_raw * 100, 2) if return_1y_raw is not None else None
            return_3y_raw = _safe_float(info.get("threeYearAverageReturn"))
            return_3y = round(return_3y_raw * 100, 2) if return_3y_raw is not None else None
            return_5y_raw = _safe_float(info.get("fiveYearAverageReturn"))
            return_5y = round(return_5y_raw * 100, 2) if return_5y_raw is not None else None

            # Inception date
            inception_date = None
            inception_raw = info.get("inceptionDate")
            if inception_raw is not None:
                try:
                    inception_date = datetime.fromtimestamp(inception_raw)
                except (ValueError, TypeError, OSError):
                    inception_date = None

            source_currency = str(info.get("currency", "EUR"))
            base_currency = config.base_currency.upper()
            price_base = convert_amount(
                price,
                source_currency=source_currency,
                target_currency=base_currency,
                provider=self,
            )
            aum_base = (
                convert_amount(
                    aum,
                    source_currency=source_currency,
                    target_currency=base_currency,
                    provider=self,
                )
                if aum > 0
                else aum
            )

            return FundProfile(
                ticker=ticker,
                name=entry.name,
                category=entry.category,
                fund_family=entry.fund_family,
                ter=round(ter, 4),
                aum=aum_base,
                inception_date=inception_date,
                replication=entry.replication,
                distribution=entry.distribution,
                return_1y=return_1y,
                return_3y=return_3y,
                return_5y=return_5y,
                currency=base_currency,
                current_price=price_base,
                is_available=True,
            )
        except Exception:
            return None

    @staticmethod
    def _extract_aum(
        info: dict[str, object],
        ticker_obj: yf.Ticker,
        ticker: str,
    ) -> float:
        """Extract AUM in trading currency from yfinance metadata.

        Prefer ``info['totalAssets']`` (already currency-denominated).
        For some UCITS listings, Yahoo leaves ``totalAssets`` empty while
        exposing ``Total Net Assets`` in ``funds_data.fund_operations``.
        In that case we estimate AUM using:

            Total Net Assets * NAV * 1,000

        Returns:
            AUM as a positive float, or 0.0 if unavailable.
        """
        total_assets = _safe_float(info.get("totalAssets"))
        if total_assets is not None and total_assets > 0:
            return total_assets

        try:
            fund_operations = ticker_obj.funds_data.fund_operations
            total_net_assets = _safe_float(
                fund_operations.loc["Total Net Assets", ticker]
            )
        except Exception:
            return 0.0

        if total_net_assets is None or total_net_assets <= 0:
            return 0.0

        nav_price = _safe_float(info.get("navPrice"))
        if nav_price is None:
            nav_price = _safe_float(info.get("regularMarketPrice"))
        if nav_price is None:
            nav_price = _safe_float(info.get("currentPrice"))
        if nav_price is None or nav_price <= 0:
            return 0.0

        return total_net_assets * nav_price * 1_000.0

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
