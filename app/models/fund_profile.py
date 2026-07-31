"""Data models for the four-fund portfolio comparison feature.

Contains the FundProfile dataclass — extended fund metadata fetched
from the market data provider (TER, AUM, returns, inception date).
These are plain dataclasses (not ORM models) since fund profiles are
fetched live from market data, not persisted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.data.four_fund_universe import FundCategory


@dataclass(frozen=True)
class FundProfile:
    """Extended metadata for a single ETF in the four-fund universe.

    Attributes:
        ticker: Exchange-suffixed ticker symbol (e.g., "EUNL.DE").
        name: Human-readable ETF name.
        category: FundCategory slot in the four-fund portfolio.
        fund_family: Issuer / fund family (e.g., "iShares", "Vanguard").
        ter: Total Expense Ratio as a percentage (e.g., 0.12 means 0.12%).
        aum: Assets Under Management in EUR (raw number).
        inception_date: Fund inception date, or None if unavailable.
        replication: "Physical" or "Synthetic".
        distribution: "Accumulating" or "Distributing".
        return_1y: 1-year return as a percentage, or None.
        return_3y: 3-year annualized return as a percentage, or None.
        return_5y: 5-year annualized return as a percentage, or None.
        currency: Trading currency code (e.g., "EUR", "USD").
        current_price: Latest price in the trading currency.
        is_available: False if the data fetch failed for this ticker.
    """

    ticker: str
    name: str
    category: FundCategory
    fund_family: str
    ter: float
    aum: float
    inception_date: datetime | None
    replication: str
    distribution: str
    return_1y: float | None
    return_3y: float | None
    return_5y: float | None
    currency: str
    current_price: float
    pe_ratio: float | None = None
    is_available: bool = True


@dataclass(frozen=True)
class PortfolioSelection:
    """A user's selected four-fund portfolio with allocation weights.

    Attributes:
        eu_stocks: Selected FundProfile for the domestic (EU) stocks slot.
        developed_world: Selected FundProfile for the developed world slot.
        emerging_markets: Selected FundProfile for the emerging markets slot.
        bonds: Selected FundProfile for the bonds slot (domestic or international).
        eu_stocks_weight: Allocation weight for EU stocks (0.0 to 1.0).
        developed_world_weight: Allocation weight for developed world.
        emerging_markets_weight: Allocation weight for emerging markets.
        bonds_weight: Allocation weight for bonds.
    """

    eu_stocks: FundProfile | None
    developed_world: FundProfile | None
    emerging_markets: FundProfile | None
    bonds: FundProfile | None
    eu_stocks_weight: float = 0.25
    developed_world_weight: float = 0.25
    emerging_markets_weight: float = 0.25
    bonds_weight: float = 0.25
