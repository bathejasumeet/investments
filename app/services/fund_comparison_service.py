"""Fund comparison service — compares ETFs for the four-fund portfolio.

Loads the curated four-fund ETF universe, fetches extended fund
metadata (TER, AUM, returns) from the market data provider, and
provides ranking, best-in-class selection, and portfolio TER
calculation capabilities.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from app.data.four_fund_universe import FundCategory, FundEntry, get_all_funds
from app.models.fund_profile import FundProfile, PortfolioSelection
from app.providers.base import MarketDataProvider


class FundComparisonService:
    """Service for comparing and ranking ETFs in the four-fund universe."""

    def __init__(self, provider: MarketDataProvider) -> None:
        self._provider = provider
        self._cache: dict[str, FundProfile] = {}
        self._last_fetch_time: datetime | None = None

    def load_universe(self) -> list[FundEntry]:
        """Load the curated four-fund ETF universe.

        Returns:
            List of all FundEntry objects across all categories.
        """
        return get_all_funds()

    def fetch_all_profiles(self) -> list[FundProfile]:
        """Fetch extended fund metadata for all ETFs in the universe.

        Uses ThreadPoolExecutor to parallelize HTTP requests to the
        market data provider, significantly reducing total fetch time
        (e.g., 23 sequential requests at ~2s each = ~46s sequential
        vs ~5-8s with 8 parallel workers).

        Returns:
            List of FundProfile with TER, AUM, and returns data.
            Funds that fail to fetch are included with is_available=False.
        """
        entries = self.load_universe()

        # Separate cached from uncached entries
        to_fetch: list[FundEntry] = []
        profiles: list[FundProfile] = []

        for entry in entries:
            cached = self._cache.get(entry.ticker)
            if cached is not None:
                profiles.append(cached)
            else:
                to_fetch.append(entry)

        # Fetch uncached entries in parallel
        if to_fetch:
            fetched = self._fetch_profiles_parallel(to_fetch)
            for entry in to_fetch:
                profile = fetched.get(entry.ticker)
                if profile is not None:
                    self._cache[entry.ticker] = profile
                    profiles.append(profile)
                else:
                    # Create an unavailable profile placeholder
                    unavailable = FundProfile(
                        ticker=entry.ticker,
                        name=entry.name,
                        category=entry.category,
                        fund_family=entry.fund_family,
                        ter=entry.ter,
                        aum=0.0,
                        inception_date=None,
                        replication=entry.replication,
                        distribution=entry.distribution,
                        return_1y=None,
                        return_3y=None,
                        return_5y=None,
                        currency="EUR",
                        current_price=0.0,
                        is_available=False,
                    )
                    profiles.append(unavailable)

        self._last_fetch_time = datetime.utcnow()
        return profiles

    def _fetch_profiles_parallel(
        self, entries: list[FundEntry]
    ) -> dict[str, FundProfile]:
        """Fetch fund profiles in parallel using ThreadPoolExecutor.

        Args:
            entries: List of FundEntry to fetch.

        Returns:
            Dictionary mapping ticker to FundProfile for successful fetches.
        """
        results: dict[str, FundProfile] = {}

        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_ticker = {
                executor.submit(self._provider.get_fund_info, entry.ticker): entry.ticker
                for entry in entries
            }

            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    profile = future.result()
                    if profile is not None:
                        results[ticker] = profile
                except Exception:
                    # Individual fetch failures are handled by the caller
                    pass

        return results

    def get_by_category(
        self, profiles: list[FundProfile], category: FundCategory
    ) -> list[FundProfile]:
        """Filter fund profiles by category.

        Args:
            profiles: List of FundProfile to filter.
            category: FundCategory to filter by.

        Returns:
            Filtered list of FundProfile.
        """
        return [p for p in profiles if p.category == category]

    def rank_by_ter(self, profiles: list[FundProfile]) -> list[FundProfile]:
        """Rank funds by Total Expense Ratio (lowest first).

        Only includes funds with is_available=True.

        Args:
            profiles: List of FundProfile to rank.

        Returns:
            Sorted list (ascending TER).
        """
        available = [p for p in profiles if p.is_available]
        return sorted(available, key=lambda p: p.ter)

    def rank_by_return(
        self, profiles: list[FundProfile], period: str = "3y"
    ) -> list[FundProfile]:
        """Rank funds by return for a given period (highest first).

        Args:
            profiles: List of FundProfile to rank.
            period: "1y", "3y", or "5y".

        Returns:
            Sorted list (descending return). Funds with no return data
            are placed at the end.
        """
        available = [p for p in profiles if p.is_available]

        def get_return(p: FundProfile) -> float:
            if period == "1y":
                return p.return_1y if p.return_1y is not None else float("-inf")
            elif period == "3y":
                return p.return_3y if p.return_3y is not None else float("-inf")
            elif period == "5y":
                return p.return_5y if p.return_5y is not None else float("-inf")
            return float("-inf")

        return sorted(available, key=get_return, reverse=True)

    def rank_by_aum(self, profiles: list[FundProfile]) -> list[FundProfile]:
        """Rank funds by Assets Under Management (largest first).

        Args:
            profiles: List of FundProfile to rank.

        Returns:
            Sorted list (descending AUM).
        """
        available = [p for p in profiles if p.is_available]
        return sorted(available, key=lambda p: p.aum, reverse=True)

    def best_in_class(
        self, profiles: list[FundProfile]
    ) -> dict[FundCategory, FundProfile]:
        """Select the best fund in each category (lowest TER).

        Ties are broken by larger AUM (more established fund).

        Args:
            profiles: List of FundProfile across all categories.

        Returns:
            Dictionary mapping each FundCategory to its best FundProfile.
            Categories with no available funds are omitted.
        """
        result: dict[FundCategory, FundProfile] = {}

        for category in FundCategory:
            category_profiles = self.get_by_category(profiles, category)
            available = [p for p in category_profiles if p.is_available]
            if not available:
                continue
            # Sort by TER ascending, then AUM descending (tie-breaker)
            sorted_profiles = sorted(
                available, key=lambda p: (p.ter, -p.aum)
            )
            result[category] = sorted_profiles[0]

        return result

    def calculate_portfolio_ter(
        self, selection: PortfolioSelection
    ) -> float:
        """Calculate the weighted average TER for a portfolio selection.

        Args:
            selection: PortfolioSelection with funds and weights.

        Returns:
            Weighted average TER as a percentage (e.g., 0.15 = 0.15%).
            Returns 0.0 if no funds are selected.
        """
        total_weight = 0.0
        weighted_ter = 0.0

        fund_weight_pairs = [
            (selection.eu_stocks, selection.eu_stocks_weight),
            (selection.developed_world, selection.developed_world_weight),
            (selection.emerging_markets, selection.emerging_markets_weight),
            (selection.bonds, selection.bonds_weight),
        ]

        for fund, weight in fund_weight_pairs:
            if fund is not None and fund.is_available and weight > 0:
                weighted_ter += fund.ter * weight
                total_weight += weight

        if total_weight == 0:
            return 0.0

        return round(weighted_ter / total_weight, 4)

    def calculate_portfolio_aum(
        self, selection: PortfolioSelection
    ) -> float:
        """Calculate the combined AUM for a portfolio selection.

        Args:
            selection: PortfolioSelection with funds.

        Returns:
            Sum of AUM across all selected funds (in EUR).
        """
        total = 0.0
        for fund in [
            selection.eu_stocks,
            selection.developed_world,
            selection.emerging_markets,
            selection.bonds,
        ]:
            if fund is not None and fund.is_available:
                total += fund.aum
        return total

    def compare_two_funds(
        self, fund_a: FundProfile, fund_b: FundProfile
    ) -> dict[str, object]:
        """Compare two funds head-to-head across key metrics.

        Args:
            fund_a: First FundProfile.
            fund_b: Second FundProfile.

        Returns:
            Dictionary with comparison results and winner per metric.
        """
        ter_winner = "a" if fund_a.ter < fund_b.ter else ("b" if fund_b.ter < fund_a.ter else "tie")
        aum_winner = "a" if fund_a.aum > fund_b.aum else ("b" if fund_b.aum > fund_a.aum else "tie")

        return_3y_a = fund_a.return_3y if fund_a.return_3y is not None else float("-inf")
        return_3y_b = fund_b.return_3y if fund_b.return_3y is not None else float("-inf")
        return_winner = "a" if return_3y_a > return_3y_b else ("b" if return_3y_b > return_3y_a else "tie")

        return {
            "fund_a": fund_a,
            "fund_b": fund_b,
            "ter": {"a": fund_a.ter, "b": fund_b.ter, "winner": ter_winner},
            "aum": {"a": fund_a.aum, "b": fund_b.aum, "winner": aum_winner},
            "return_3y": {
                "a": fund_a.return_3y,
                "b": fund_b.return_3y,
                "winner": return_winner,
            },
            "overall_winner": self._determine_overall_winner(
                ter_winner, aum_winner, return_winner
            ),
        }

    def get_last_fetch_time(self) -> datetime | None:
        """Return the timestamp of the last successful fetch.

        Returns:
            Datetime of last fetch, or None if never fetched.
        """
        return self._last_fetch_time

    @staticmethod
    def _determine_overall_winner(
        ter: str, aum: str, ret: str
    ) -> str:
        """Determine the overall winner from individual metric winners.

        Bogleheads priority: TER (costs matter most) > AUM (fund stability)
        > returns (past performance doesn't guarantee future).

        Args:
            ter: TER winner ("a", "b", or "tie").
            aum: AUM winner.
            ret: Return winner.

        Returns:
            "a", "b", or "tie".
        """
        if ter != "tie":
            return ter
        if aum != "tie":
            return aum
        return ret
