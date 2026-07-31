"""Investment option service — fetches and ranks European investment options.

Loads the curated ticker universe, fetches current prices and 5-year
history from the market data provider, calculates performance deltas
and benefit scores, and provides filtering and sorting capabilities.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import datetime, timedelta

from app.config import config
from app.data.eu_ticker_universes import AssetClass, TickerEntry, get_all_entries
from app.models.investment_option import (
    BenefitScore,
    InvestmentOption,
    PerformanceDelta,
)
from app.providers.base import MarketDataProvider, PriceHistory
from app.utils.currency import convert_amount
from app.utils.interruptible_executor import (
    DEFAULT_OVERALL_TIMEOUT_SECONDS,
    map_parallel,
)

# Callback signature for progress reporting: (completed, total).
ProgressCallback = Callable[[int, int], None]


def _to_finite_float(value: object) -> float | None:
    """Convert value to float, returning None for non-finite values."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


class InvestmentOptionService:
    """Service for fetching and ranking European investment options."""

    def __init__(
        self,
        provider: MarketDataProvider,
        base_currency: str = config.base_currency,
    ) -> None:
        self._provider = provider
        self._base_currency = base_currency.upper()
        self._cache: dict[str, InvestmentOption] = {}
        self._history_cache: dict[str, PriceHistory] = {}
        self._currency_cache: dict[str, str] = {}
        self._last_fetch_time: datetime | None = None

    def load_ticker_universe(self) -> list[TickerEntry]:
        """Load the curated European ticker universe.

        Returns:
            List of all TickerEntry objects (stocks + ETFs + bond ETFs).
        """
        return get_all_entries()

    def fetch_all_options(
        self,
        portfolio_tickers: list[str] | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> list[InvestmentOption]:
        """Fetch all European investment options with current prices.

        Args:
            portfolio_tickers: Tickers already in the user's portfolio.
            progress_callback: Optional ``(completed, total)`` callback that
                is forwarded to the provider's bulk price fetch so the UI can
                render live progress while prices download.

        Returns:
            List of InvestmentOption with current prices, sorted by
            benefit score descending.
        """
        if portfolio_tickers is None:
            portfolio_tickers = []

        portfolio_set = {t.upper() for t in portfolio_tickers}
        entries = self.load_ticker_universe()
        tickers = [e.ticker for e in entries]

        prices = self._provider.get_current_prices(tickers, progress_callback)
        self._last_fetch_time = datetime.utcnow()

        options: list[InvestmentOption] = []
        for entry in entries:
            quote = prices.get(entry.ticker)
            if quote is None:
                # Provider failed for this ticker — use cached or skip
                cached = self._cache.get(entry.ticker)
                if cached is None:
                    continue
                options.append(cached)
                continue

            self._currency_cache[entry.ticker] = quote.currency
            price_in_base = convert_amount(
                quote.price,
                source_currency=quote.currency,
                target_currency=self._base_currency,
                provider=self._provider,
            )

            # P/E ratio — reads from the provider's .info cache (populated
            # during get_current_prices above), so zero extra network calls.
            # Bonds return None (no trailingPE in .info).
            pe_ratio = self._provider.get_pe_ratio(entry.ticker)

            option = InvestmentOption(
                ticker=entry.ticker,
                name=entry.name,
                exchange=entry.exchange,
                asset_class=entry.asset_class,
                sector=entry.sector,
                current_price=price_in_base,
                currency=self._base_currency,
                in_portfolio=entry.ticker.upper() in portfolio_set,
                pe_ratio=pe_ratio,
            )
            self._cache[entry.ticker] = option
            options.append(option)

        return options

    def prefetch_histories(
        self,
        tickers: list[str],
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        """Fetch 5Y price histories for multiple tickers in parallel.

        Uses ThreadPoolExecutor to parallelize HTTP requests, then
        caches results so subsequent calls to calculate_performance_deltas,
        calculate_benefit_score, and prepare_eu_chart_data are instant.
        Already-cached tickers are skipped, making repeated calls idempotent
        (e.g. across Streamlit reruns).

        Args:
            tickers: List of ticker symbols to prefetch histories for.
            progress_callback: Optional ``(completed, total)`` callback for
                progress reporting, invoked from the main thread as each
                ticker's history resolves.
        """
        # Filter out already-cached tickers
        to_fetch = [t for t in tickers if t not in self._history_cache]

        if not to_fetch:
            # Everything already cached — report full completion if asked.
            if progress_callback is not None:
                progress_callback(0, 0)
            return

        total = len(to_fetch)
        completed = 0

        def _fetch(ticker: str) -> tuple[str, PriceHistory | None]:
            try:
                return ticker, self._provider.get_price_history_5y(ticker)
            except Exception:
                return ticker, None

        def _on_result(item: tuple[str, PriceHistory | None]) -> None:
            nonlocal completed
            ticker, history = item
            if history is not None:
                self._history_cache[ticker] = history
            completed += 1
            if progress_callback is not None:
                progress_callback(completed, total)

        map_parallel(
            _fetch,
            to_fetch,
            max_workers=8,
            overall_timeout=DEFAULT_OVERALL_TIMEOUT_SECONDS,
            on_result=_on_result,
        )

    def has_cached_histories(self, tickers: list[str]) -> bool:
        """Return True if every ticker has a cached 5Y history.

        Lets the UI decide whether to show the (slow) history-loading
        progress bar or render instantly from cache on a Streamlit rerun.

        Args:
            tickers: Ticker symbols to check.

        Returns:
            True if all tickers are present in the history cache.
        """
        return all(t in self._history_cache for t in tickers)

    def get_options_by_category(
        self,
        options: list[InvestmentOption],
        asset_class: AssetClass,
    ) -> list[InvestmentOption]:
        """Filter options by asset class.

        Args:
            options: List of InvestmentOption to filter.
            asset_class: AssetClass to filter by.

        Returns:
            Filtered list of InvestmentOption.
        """
        return [o for o in options if o.asset_class == asset_class]

    def calculate_performance_deltas(
        self, ticker: str
    ) -> list[PerformanceDelta]:
        """Calculate 1Y, 3Y, and 5Y performance deltas for a ticker.

        Fetches 5-year price history and computes deltas for each period.
        If less data is available, marks the period as unavailable and
        uses the available range.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            List of PerformanceDelta for 1Y, 3Y, and 5Y periods.
        """
        history = self._get_history(ticker)
        if history is None or not history.closes:
            return []

        deltas: list[PerformanceDelta] = []
        now = history.dates[-1]

        for period_label, years in [("1Y", 1), ("3Y", 3), ("5Y", 5)]:
            target_start = now - timedelta(days=years * 365)
            delta = self._compute_delta(
                history, period_label, target_start, now
            )
            if delta is not None:
                deltas.append(delta)

        return deltas

    def calculate_benefit_score(
        self,
        ticker: str,
        volume: float = 0.0,
        max_volume: float = 1.0,
        deltas: list[PerformanceDelta] | None = None,
    ) -> BenefitScore:
        """Calculate composite benefit score for an investment option.

        Combines 1-year momentum, 5-year return, and trading volume
        into a single score normalized to 0.0-1.0.

        Args:
            ticker: Stock ticker symbol.
            volume: Recent average trading volume.
            max_volume: Maximum volume in the category (for normalization).
            deltas: Pre-computed performance deltas to avoid re-fetching
                history. If None, deltas are fetched via
                calculate_performance_deltas().

        Returns:
            BenefitScore with component breakdown.
        """
        if deltas is None:
            deltas = self.calculate_performance_deltas(ticker)

        momentum = 0.0
        return_5y = 0.0

        for delta in deltas:
            if delta.period == "1Y":
                # Normalize momentum: +50% -> 1.0, -50% -> 0.0
                momentum = max(0.0, min(1.0, (delta.percentage_change + 50) / 100))
            elif delta.period == "5Y":
                # Normalize 5Y return: +200% -> 1.0, -100% -> 0.0
                return_5y = max(0.0, min(1.0, (delta.percentage_change + 100) / 300))

        volume_score = max(0.0, min(1.0, volume / max_volume)) if max_volume > 0 else 0.0

        return BenefitScore(
            momentum=round(momentum, 4),
            return_5y=round(return_5y, 4),
            volume=round(volume_score, 4),
        )

    def sort_options(
        self,
        options: list[InvestmentOption],
        criterion: str = "benefit_score",
    ) -> list[InvestmentOption]:
        """Sort investment options by the specified criterion.

        Args:
            options: List of InvestmentOption to sort.
            criterion: Sort key — "benefit_score", "return_5y", or "volume".

        Returns:
            Sorted list (descending order).
        """
        if criterion == "benefit_score":
            return sorted(options, key=lambda o: o.benefit_score, reverse=True)
        # Future: support return_5y and volume when those fields are populated
        return sorted(options, key=lambda o: o.benefit_score, reverse=True)

    def filter_options(
        self,
        options: list[InvestmentOption],
        search: str = "",
        exchanges: list[str] | None = None,
        sectors: list[str] | None = None,
        asset_classes: list[AssetClass] | None = None,
    ) -> list[InvestmentOption]:
        """Filter investment options by search term and criteria.

        Args:
            options: List of InvestmentOption to filter.
            search: Search substring (matches ticker, name, or sector).
            exchanges: List of exchanges to include (None = all).
            sectors: List of sectors to include (None = all).
            asset_classes: List of asset classes to include (None = all).

        Returns:
            Filtered list of InvestmentOption.
        """
        result = options

        if search:
            search_lower = search.lower()
            result = [
                o for o in result
                if search_lower in o.ticker.lower()
                or search_lower in o.name.lower()
                or search_lower in o.sector.lower()
            ]

        if exchanges:
            result = [o for o in result if o.exchange in exchanges]

        if sectors:
            result = [o for o in result if o.sector in sectors]

        if asset_classes:
            result = [o for o in result if o.asset_class in asset_classes]

        return result

    def get_last_fetch_time(self) -> datetime | None:
        """Return the timestamp of the last successful fetch.

        Returns:
            Datetime of last fetch, or None if never fetched.
        """
        return self._last_fetch_time

    def is_data_stale(self, threshold_hours: int = 1) -> bool:
        """Check if cached data is stale.

        Args:
            threshold_hours: Staleness threshold in hours.

        Returns:
            True if data is stale or unavailable, False otherwise.
        """
        if self._last_fetch_time is None:
            return True
        return datetime.utcnow() - self._last_fetch_time > timedelta(hours=threshold_hours)

    def prepare_eu_chart_data(
        self, ticker: str, period: str = "5Y"
    ) -> dict[str, list] | None:
        """Prepare price history data for Plotly chart rendering.

        Args:
            ticker: Stock ticker symbol.
            period: Time range — "1Y", "3Y", or "5Y".

        Returns:
            Dictionary with dates and closes for Plotly, or None.
        """
        history = self._get_history(ticker)
        if history is None or not history.dates:
            return None

        # Filter by period
        if period == "1Y":
            cutoff = history.dates[-1] - timedelta(days=365)
            filtered = [
                (d, c_val)
                for d, c in zip(history.dates, history.closes, strict=False)
                if d >= cutoff and (c_val := _to_finite_float(c)) is not None
            ]
        elif period == "3Y":
            cutoff = history.dates[-1] - timedelta(days=3 * 365)
            filtered = [
                (d, c_val)
                for d, c in zip(history.dates, history.closes, strict=False)
                if d >= cutoff and (c_val := _to_finite_float(c)) is not None
            ]
        else:
            filtered = [
                (d, c_val)
                for d, c in zip(history.dates, history.closes, strict=False)
                if (c_val := _to_finite_float(c)) is not None
            ]

        if not filtered:
            return None

        dates, closes = zip(*filtered, strict=False)
        start_price = closes[0]
        if start_price == 0:
            return None

        return {
            "ticker": ticker,
            "dates": [d.strftime("%Y-%m-%d") for d in dates],
            "closes": list(closes),
            "pct_changes": [
                round(((c - start_price) / start_price) * 100, 2) for c in closes
            ],
        }

    def _get_history(self, ticker: str) -> PriceHistory | None:
        """Get 5Y price history for a ticker, using cache if available.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            PriceHistory if available, None otherwise.
        """
        if ticker in self._history_cache:
            return self._history_cache[ticker]

        history = self._provider.get_price_history_5y(ticker)
        if history is not None:
            source_currency = self._currency_cache.get(ticker, self._base_currency)
            converted_history = PriceHistory(
                ticker=history.ticker,
                dates=history.dates,
                opens=[
                    convert_amount(v, source_currency, self._base_currency, self._provider)
                    for v in history.opens
                ],
                highs=[
                    convert_amount(v, source_currency, self._base_currency, self._provider)
                    for v in history.highs
                ],
                lows=[
                    convert_amount(v, source_currency, self._base_currency, self._provider)
                    for v in history.lows
                ],
                closes=[
                    convert_amount(v, source_currency, self._base_currency, self._provider)
                    for v in history.closes
                ],
                volumes=history.volumes,
            )
            self._history_cache[ticker] = converted_history
            return converted_history
        return history

    def _compute_delta(
        self,
        history: PriceHistory,
        period_label: str,
        target_start: datetime,
        end_date: datetime,
    ) -> PerformanceDelta | None:
        """Compute a performance delta from price history.

        Finds the closest date to target_start and computes the change.

        Args:
            history: PriceHistory data.
            period_label: Period label (e.g., "1Y").
            target_start: Target start date.
            end_date: End date.

        Returns:
            PerformanceDelta if computable, None otherwise.
        """
        if not history.dates or not history.closes:
            return None

        # Find the closest date to target_start
        start_idx = 0
        for i, d in enumerate(history.dates):
            if d <= target_start:
                start_idx = i
            else:
                break

        start_price = _to_finite_float(history.closes[start_idx])
        end_price = _to_finite_float(history.closes[-1])
        if start_price is None or end_price is None or start_price == 0:
            return None

        absolute_change = end_price - start_price
        percentage_change = (absolute_change / start_price) * 100

        # Check if we have full data for this period
        actual_start = history.dates[start_idx]
        available = (end_date - actual_start).days >= (period_label == "5Y" and 1825 or 1095) - 30

        return PerformanceDelta(
            period=period_label,
            start_date=actual_start,
            end_date=end_date,
            start_price=round(start_price, 2),
            end_price=round(end_price, 2),
            absolute_change=round(absolute_change, 2),
            percentage_change=round(percentage_change, 2),
            available=available,
        )
