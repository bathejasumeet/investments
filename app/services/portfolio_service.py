"""Portfolio service — business logic for portfolio calculations.

Handles portfolio value calculation, gain/loss computation,
portfolio summaries, and data freshness checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.holding import Holding
from app.config import config
from app.providers.base import MarketDataProvider, PriceQuote
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository
from app.utils.currency import convert_amount


@dataclass(frozen=True)
class HoldingSummary:
    """Summary of a single holding with calculated values."""

    ticker: str
    quantity: float
    purchase_price: float
    current_price: float
    current_value: float
    absolute_gain: float
    percentage_gain: float
    currency: str = "EUR"


@dataclass(frozen=True)
class PortfolioSummary:
    """Aggregate summary of the entire portfolio."""

    holdings: list[HoldingSummary] = field(default_factory=list)
    total_value: float = 0.0
    total_cost_basis: float = 0.0
    total_gain_loss: float = 0.0
    total_percentage_gain: float = 0.0
    last_updated: Optional[datetime] = None
    is_stale: bool = False
    currency: str = "EUR"


class PortfolioService:
    """Service for portfolio calculations and summaries."""

    def __init__(
        self,
        holding_repo: Optional[HoldingRepository],
        price_repo: Optional[PriceRepository],
        provider: MarketDataProvider,
        session: Session,
        base_currency: str = config.base_currency,
    ) -> None:
        self._holding_repo = holding_repo
        self._price_repo = price_repo
        self._provider = provider
        self._session = session
        self._base_currency = base_currency.upper()

    def _to_base_currency(self, amount: float, source_currency: str) -> float:
        """Convert an amount from source currency into configured base currency."""
        return convert_amount(
            amount,
            source_currency=source_currency,
            target_currency=self._base_currency,
            provider=self._provider,
        )

    def _get_current_prices(self, tickers: list[str]) -> dict[str, PriceQuote]:
        if not tickers:
            return {}
        return self._provider.get_current_prices(tickers)

    def calculate_total_value(self, holdings: list[Holding]) -> float:
        if not holdings:
            return 0.0
        tickers = [h.ticker for h in holdings]
        prices = self._get_current_prices(tickers)
        total = 0.0
        for holding in holdings:
            quote = prices.get(holding.ticker)
            if quote:
                price_in_base = self._to_base_currency(quote.price, quote.currency)
                total += holding.quantity * price_in_base
        return total

    def calculate_gain_loss(self, holding: Holding) -> HoldingSummary:
        quote = self._provider.get_current_price(holding.ticker)
        current_price = (
            self._to_base_currency(quote.price, quote.currency)
            if quote
            else 0.0
        )
        current_value = holding.quantity * current_price
        cost_basis = holding.quantity * holding.purchase_price
        absolute_gain = current_value - cost_basis
        if holding.purchase_price > 0:
            percentage_gain = (
                (current_price - holding.purchase_price) / holding.purchase_price
            ) * 100
        else:
            percentage_gain = 0.0
        return HoldingSummary(
            ticker=holding.ticker,
            quantity=holding.quantity,
            purchase_price=holding.purchase_price,
            current_price=current_price,
            current_value=current_value,
            absolute_gain=absolute_gain,
            percentage_gain=percentage_gain,
            currency=self._base_currency,
        )

    def get_portfolio_summary(
        self, holdings: list[Holding]
    ) -> PortfolioSummary:
        if not holdings:
            return PortfolioSummary()
        tickers = [h.ticker for h in holdings]
        prices = self._get_current_prices(tickers)
        holding_summaries: list[HoldingSummary] = []
        total_value = 0.0
        total_cost = 0.0
        for holding in holdings:
            quote = prices.get(holding.ticker)
            current_price = (
                self._to_base_currency(quote.price, quote.currency)
                if quote
                else 0.0
            )
            current_value = holding.quantity * current_price
            cost_basis = holding.quantity * holding.purchase_price
            absolute_gain = current_value - cost_basis
            if holding.purchase_price > 0:
                pct_gain = (
                    (current_price - holding.purchase_price)
                    / holding.purchase_price
                ) * 100
            else:
                pct_gain = 0.0
            holding_summaries.append(
                HoldingSummary(
                    ticker=holding.ticker,
                    quantity=holding.quantity,
                    purchase_price=holding.purchase_price,
                    current_price=current_price,
                    current_value=current_value,
                    absolute_gain=absolute_gain,
                    percentage_gain=pct_gain,
                    currency=self._base_currency,
                )
            )
            total_value += current_value
            total_cost += cost_basis
        total_gain = total_value - total_cost
        total_pct = (total_gain / total_cost * 100) if total_cost > 0 else 0.0
        last_updated = None
        if prices:
            timestamps = [q.timestamp for q in prices.values()]
            last_updated = max(timestamps) if timestamps else None
        is_stale = self.check_data_freshness(last_updated)
        return PortfolioSummary(
            holdings=holding_summaries,
            total_value=total_value,
            total_cost_basis=total_cost,
            total_gain_loss=total_gain,
            total_percentage_gain=total_pct,
            last_updated=last_updated,
            is_stale=is_stale,
            currency=self._base_currency,
        )

    def check_data_freshness(self, timestamp: Optional[datetime]) -> bool:
        if timestamp is None:
            return True
        return datetime.utcnow() - timestamp > timedelta(hours=1)

    def calculate_allocation(self, holdings: list[Holding]) -> dict[str, float]:
        if not holdings:
            return {}
        tickers = [h.ticker for h in holdings]
        prices = self._get_current_prices(tickers)
        values: dict[str, float] = {}
        total = 0.0
        for holding in holdings:
            quote = prices.get(holding.ticker)
            price = (
                self._to_base_currency(quote.price, quote.currency)
                if quote
                else 0.0
            )
            value = holding.quantity * price
            values[holding.ticker] = value
            total += value
        if total == 0:
            return {t: 0.0 for t in values}
        return {t: (v / total * 100) for t, v in values.items()}

    def calculate_sector_exposure(
        self, holdings: list[Holding]
    ) -> dict[str, float]:
        if not holdings:
            return {}
        tickers = [h.ticker for h in holdings]
        prices = self._get_current_prices(tickers)
        sector_values: dict[str, float] = {}
        total = 0.0
        for holding in holdings:
            quote = prices.get(holding.ticker)
            price = (
                self._to_base_currency(quote.price, quote.currency)
                if quote
                else 0.0
            )
            value = holding.quantity * price
            trend = self._provider.get_trend_data(holding.ticker)
            sector = trend.sector if trend else "Unknown"
            sector_values[sector] = sector_values.get(sector, 0.0) + value
            total += value
        if total == 0:
            return {}
        return {s: (v / total * 100) for s, v in sector_values.items()}

    def compare_holding_performance(
        self, holdings: list[Holding]
    ) -> list[HoldingSummary]:
        summaries: list[HoldingSummary] = []
        for holding in holdings:
            summaries.append(self.calculate_gain_loss(holding))
        summaries.sort(key=lambda s: s.percentage_gain, reverse=True)
        return summaries