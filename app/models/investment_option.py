"""Data models for European investment options.

Contains dataclasses for investment options, performance deltas,
bond market context, exchange rates, and benefit scores.
These are plain dataclasses (not ORM models) since investment
options are fetched live from market data, not persisted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.data.eu_ticker_universes import AssetClass


@dataclass(frozen=True)
class InvestmentOption:
    """A single European investment opportunity.

    Attributes:
        ticker: Exchange-suffixed ticker symbol (e.g., "SAP.DE").
        name: Human-readable name.
        exchange: Exchange identifier (e.g., "XETRA").
        asset_class: AssetClass enum (stock/etf/bond_etf).
        sector: Business sector or ETF category.
        current_price: Latest price in original currency.
        currency: Original trading currency (e.g., "EUR", "GBP").
        benefit_score: Composite ranking score (0.0 to 1.0).
        in_portfolio: Whether the user already holds this ticker.
        is_delisted: Whether the ticker is suspended/delisted.
    """

    ticker: str
    name: str
    exchange: str
    asset_class: AssetClass
    sector: str
    current_price: float
    currency: str
    benefit_score: float = 0.0
    in_portfolio: bool = False
    is_delisted: bool = False
    pe_ratio: float | None = None


@dataclass(frozen=True)
class PerformanceDelta:
    """Performance change over a specific time period.

    Attributes:
        period: Time period label ("1Y", "3Y", "5Y").
        start_date: Start date of the period.
        end_date: End date of the period.
        start_price: Price at the start of the period.
        end_price: Price at the end of the period.
        absolute_change: End price minus start price.
        percentage_change: Percentage change from start to end.
        available: Whether full data is available for this period.
    """

    period: str
    start_date: datetime
    end_date: datetime
    start_price: float
    end_price: float
    absolute_change: float
    percentage_change: float
    available: bool = True


@dataclass(frozen=True)
class BondMarketContext:
    """European bond market overview for contextualizing bond ETFs.

    Attributes:
        treasury_2y: 2-year Eurozone government bond yield (%).
        treasury_5y: 5-year Eurozone government bond yield (%).
        treasury_10y: 10-year Eurozone government bond yield (%).
        treasury_30y: 30-year Eurozone government bond yield (%).
        yield_curve_signal: "normal", "inverted", or "flat".
        ecb_deposit_rate: Current ECB deposit facility rate (%).
        timestamp: When this data was fetched.
    """

    treasury_2y: float
    treasury_5y: float
    treasury_10y: float
    treasury_30y: float
    yield_curve_signal: str
    ecb_deposit_rate: float
    timestamp: datetime


@dataclass(frozen=True)
class ExchangeRate:
    """Currency conversion record.

    Attributes:
        source_currency: Original currency code (e.g., "GBP").
        target_currency: Target/base currency code (e.g., "EUR").
        rate: Conversion rate (1 source = rate * target).
        timestamp: When this rate was fetched.
    """

    source_currency: str
    target_currency: str
    rate: float
    timestamp: datetime


@dataclass
class BenefitScore:
    """Composite ranking metric for an investment option.

    Combines momentum, historical return, and volume into a
    single score normalized to 0.0-1.0.

    Attributes:
        momentum: Normalized 1-year momentum score (0.0-1.0).
        return_5y: Normalized 5-year return score (0.0-1.0).
        volume: Normalized trading volume score (0.0-1.0).
        composite_score: Weighted composite (0.0-1.0).
        component_breakdown: Human-readable breakdown string.
    """

    momentum: float = 0.0
    return_5y: float = 0.0
    volume: float = 0.0
    composite_score: float = 0.0
    component_breakdown: str = ""

    def __post_init__(self) -> None:
        """Calculate composite score from components."""
        # Default weights: momentum 40%, return 40%, volume 20%
        self.composite_score = round(
            (self.momentum * 0.4) + (self.return_5y * 0.4) + (self.volume * 0.2),
            4,
        )
        self.component_breakdown = (
            f"Momentum: {self.momentum:.0%} | "
            f"5Y Return: {self.return_5y:.0%} | "
            f"Volume: {self.volume:.0%}"
        )
