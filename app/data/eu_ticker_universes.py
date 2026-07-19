"""Curated European investment option ticker universe.

Static lists of European stocks, ETFs, and bond ETFs across major
exchanges. Each entry includes metadata for categorization and display.

Exchanges covered:
    - XETRA (Germany): .DE suffix
    - Euronext Amsterdam: .AS suffix
    - Euronext Paris: .PA suffix
    - London Stock Exchange: .L suffix
    - Borsa Italiana (Milan): .MI suffix
    - SIX Swiss Exchange: .SW suffix
    - NASDAQ Stockholm: .ST suffix
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AssetClass(str, Enum):
    """Asset class enumeration for investment options."""

    STOCK = "stock"
    ETF = "etf"
    BOND_ETF = "bond_etf"


@dataclass(frozen=True)
class TickerEntry:
    """A single curated ticker entry with metadata.

    Attributes:
        ticker: Exchange-suffixed ticker symbol (e.g., "SAP.DE").
        name: Human-readable company/ETF name.
        exchange: Exchange identifier (e.g., "XETRA", "LSE").
        sector: Business sector (e.g., "Technology", "Healthcare").
        asset_class: AssetClass enum value.
    """

    ticker: str
    name: str
    exchange: str
    sector: str
    asset_class: AssetClass


# --- European Stocks (~25 across sectors and exchanges) ---

EU_STOCKS: list[TickerEntry] = [
    # Technology
    TickerEntry("SAP.DE", "SAP SE", "XETRA", "Technology", AssetClass.STOCK),
    TickerEntry("ASML.AS", "ASML Holding", "Euronext", "Technology", AssetClass.STOCK),
    TickerEntry("INF.L", "Infineon Technologies", "LSE", "Technology", AssetClass.STOCK),
    TickerEntry("CAP.PA", "Capgemini", "Euronext", "Technology", AssetClass.STOCK),
    # Healthcare
    TickerEntry("AZN.L", "AstraZeneca", "LSE", "Healthcare", AssetClass.STOCK),
    TickerEntry("NOVO-B.CO", "Novo Nordisk", "Copenhagen", "Healthcare", AssetClass.STOCK),
    TickerEntry("RHHBY", "Roche Holding (ADR)", "OTC", "Healthcare", AssetClass.STOCK),
    TickerEntry("NOVN.SW", "Novartis", "SIX", "Healthcare", AssetClass.STOCK),
    TickerEntry("SAN.PA", "Sanofi", "Euronext", "Healthcare", AssetClass.STOCK),
    # Consumer
    TickerEntry("MC.PA", "LVMH", "Euronext", "Consumer", AssetClass.STOCK),
    TickerEntry("OR.PA", "L'Oreal", "Euronext", "Consumer", AssetClass.STOCK),
    TickerEntry("NESN.SW", "Nestle", "SIX", "Consumer", AssetClass.STOCK),
    TickerEntry("BAS.DE", "BASF", "XETRA", "Consumer", AssetClass.STOCK),
    TickerEntry("ULVR.L", "Unilever", "LSE", "Consumer", AssetClass.STOCK),
    # Finance
    TickerEntry("INGA.AS", "ING Group", "Euronext", "Finance", AssetClass.STOCK),
    TickerEntry("ISP.MI", "Intesa Sanpaolo", "Milan", "Finance", AssetClass.STOCK),
    TickerEntry("BNP.PA", "BNP Paribas", "Euronext", "Finance", AssetClass.STOCK),
    TickerEntry("DBK.DE", "Deutsche Bank", "XETRA", "Finance", AssetClass.STOCK),
    TickerEntry("HSBA.L", "HSBC Holdings", "LSE", "Finance", AssetClass.STOCK),
    # Energy
    TickerEntry("SHEL.L", "Shell", "LSE", "Energy", AssetClass.STOCK),
    TickerEntry("ENI.MI", "Eni", "Milan", "Energy", AssetClass.STOCK),
    TickerEntry("REP.MC", "Repsol", "Madrid", "Energy", AssetClass.STOCK),
    TickerEntry("TTE.PA", "TotalEnergies", "Euronext", "Energy", AssetClass.STOCK),
    # Industrials
    TickerEntry("AIR.PA", "Airbus", "Euronext", "Industrials", AssetClass.STOCK),
    TickerEntry("SIE.DE", "Siemens", "XETRA", "Industrials", AssetClass.STOCK),
    TickerEntry("ALV.DE", "Allianz", "XETRA", "Finance", AssetClass.STOCK),
]

# --- European UCITS ETFs (~12) ---

EU_ETF: list[TickerEntry] = [
    TickerEntry("IWDA.AS", "iShares Core MSCI World", "Euronext", "Broad Market", AssetClass.ETF),
    TickerEntry("VUSA.L", "Vanguard S&P 500 UCITS", "LSE", "Broad Market", AssetClass.ETF),
    TickerEntry("EUNL.DE", "iShares Core MSCI Europe", "XETRA", "Broad Market", AssetClass.ETF),
    TickerEntry("EMIM.L", "iShares EM IMI", "LSE", "Emerging Markets", AssetClass.ETF),
    TickerEntry("EXSA.DE", "iShares Core MSCI EM", "XETRA", "Emerging Markets", AssetClass.ETF),
    TickerEntry("SXRV.DE", "Lyxor S&P 500", "XETRA", "Broad Market", AssetClass.ETF),
    TickerEntry("VGWL.DE", "Vanguard FTSE All-World", "XETRA", "Broad Market", AssetClass.ETF),
    TickerEntry("IUIT.L", "iShares S&P 500 Information Technology", "LSE", "Technology", AssetClass.ETF),
    TickerEntry("EXHA.DE", "iShares Core MSCI Europe Health Care", "XETRA", "Healthcare", AssetClass.ETF),
    TickerEntry("EUNY.DE", "iShares MSCI Europe Financials", "XETRA", "Finance", AssetClass.ETF),
    TickerEntry("LYPG.DE", "Lyxor MSCI World Energy", "XETRA", "Energy", AssetClass.ETF),
    TickerEntry("WEBN.DE", "Amundi MSCI Europe", "XETRA", "Broad Market", AssetClass.ETF),
]

# --- European Bond ETFs (~10) ---

EU_BOND_ETF: list[TickerEntry] = [
    TickerEntry("VETY.L", "Vanguard EUR Treasury Bond", "LSE", "Government", AssetClass.BOND_ETF),
    TickerEntry("IBTS.AS", "iShares Euro Govt Bond 1-3yr", "Euronext", "Government", AssetClass.BOND_ETF),
    TickerEntry("IEGA.AS", "iShares Euro Govt Bond 7-10yr", "Euronext", "Government", AssetClass.BOND_ETF),
    TickerEntry("IEAC.AS", "iShares Euro Corp Bond", "Euronext", "Corporate", AssetClass.BOND_ETF),
    TickerEntry("VAGF.L", "Vanguard Global Aggregate Bond EUR Hedged", "LSE", "Global Aggregate", AssetClass.BOND_ETF),
    TickerEntry("IBTA.L", "iShares EUR Govt Bond 1-5yr", "LSE", "Government", AssetClass.BOND_ETF),
    TickerEntry("EXHB.DE", "iShares EUR High Yield Corp Bond", "XETRA", "Corporate", AssetClass.BOND_ETF),
    TickerEntry("EXX1.DE", "iShares EUR Inflation Linked Bond", "XETRA", "Inflation-Linked", AssetClass.BOND_ETF),
    TickerEntry("XEON.DE", "Xtrackers EUR Overnight Rate", "XETRA", "Money Market", AssetClass.BOND_ETF),
    TickerEntry("IBGS.L", "iShares EUR Govt Bond 3-5yr", "LSE", "Government", AssetClass.BOND_ETF),
]


def get_all_entries() -> list[TickerEntry]:
    """Return all curated European ticker entries.

    Returns:
        Combined list of stocks, ETFs, and bond ETFs.
    """
    return EU_STOCKS + EU_ETF + EU_BOND_ETF


def get_entries_by_class(asset_class: AssetClass) -> list[TickerEntry]:
    """Return ticker entries filtered by asset class.

    Args:
        asset_class: The AssetClass to filter by.

    Returns:
        List of TickerEntry matching the asset class.
    """
    all_entries = get_all_entries()
    return [e for e in all_entries if e.asset_class == asset_class]