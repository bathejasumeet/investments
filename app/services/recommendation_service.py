"""Recommendation service — generates investment recommendations.

Fetches top gainers, calculates momentum, ranks by confidence,
and detects portfolio overlap.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from app.config import config
from app.providers.base import MarketDataProvider, TrendData
from app.utils.currency import convert_amount


@dataclass(frozen=True)
class Recommendation:
    """A single investment recommendation."""

    ticker: str
    current_price: float
    trend_direction: str
    sector: str
    confidence_score: float
    change_percent: float
    currency: str = "EUR"
    in_portfolio: bool = False
    rationale: str = ""


class RecommendationService:
    """Service for generating investment recommendations."""

    def __init__(
        self,
        provider: MarketDataProvider,
        base_currency: str = config.base_currency,
    ) -> None:
        self._provider = provider
        self._base_currency = base_currency.upper()
        self._last_fetch_time: Optional[datetime] = None

    def get_recommendations(
        self,
        portfolio_tickers: Optional[list[str]] = None,
        limit: int = 10,
    ) -> list[Recommendation]:
        """Generate ranked investment recommendations.

        Args:
            portfolio_tickers: Tickers already in the portfolio.
            limit: Maximum number of recommendations.

        Returns:
            List of Recommendation sorted by confidence descending.
        """
        if portfolio_tickers is None:
            portfolio_tickers = []

        portfolio_set = {t.upper() for t in portfolio_tickers}

        # Fetch top gainers from provider
        trends = self._provider.get_top_gainers(limit=limit * 2)
        self._last_fetch_time = datetime.utcnow()

        recommendations: list[Recommendation] = []
        for trend in trends:
            quote = self._provider.get_current_price(trend.ticker)
            if quote:
                price = convert_amount(
                    quote.price,
                    source_currency=quote.currency,
                    target_currency=self._base_currency,
                    provider=self._provider,
                )
            else:
                price = 0.0

            in_portfolio = trend.ticker.upper() in portfolio_set

            rationale = self._build_rationale(trend, in_portfolio)

            recommendations.append(
                Recommendation(
                    ticker=trend.ticker,
                    current_price=price,
                    trend_direction=trend.trend_direction,
                    sector=trend.sector,
                    confidence_score=trend.confidence_score,
                    change_percent=trend.change_percent,
                    currency=self._base_currency,
                    in_portfolio=in_portfolio,
                    rationale=rationale,
                )
            )

        # Sort by confidence score descending
        recommendations.sort(key=lambda r: r.confidence_score, reverse=True)
        return recommendations[:limit]

    def check_freshness(self, timestamp: Optional[datetime]) -> bool:
        """Check if recommendation data is stale (> 1 hour old).

        Args:
            timestamp: The timestamp to check.

        Returns:
            True if stale or unavailable, False if fresh.
        """
        if timestamp is None:
            return True
        return datetime.utcnow() - timestamp > timedelta(hours=1)

    def get_last_fetch_time(self) -> Optional[datetime]:
        """Return the timestamp of the last recommendation fetch.

        Returns:
            Datetime of last fetch, or None if never fetched.
        """
        return self._last_fetch_time

    def _build_rationale(
        self, trend: TrendData, in_portfolio: bool
    ) -> str:
        """Build a human-readable rationale for a recommendation.

        Args:
            trend: TrendData for the recommendation.
            in_portfolio: Whether the ticker is already held.

        Returns:
            Rationale string.
        """
        direction_text = {
            "up": "showing strong upward momentum",
            "down": "in a downward trend (potential value opportunity)",
            "flat": "trading sideways with stable performance",
        }
        trend_text = direction_text.get(
            trend.trend_direction, "showing mixed signals"
        )

        parts = [
            f"{trend.ticker} is {trend_text}",
            f"with a {trend.change_percent:+.2f}% change in the past month",
            f"({trend.sector} sector)",
        ]

        if in_portfolio:
            parts.append("— you already hold this stock")

        return ". ".join(parts) + "."