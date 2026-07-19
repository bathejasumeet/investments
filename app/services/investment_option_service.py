"""Investment option service — fetches and ranks European investment options.

Loads the curated ticker universe, fetches current prices and 5-year
history from the market data provider, calculates performance deltas
and benefit scores, and provides filtering and sorting capabilities.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from app.data.eu_ticker_universes import AssetClass, TickerEntry, get_all_entries
from app.models.investment_option import (
    BenefitScore,
    InvestmentOption,
    PerformanceDelta,
)
from app.providers.base import MarketDataProvider, PriceHistory, PriceQuote


class InvestmentOptionService:
    """Service for fetching and ranking European investment options."""

    def __init__(self, provider: MarketDataProvider) -> None:
        self._provider = provider
        self._cache: dict[str, InvestmentOption] = {}
        self._last_fetch_time: Optional[datetime] = None

    def load_ticker_universe(self) -> list[TickerEntry]:
        """Load the curated European ticker universe.

        Returns:
            List of all TickerEntry objects (stocks + ETFs + bond ETFs).
        """
        return get_all_entries()

    def fetch_all_options(
        self,
        portfolio_tickers: Optional[list[str]] = None,
    ) -> list[InvestmentOption]:
        """Fetch all European investment options with current prices.

        Args:
            portfolio_tickers: Tickers already in the user's portfolio.

        Returns:
            List of InvestmentOption with current prices, sorted by
            benefit score descending.
        """
        if portfolio_tickers is None:
            portfolio_tickers = []

        portfolio_set = {t.upper() for t in portfolio_tickers}
        entries = self.load_ticker_universe()
        tickers = [e.ticker for e in entries]

        prices = self._provider.get_current_prices(tickers)
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

            option = InvestmentOption(
                ticker=entry.ticker,
                name=entry.name,
                exchange=entry.exchange,
                asset_class=entry.asset_class,
                sector=entry.sector,
                current_price=quote.price,
                currency=quote.currency,
                in_portfolio=entry.ticker.upper() in portfolio_set,
            )
            self._cache[entry.ticker] = option
            options.append(option)

        return options

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
        history = self._provider.get_price_history_5y(ticker)
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
    ) -> BenefitScore:
        """Calculate composite benefit score for an investment option.

        Combines 1-year momentum, 5-year return, and trading volume
        into a single score normalized to 0.0-1.0.

        Args:
            ticker: Stock ticker symbol.
            volume: Recent average trading volume.
            max_volume: Maximum volume in the category (for normalization).

        Returns:
            BenefitScore with component breakdown.
        """
        deltas = self.calculate_performance_deltas(ticker)

        momentum = 0.0
        return_5y = 0.0

        for delta in deltas:
            if delta.period == "1Y":
                # Normalize momentum: +50% → 1.0, -50% → 0.0
                momentum = max(0.0, min(1.0, (delta.percentage_change + 50) / 100))
            elif delta.period == "5Y":
                # Normalize 5Y return: +200% → 1.0, -100% → 0.0
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
        exchanges: Optional[list[str]] = None,
        sectors: Optional[list[str]] = None,
        asset_classes: Optional[list[AssetClass]] = None,
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

    def get_last_fetch_time(self) -> Optional[datetime]:
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
    ) -> Optional[dict[str, list]]:
        """Prepare price history data for Plotly chart rendering.

        Args:
            ticker: Stock ticker symbol.
            period: Time range — "1Y", "3Y", or "5Y".

        Returns:
            Dictionary with dates and closes for Plotly, or None.
        """
        history = self._provider.get_price_history_5y(ticker)
        if history is None or not history.dates:
            return None

        # Filter by period
        if period == "1Y":
            cutoff = history.dates[-1] - timedelta(days=365)
            filtered = [
                (d, c) for d, c in zip(history.dates, history.closes)
                if d >= cutoff
            ]
        elif period == "3Y":
            cutoff = history.dates[-1] - timedelta(days=3 * 365)
            filtered = [
                (d, c) for d, c in zip(history.dates, history.closes)
                if d >= cutoff
            ]
        else:
            filtered = list(zip(history.dates, history.closes))

        if not filtered:
            return None

        dates, closes = zip(*filtered)
        start_price = closes[0]

        return {
            "ticker": ticker,
            "dates": [d.strftime("%Y-%m-%d") for d in dates],
            "closes": list(closes),
            "pct_changes": [
                round(((c - start_price) / start_price) * 100, 2) for c in closes
            ],
        }

    def _compute_delta(
        self,
        history: PriceHistory,
        period_label: str,
        target_start: datetime,
        end_date: datetime,
    ) -> Optional[PerformanceDelta]:
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

        start_price = history.closes[start_idx]
        end_price = history.closes[-1]

        if start_price == 0:
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