"""Curated ETF universe for the Bogleheads four-fund portfolio.

Organizes European-domiciled UCITS ETFs into the four Bogleheads
portfolio slots: domestic (EU) stocks, developed world, emerging
markets, and bonds (domestic + international).

Each entry includes metadata for categorization, fund family,
replication method, distribution policy, and a curated TER (Total
Expense Ratio) — enabling TER, AUM, and return comparisons within
each category.

Categories:
    - EU_STOCKS: Broad European equity indices (domestic for a EU investor)
    - DEVELOPED_WORLD: Global / non-EU developed market indices
    - EMERGING_MARKETS: Emerging market equity indices
    - BONDS_DOMESTIC: EUR-denominated government / corporate bonds
    - BONDS_INTERNATIONAL: Global aggregate bonds (EUR-hedged)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FundCategory(StrEnum):
    """Bogleheads four-fund portfolio slot."""

    EU_STOCKS = "eu_stocks"
    DEVELOPED_WORLD = "developed_world"
    EMERGING_MARKETS = "emerging_markets"
    BONDS_DOMESTIC = "bonds_domestic"
    BONDS_INTERNATIONAL = "bonds_international"


@dataclass(frozen=True)
class FundEntry:
    """A single curated ETF entry with static metadata.

    Attributes:
        ticker: Exchange-suffixed ticker symbol (e.g., "EUNL.DE").
        name: Human-readable ETF name.
        exchange: Exchange identifier (e.g., "XETRA", "LSE").
        category: FundCategory slot in the four-fund portfolio.
        fund_family: Issuer / fund family (e.g., "iShares", "Vanguard").
        ter: Total Expense Ratio as a percentage (e.g., 0.12 means 0.12%).
        replication: "Physical" or "Synthetic".
        distribution: "Accumulating" or "Distributing".
    """

    ticker: str
    name: str
    exchange: str
    category: FundCategory
    fund_family: str
    ter: float
    replication: str
    distribution: str


# --- Domestic (EU) Stocks — broad European equity indices ---

EU_STOCKS: list[FundEntry] = [
    FundEntry(
        "EUNL.DE", "iShares Core MSCI Europe", "XETRA",
        FundCategory.EU_STOCKS, "iShares", 0.12, "Physical", "Accumulating",
    ),
    FundEntry(
        "VEUR.AS", "Vanguard FTSE Developed Europe", "Euronext",
        FundCategory.EU_STOCKS, "Vanguard", 0.12, "Physical", "Distributing",
    ),
    FundEntry(
        "EXSA.DE", "iShares Core MSCI EM", "XETRA",
        FundCategory.EU_STOCKS, "iShares", 0.18, "Physical", "Distributing",
    ),
    FundEntry(
        "WEBN.DE", "Amundi MSCI Europe", "XETRA",
        FundCategory.EU_STOCKS, "Amundi", 0.25, "Synthetic", "Distributing",
    ),
    FundEntry(
        "EXHA.DE", "iShares Core MSCI Europe Health Care", "XETRA",
        FundCategory.EU_STOCKS, "iShares", 0.18, "Physical", "Distributing",
    ),
]

# --- Developed World — global / non-EU developed markets ---

DEVELOPED_WORLD: list[FundEntry] = [
    FundEntry(
        "IWDA.AS", "iShares Core MSCI World", "Euronext",
        FundCategory.DEVELOPED_WORLD, "iShares", 0.20, "Physical", "Accumulating",
    ),
    FundEntry(
        "SWDA.L", "iShares Core MSCI World", "LSE",
        FundCategory.DEVELOPED_WORLD, "iShares", 0.20, "Physical", "Accumulating",
    ),
    FundEntry(
        "VWRL.L", "Vanguard FTSE All-World", "LSE",
        FundCategory.DEVELOPED_WORLD, "Vanguard", 0.22, "Physical", "Distributing",
    ),
    FundEntry(
        "VWCE.DE", "Vanguard FTSE All-World UCITS", "XETRA",
        FundCategory.DEVELOPED_WORLD, "Vanguard", 0.22, "Physical", "Accumulating",
    ),
    FundEntry(
        "SXRV.DE", "Lyxor Core MSCI World (DR)", "XETRA",
        FundCategory.DEVELOPED_WORLD, "Lyxor", 0.25, "Synthetic", "Accumulating",
    ),
]

# --- Emerging Markets ---

EMERGING_MARKETS: list[FundEntry] = [
    FundEntry(
        "EMIM.L", "iShares Core MSCI EM IMI", "LSE",
        FundCategory.EMERGING_MARKETS, "iShares", 0.18, "Physical", "Accumulating",
    ),
    FundEntry(
        "EUNM.DE", "iShares Core MSCI EM IMI", "XETRA",
        FundCategory.EMERGING_MARKETS, "iShares", 0.18, "Physical", "Accumulating",
    ),
    FundEntry(
        "VFEM.L", "Vanguard FTSE Emerging Markets", "LSE",
        FundCategory.EMERGING_MARKETS, "Vanguard", 0.22, "Physical", "Distributing",
    ),
    FundEntry(
        "EMIM.DE", "iShares Core MSCI EM IMI", "XETRA",
        FundCategory.EMERGING_MARKETS, "iShares", 0.18, "Physical", "Accumulating",
    ),
]

# --- Bonds (Domestic — EUR-denominated) ---

BONDS_DOMESTIC: list[FundEntry] = [
    FundEntry(
        "IEGA.AS", "iShares Euro Govt Bond 7-10yr", "Euronext",
        FundCategory.BONDS_DOMESTIC, "iShares", 0.07, "Physical", "Distributing",
    ),
    FundEntry(
        "IBTS.AS", "iShares Euro Govt Bond 1-3yr", "Euronext",
        FundCategory.BONDS_DOMESTIC, "iShares", 0.09, "Physical", "Distributing",
    ),
    FundEntry(
        "IEAC.AS", "iShares Euro Corp Bond", "Euronext",
        FundCategory.BONDS_DOMESTIC, "iShares", 0.20, "Physical", "Distributing",
    ),
    FundEntry(
        "EXHB.DE", "iShares EUR High Yield Corp Bond", "XETRA",
        FundCategory.BONDS_DOMESTIC, "iShares", 0.35, "Physical", "Distributing",
    ),
    FundEntry(
        "EXX1.DE", "iShares EUR Inflation Linked Bond", "XETRA",
        FundCategory.BONDS_DOMESTIC, "iShares", 0.25, "Physical", "Distributing",
    ),
]

# --- Bonds (International — global, EUR-hedged) ---

BONDS_INTERNATIONAL: list[FundEntry] = [
    FundEntry(
        "AGGH.L", "iShares Global Aggregate Bond EUR Hedged", "LSE",
        FundCategory.BONDS_INTERNATIONAL, "iShares", 0.10, "Physical", "Distributing",
    ),
    FundEntry(
        "VAGF.L", "Vanguard Global Aggregate Bond EUR Hedged", "LSE",
        FundCategory.BONDS_INTERNATIONAL, "Vanguard", 0.12, "Physical", "Distributing",
    ),
    FundEntry(
        "XEON.DE", "Xtrackers EUR Overnight Rate", "XETRA",
        FundCategory.BONDS_INTERNATIONAL, "Xtrackers", 0.15, "Synthetic", "Accumulating",
    ),
    FundEntry(
        "IBGS.L", "iShares EUR Govt Bond 3-5yr", "LSE",
        FundCategory.BONDS_INTERNATIONAL, "iShares", 0.07, "Physical", "Distributing",
    ),
]


def get_all_funds() -> list[FundEntry]:
    """Return all curated four-fund ETF entries.

    Returns:
        Combined list of all FundEntry objects across all categories.
    """
    return (
        EU_STOCKS
        + DEVELOPED_WORLD
        + EMERGING_MARKETS
        + BONDS_DOMESTIC
        + BONDS_INTERNATIONAL
    )


def get_funds_by_category(category: FundCategory) -> list[FundEntry]:
    """Return fund entries filtered by category.

    Args:
        category: The FundCategory to filter by.

    Returns:
        List of FundEntry matching the category.
    """
    return [f for f in get_all_funds() if f.category == category]
