"""Recommendation service — generates explainable investment recommendations.

Fetches top gainers, computes a transparent factor breakdown
(momentum, valuation proxy, volatility, volume, concentration impact),
ranks by the resulting composite confidence score, and detects
portfolio overlap.

Every recommendation carries a :class:`FactorBreakdown` so users can
see exactly *why* a ticker was recommended — no black-box scores.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.config import config
from app.providers.base import MarketDataProvider, PriceHistory, TrendData
from app.utils.currency import convert_amount

# --- Factor weights (MUST sum to 1.0) ---
_WEIGHT_MOMENTUM: float = 0.30
_WEIGHT_VALUATION: float = 0.20
_WEIGHT_VOLATILITY: float = 0.15
_WEIGHT_VOLUME: float = 0.15
_WEIGHT_CONCENTRATION: float = 0.20

# --- Normalization constants ---
_MAX_CHANGE_PERCENT: float = 20.0  # +20% → momentum 1.0, -20% → 0.0
_MAX_DAILY_VOLATILITY: float = 0.05  # 5% daily std-dev → volatility score 0.0
_REFERENCE_MAX_VOLUME: float = 100_000_000.0  # 100M shares/day → volume score 1.0


@dataclass(frozen=True)
class FactorScore:
    """A single explainable factor contributing to the recommendation score.

    Attributes:
        name: Human-readable factor name (e.g., "Momentum").
        score: Normalized score in the 0.0–1.0 range.
        weight: Weight in the composite score (all weights sum to 1.0).
        raw_value: The raw metric value before normalization.
        explanation: Human-readable explanation of how the score was derived.
    """

    name: str
    score: float
    weight: float
    raw_value: float
    explanation: str


@dataclass(frozen=True)
class FactorBreakdown:
    """Explainable breakdown of all factors behind a recommendation.

    Attributes:
        momentum: Price momentum factor (recent change percent).
        valuation: Valuation proxy factor (position in recent price range).
        volatility: Volatility factor (lower volatility → higher score).
        volume: Trading volume / liquidity factor.
        concentration: Portfolio concentration impact factor.
    """

    momentum: FactorScore
    valuation: FactorScore
    volatility: FactorScore
    volume: FactorScore
    concentration: FactorScore

    def all_factors(self) -> list[FactorScore]:
        """Return all five factor scores in display order."""
        return [
            self.momentum,
            self.valuation,
            self.volatility,
            self.volume,
            self.concentration,
        ]

    @property
    def composite_score(self) -> float:
        """Weighted composite score (0.0–1.0), rounded to 4 decimals."""
        return round(
            sum(f.score * f.weight for f in self.all_factors()),
            4,
        )


@dataclass(frozen=True)
class Recommendation:
    """A single investment recommendation with an explainable factor breakdown.

    The ``confidence_score`` is no longer a black-box number — it is the
    weighted sum of the scores in :attr:`factors`.
    """

    ticker: str
    current_price: float
    trend_direction: str
    sector: str
    confidence_score: float
    change_percent: float
    currency: str = "EUR"
    in_portfolio: bool = False
    rationale: str = ""
    factors: FactorBreakdown | None = None


class RecommendationService:
    """Service for generating explainable investment recommendations."""

    def __init__(
        self,
        provider: MarketDataProvider,
        base_currency: str = config.base_currency,
    ) -> None:
        self._provider = provider
        self._base_currency = base_currency.upper()
        self._last_fetch_time: datetime | None = None

    def get_recommendations(
        self,
        portfolio_tickers: list[str] | None = None,
        limit: int = 10,
    ) -> list[Recommendation]:
        """Generate ranked investment recommendations with factor breakdowns.

        Args:
            portfolio_tickers: Tickers already in the portfolio.
            limit: Maximum number of recommendations.

        Returns:
            List of Recommendation sorted by composite confidence descending.
        """
        if portfolio_tickers is None:
            portfolio_tickers = []

        portfolio_set = {t.upper() for t in portfolio_tickers}

        trends = self._provider.get_top_gainers(limit=limit * 2)
        self._last_fetch_time = datetime.utcnow()

        recommendations: list[Recommendation] = []
        for trend in trends:
            rec = self._build_recommendation(trend, portfolio_set)
            if rec is not None:
                recommendations.append(rec)

        recommendations.sort(key=lambda r: r.confidence_score, reverse=True)
        return recommendations[:limit]

    def check_freshness(self, timestamp: datetime | None) -> bool:
        """Check if recommendation data is stale (> 1 hour old).

        Args:
            timestamp: The timestamp to check.

        Returns:
            True if stale or unavailable, False if fresh.
        """
        if timestamp is None:
            return True
        return datetime.utcnow() - timestamp > timedelta(hours=1)

    def get_last_fetch_time(self) -> datetime | None:
        """Return the timestamp of the last recommendation fetch."""
        return self._last_fetch_time

    # ------------------------------------------------------------------
    # Internal: recommendation building
    # ------------------------------------------------------------------

    def _build_recommendation(
        self, trend: TrendData, portfolio_set: set[str]
    ) -> Recommendation | None:
        """Build a single recommendation with its factor breakdown.

        Args:
            trend: TrendData for the ticker.
            portfolio_set: Uppercased set of portfolio tickers.

        Returns:
            Recommendation with factors, or None if price unavailable.
        """
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
        history = self._provider.get_price_history(trend.ticker)
        factors = self._compute_factors(trend, history, in_portfolio)
        rationale = self._build_rationale(trend, in_portfolio, factors)

        return Recommendation(
            ticker=trend.ticker,
            current_price=price,
            trend_direction=trend.trend_direction,
            sector=trend.sector,
            confidence_score=factors.composite_score,
            change_percent=trend.change_percent,
            currency=self._base_currency,
            in_portfolio=in_portfolio,
            rationale=rationale,
            factors=factors,
        )

    def _compute_factors(
        self,
        trend: TrendData,
        history: PriceHistory | None,
        in_portfolio: bool,
    ) -> FactorBreakdown:
        """Compute all five explainable factors for a recommendation."""
        return FactorBreakdown(
            momentum=self._compute_momentum(trend.change_percent),
            valuation=self._compute_valuation(history),
            volatility=self._compute_volatility(history),
            volume=self._compute_volume(history),
            concentration=self._compute_concentration(in_portfolio),
        )

    # ------------------------------------------------------------------
    # Internal: individual factor computations
    # ------------------------------------------------------------------

    def _compute_momentum(self, change_percent: float) -> FactorScore:
        """Compute momentum factor from monthly change percent.

        Normalization: +20% → 1.0, -20% → 0.0 (linear).
        """
        score = max(
            0.0,
            min(1.0, (change_percent + _MAX_CHANGE_PERCENT) / (_MAX_CHANGE_PERCENT * 2)),
        )
        return FactorScore(
            name="Momentum",
            score=round(score, 4),
            weight=_WEIGHT_MOMENTUM,
            raw_value=change_percent,
            explanation=(
                f"{change_percent:+.2f}% price change over the past month. "
                f"Normalized to {score:.0%} (±{_MAX_CHANGE_PERCENT:.0f}% range)."
            ),
        )

    def _compute_valuation(
        self, history: PriceHistory | None
    ) -> FactorScore:
        """Compute valuation proxy from position in the recent price range.

        A price near the recent low scores high (better value); a price
        near the recent high scores low (expensive). Returns a neutral
        0.5 when insufficient history is available.
        """
        if history is None or not history.closes or not history.highs or not history.lows:
            return self._neutral_factor("Valuation", _WEIGHT_VALUATION)

        current = float(history.closes[-1])
        period_high = max(float(h) for h in history.highs)
        period_low = min(float(low) for low in history.lows)
        range_span = period_high - period_low

        position = 0.5 if range_span == 0 else (current - period_low) / range_span
        score = max(0.0, min(1.0, 1.0 - position))

        return FactorScore(
            name="Valuation",
            score=round(score, 4),
            weight=_WEIGHT_VALUATION,
            raw_value=position,
            explanation=(
                f"Current price {current:.2f} sits at {position:.0%} of the "
                f"recent range [{period_low:.2f}, {period_high:.2f}]. "
                f"Lower position = better value."
            ),
        )

    def _compute_volatility(
        self, history: PriceHistory | None
    ) -> FactorScore:
        """Compute volatility factor from std-dev of daily returns.

        Lower volatility → higher stability score. Returns a neutral
        0.5 when fewer than 2 data points are available.
        """
        if history is None or len(history.closes) < 2:
            return self._neutral_factor("Volatility", _WEIGHT_VOLATILITY)

        closes = [float(c) for c in history.closes]
        returns = [
            (closes[i] - closes[i - 1]) / closes[i - 1]
            for i in range(1, len(closes))
        ]
        vol = statistics.pstdev(returns) if len(returns) > 1 else 0.0
        score = max(0.0, min(1.0, 1.0 - (vol / _MAX_DAILY_VOLATILITY)))

        return FactorScore(
            name="Volatility",
            score=round(score, 4),
            weight=_WEIGHT_VOLATILITY,
            raw_value=vol,
            explanation=(
                f"Daily return std-dev: {vol:.4f} ({vol:.2%}). "
                f"Lower volatility = higher stability score."
            ),
        )

    def _compute_volume(
        self, history: PriceHistory | None
    ) -> FactorScore:
        """Compute volume / liquidity factor from average daily volume.

        Higher volume → higher liquidity score. Returns a neutral 0.5
        when no volume data is available.
        """
        if history is None or not history.volumes:
            return self._neutral_factor("Volume", _WEIGHT_VOLUME)

        avg_volume = sum(float(v) for v in history.volumes) / len(history.volumes)
        score = max(0.0, min(1.0, avg_volume / _REFERENCE_MAX_VOLUME))

        return FactorScore(
            name="Volume",
            score=round(score, 4),
            weight=_WEIGHT_VOLUME,
            raw_value=avg_volume,
            explanation=(
                f"Average volume: {avg_volume:,.0f} shares/day. "
                f"Normalized against {_REFERENCE_MAX_VOLUME:,.0f} reference."
            ),
        )

    def _compute_concentration(self, in_portfolio: bool) -> FactorScore:
        """Compute concentration impact factor from portfolio overlap.

        Tickers already held receive 0.0 (adding more increases
        concentration risk); new tickers receive 1.0 (adds diversification).
        """
        if in_portfolio:
            return FactorScore(
                name="Concentration",
                score=0.0,
                weight=_WEIGHT_CONCENTRATION,
                raw_value=1.0,
                explanation=(
                    "Already in your portfolio — adding more would "
                    "increase concentration risk."
                ),
            )
        return FactorScore(
            name="Concentration",
            score=1.0,
            weight=_WEIGHT_CONCENTRATION,
            raw_value=0.0,
            explanation="Not currently held — adds diversification to your portfolio.",
        )

    # ------------------------------------------------------------------
    # Internal: helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _neutral_factor(name: str, weight: float) -> FactorScore:
        """Create a neutral (0.5) factor score for missing data."""
        return FactorScore(
            name=name,
            score=0.5,
            weight=weight,
            raw_value=0.0,
            explanation="Insufficient data — neutral score assigned.",
        )

    def _build_rationale(
        self,
        trend: TrendData,
        in_portfolio: bool,
        factors: FactorBreakdown,
    ) -> str:
        """Build a human-readable rationale summarizing the factor breakdown.

        Args:
            trend: TrendData for the recommendation.
            in_portfolio: Whether the ticker is already held.
            factors: Computed factor breakdown.

        Returns:
            Rationale string referencing the top contributing factor.
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

        top_factor = max(factors.all_factors(), key=lambda f: f.score * f.weight)
        parts.append(f"Top driver: {top_factor.name} ({top_factor.score:.0%})")

        return ". ".join(parts) + "."
