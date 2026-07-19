"""Unit tests for the FundComparisonService.

Tests cover:
- Loading the curated four-fund universe
- Fetching fund profiles with mock provider
- Category filtering
- TER ranking (ascending)
- Return ranking (descending)
- AUM ranking (descending)
- Best-in-class selection (lowest TER, AUM tie-breaker)
- Portfolio TER calculation (weighted average)
- Portfolio AUM calculation
- Head-to-head fund comparison
- Handling of unavailable funds
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.data.four_fund_universe import FundCategory, get_all_funds
from app.models.fund_profile import FundProfile, PortfolioSelection
from app.providers.base import MarketDataProvider
from app.services.fund_comparison_service import FundComparisonService

# --- Test Fixtures ---

def _make_profile(
    ticker: str,
    category: FundCategory,
    ter: float = 0.20,
    aum: float = 1_000_000_000,
    return_1y: float | None = 5.0,
    return_3y: float | None = 8.0,
    return_5y: float | None = 12.0,
    is_available: bool = True,
) -> FundProfile:
    """Create a FundProfile with sensible defaults for testing."""
    return FundProfile(
        ticker=ticker,
        name=f"Test Fund {ticker}",
        category=category,
        fund_family="iShares",
        ter=ter,
        aum=aum,
        inception_date=datetime(2010, 1, 1),
        replication="Physical",
        distribution="Accumulating",
        return_1y=return_1y,
        return_3y=return_3y,
        return_5y=return_5y,
        currency="EUR",
        current_price=100.0,
        is_available=is_available,
    )


@pytest.fixture
def sample_profiles() -> list[FundProfile]:
    """Return a set of sample FundProfiles across all categories."""
    return [
        # EU Stocks
        _make_profile("EUNL.DE", FundCategory.EU_STOCKS, ter=0.12, aum=12_000_000_000, return_3y=8.2),
        _make_profile("VEUR.AS", FundCategory.EU_STOCKS, ter=0.12, aum=8_000_000_000, return_3y=7.9),
        _make_profile("EXSA.DE", FundCategory.EU_STOCKS, ter=0.20, aum=5_000_000_000, return_3y=7.5),
        # Developed World
        _make_profile("IWDA.AS", FundCategory.DEVELOPED_WORLD, ter=0.20, aum=15_000_000_000, return_3y=10.1),
        _make_profile("SWDA.L", FundCategory.DEVELOPED_WORLD, ter=0.20, aum=10_000_000_000, return_3y=9.8),
        _make_profile("VWCE.DE", FundCategory.DEVELOPED_WORLD, ter=0.22, aum=20_000_000_000, return_3y=9.5),
        # Emerging Markets
        _make_profile("EMIM.L", FundCategory.EMERGING_MARKETS, ter=0.18, aum=6_000_000_000, return_3y=5.2),
        _make_profile("VFEM.L", FundCategory.EMERGING_MARKETS, ter=0.22, aum=4_000_000_000, return_3y=4.8),
        # Bonds Domestic
        _make_profile("IEGA.AS", FundCategory.BONDS_DOMESTIC, ter=0.07, aum=3_000_000_000, return_3y=1.2),
        _make_profile("IBTS.AS", FundCategory.BONDS_DOMESTIC, ter=0.09, aum=2_000_000_000, return_3y=0.8),
        # Bonds International
        _make_profile("AGGH.L", FundCategory.BONDS_INTERNATIONAL, ter=0.10, aum=5_000_000_000, return_3y=1.5),
        _make_profile("VAGF.L", FundCategory.BONDS_INTERNATIONAL, ter=0.12, aum=3_500_000_000, return_3y=1.3),
    ]


@pytest.fixture
def mock_fund_provider(sample_profiles) -> MarketDataProvider:
    """Return a mock provider that returns sample fund profiles."""
    provider = MagicMock(spec=MarketDataProvider)
    profile_map = {p.ticker: p for p in sample_profiles}

    def get_fund_info(ticker: str) -> FundProfile | None:
        return profile_map.get(ticker)

    provider.get_fund_info.side_effect = get_fund_info
    return provider


# --- Tests: Universe Loading ---


class TestLoadUniverse:
    """Tests for loading the curated four-fund universe."""

    def test_load_universe_returns_all_entries(self, mock_fund_provider):
        """Universe should return all curated fund entries."""
        service = FundComparisonService(mock_fund_provider)
        entries = service.load_universe()

        assert len(entries) > 0
        assert len(entries) == len(get_all_funds())

    def test_load_universe_has_all_categories(self, mock_fund_provider):
        """Universe should include funds from all five categories."""
        service = FundComparisonService(mock_fund_provider)
        entries = service.load_universe()

        categories = {e.category for e in entries}
        assert FundCategory.EU_STOCKS in categories
        assert FundCategory.DEVELOPED_WORLD in categories
        assert FundCategory.EMERGING_MARKETS in categories
        assert FundCategory.BONDS_DOMESTIC in categories
        assert FundCategory.BONDS_INTERNATIONAL in categories


# --- Tests: Fetching Profiles ---


class TestFetchAllProfiles:
    """Tests for fetching fund profiles from the provider."""

    def test_fetch_all_profiles_returns_profiles(self, mock_fund_provider):
        """Should return a FundProfile for each universe entry."""
        service = FundComparisonService(mock_fund_provider)
        profiles = service.fetch_all_profiles()

        assert len(profiles) == len(get_all_funds())
        assert all(isinstance(p, FundProfile) for p in profiles)

    def test_fetch_all_profiles_sets_fetch_time(self, mock_fund_provider):
        """Should set the last fetch time after fetching."""
        service = FundComparisonService(mock_fund_provider)
        assert service.get_last_fetch_time() is None

        service.fetch_all_profiles()

        assert service.get_last_fetch_time() is not None

    def test_fetch_all_profiles_handles_provider_failure(self):
        """Should create unavailable profiles when provider returns None."""
        provider = MagicMock(spec=MarketDataProvider)
        provider.get_fund_info.return_value = None

        service = FundComparisonService(provider)
        profiles = service.fetch_all_profiles()

        assert len(profiles) == len(get_all_funds())
        assert all(not p.is_available for p in profiles)
        # Unavailable profiles use curated TER from FundEntry
        assert all(p.ter > 0.0 for p in profiles)


# --- Tests: Category Filtering ---


class TestGetByCategory:
    """Tests for filtering profiles by category."""

    def test_get_by_category_returns_only_matching(self, mock_fund_provider, sample_profiles):
        """Should return only profiles matching the given category."""
        service = FundComparisonService(mock_fund_provider)

        eu_stocks = service.get_by_category(sample_profiles, FundCategory.EU_STOCKS)

        assert len(eu_stocks) == 3
        assert all(p.category == FundCategory.EU_STOCKS for p in eu_stocks)

    def test_get_by_category_empty_for_no_match(self, mock_fund_provider, sample_profiles):
        """Should return empty list when no profiles match."""
        service = FundComparisonService(mock_fund_provider)

        # Create an empty list
        result = service.get_by_category([], FundCategory.EU_STOCKS)

        assert result == []


# --- Tests: TER Ranking ---


class TestRankByTer:
    """Tests for ranking funds by TER (ascending)."""

    def test_rank_by_ter_ascending(self, mock_fund_provider, sample_profiles):
        """Should sort funds by TER ascending (lowest first)."""
        service = FundComparisonService(mock_fund_provider)
        eu_stocks = service.get_by_category(sample_profiles, FundCategory.EU_STOCKS)

        ranked = service.rank_by_ter(eu_stocks)

        ters = [p.ter for p in ranked]
        assert ters == sorted(ters)
        assert ters[0] <= ters[-1]

    def test_rank_by_ter_excludes_unavailable(self, mock_fund_provider):
        """Should exclude funds with is_available=False."""
        profiles = [
            _make_profile("AAA.DE", FundCategory.EU_STOCKS, ter=0.15, is_available=True),
            _make_profile("BBB.DE", FundCategory.EU_STOCKS, ter=0.10, is_available=False),
        ]
        service = FundComparisonService(mock_fund_provider)

        ranked = service.rank_by_ter(profiles)

        assert len(ranked) == 1
        assert ranked[0].ticker == "AAA.DE"


# --- Tests: Return Ranking ---


class TestRankByReturn:
    """Tests for ranking funds by return (descending)."""

    def test_rank_by_return_3y_descending(self, mock_fund_provider, sample_profiles):
        """Should sort funds by 3Y return descending (highest first)."""
        service = FundComparisonService(mock_fund_provider)
        eu_stocks = service.get_by_category(sample_profiles, FundCategory.EU_STOCKS)

        ranked = service.rank_by_return(eu_stocks, "3y")

        returns = [p.return_3y for p in ranked]
        assert returns == sorted(returns, reverse=True)
        assert returns[0] >= returns[-1]

    def test_rank_by_return_1y(self, mock_fund_provider, sample_profiles):
        """Should sort by 1Y return when period='1y'."""
        service = FundComparisonService(mock_fund_provider)
        dev = service.get_by_category(sample_profiles, FundCategory.DEVELOPED_WORLD)

        ranked = service.rank_by_return(dev, "1y")

        returns = [p.return_1y for p in ranked]
        assert returns == sorted(returns, reverse=True)

    def test_rank_by_return_handles_none(self, mock_fund_provider):
        """Funds with None return should be placed at the end."""
        profiles = [
            _make_profile("AAA.DE", FundCategory.EU_STOCKS, return_3y=None),
            _make_profile("BBB.DE", FundCategory.EU_STOCKS, return_3y=5.0),
        ]
        service = FundComparisonService(mock_fund_provider)

        ranked = service.rank_by_return(profiles, "3y")

        assert ranked[0].ticker == "BBB.DE"
        assert ranked[1].ticker == "AAA.DE"


# --- Tests: AUM Ranking ---


class TestRankByAum:
    """Tests for ranking funds by AUM (descending)."""

    def test_rank_by_aum_descending(self, mock_fund_provider, sample_profiles):
        """Should sort funds by AUM descending (largest first)."""
        service = FundComparisonService(mock_fund_provider)
        dev = service.get_by_category(sample_profiles, FundCategory.DEVELOPED_WORLD)

        ranked = service.rank_by_aum(dev)

        aums = [p.aum for p in ranked]
        assert aums == sorted(aums, reverse=True)
        assert aums[0] >= aums[-1]


# --- Tests: Best in Class ---


class TestBestInClass:
    """Tests for best-in-class selection."""

    def test_best_in_class_returns_lowest_ter(self, mock_fund_provider, sample_profiles):
        """Best in class should be the fund with the lowest TER."""
        service = FundComparisonService(mock_fund_provider)

        best = service.best_in_class(sample_profiles)

        # EU Stocks: EUNL.DE and VEUR.AS both have 0.12, EUNL.DE has larger AUM
        assert FundCategory.EU_STOCKS in best
        assert best[FundCategory.EU_STOCKS].ter == 0.12
        # Tie-breaker: larger AUM wins
        assert best[FundCategory.EU_STOCKS].ticker == "EUNL.DE"

    def test_best_in_class_for_all_categories(self, mock_fund_provider, sample_profiles):
        """Should return a best fund for each category with available funds."""
        service = FundComparisonService(mock_fund_provider)

        best = service.best_in_class(sample_profiles)

        assert len(best) == 5  # All five categories

    def test_best_in_class_skips_empty_categories(self, mock_fund_provider):
        """Should omit categories with no available funds."""
        profiles = [
            _make_profile("AAA.DE", FundCategory.EU_STOCKS, ter=0.15),
        ]
        service = FundComparisonService(mock_fund_provider)

        best = service.best_in_class(profiles)

        assert FundCategory.EU_STOCKS in best
        assert FundCategory.DEVELOPED_WORLD not in best


# --- Tests: Portfolio TER Calculation ---


class TestCalculatePortfolioTer:
    """Tests for weighted average TER calculation."""

    def test_portfolio_ter_weighted_average(self, mock_fund_provider, sample_profiles):
        """Should calculate correct weighted average TER."""
        service = FundComparisonService(mock_fund_provider)

        eu = _make_profile("EUNL.DE", FundCategory.EU_STOCKS, ter=0.12)
        dev = _make_profile("IWDA.AS", FundCategory.DEVELOPED_WORLD, ter=0.20)
        em = _make_profile("EMIM.L", FundCategory.EMERGING_MARKETS, ter=0.18)
        bonds = _make_profile("AGGH.L", FundCategory.BONDS_INTERNATIONAL, ter=0.10)

        selection = PortfolioSelection(
            eu_stocks=eu,
            developed_world=dev,
            emerging_markets=em,
            bonds=bonds,
            eu_stocks_weight=0.30,
            developed_world_weight=0.30,
            emerging_markets_weight=0.10,
            bonds_weight=0.30,
        )

        ter = service.calculate_portfolio_ter(selection)

        # (0.12*0.30 + 0.20*0.30 + 0.18*0.10 + 0.10*0.30) / 1.0
        expected = (0.036 + 0.060 + 0.018 + 0.030) / 1.0
        assert ter == round(expected, 4)

    def test_portfolio_ter_zero_when_no_funds(self, mock_fund_provider):
        """Should return 0.0 when no funds are selected."""
        service = FundComparisonService(mock_fund_provider)

        selection = PortfolioSelection(
            eu_stocks=None,
            developed_world=None,
            emerging_markets=None,
            bonds=None,
        )

        assert service.calculate_portfolio_ter(selection) == 0.0

    def test_portfolio_ter_excludes_unavailable(self, mock_fund_provider):
        """Should exclude unavailable funds from the calculation."""
        service = FundComparisonService(mock_fund_provider)

        eu = _make_profile("EUNL.DE", FundCategory.EU_STOCKS, ter=0.12, is_available=False)
        dev = _make_profile("IWDA.AS", FundCategory.DEVELOPED_WORLD, ter=0.20)

        selection = PortfolioSelection(
            eu_stocks=eu,
            developed_world=dev,
            emerging_markets=None,
            bonds=None,
            eu_stocks_weight=0.50,
            developed_world_weight=0.50,
        )

        ter = service.calculate_portfolio_ter(selection)

        # Only dev fund counts: 0.20 * 0.50 / 0.50 = 0.20
        assert ter == 0.20


# --- Tests: Portfolio AUM Calculation ---


class TestCalculatePortfolioAum:
    """Tests for combined AUM calculation."""

    def test_portfolio_aum_sums_all_funds(self, mock_fund_provider):
        """Should sum AUM across all selected available funds."""
        service = FundComparisonService(mock_fund_provider)

        selection = PortfolioSelection(
            eu_stocks=_make_profile("A", FundCategory.EU_STOCKS, aum=1_000_000_000),
            developed_world=_make_profile("B", FundCategory.DEVELOPED_WORLD, aum=2_000_000_000),
            emerging_markets=_make_profile("C", FundCategory.EMERGING_MARKETS, aum=500_000_000),
            bonds=_make_profile("D", FundCategory.BONDS_DOMESTIC, aum=300_000_000),
        )

        aum = service.calculate_portfolio_aum(selection)

        assert aum == 3_800_000_000

    def test_portfolio_aum_excludes_unavailable(self, mock_fund_provider):
        """Should exclude unavailable funds from AUM sum."""
        service = FundComparisonService(mock_fund_provider)

        selection = PortfolioSelection(
            eu_stocks=_make_profile("A", FundCategory.EU_STOCKS, aum=1_000_000_000, is_available=False),
            developed_world=_make_profile("B", FundCategory.DEVELOPED_WORLD, aum=2_000_000_000),
            emerging_markets=None,
            bonds=None,
        )

        aum = service.calculate_portfolio_aum(selection)

        assert aum == 2_000_000_000


# --- Tests: Head-to-Head Comparison ---


class TestCompareTwoFunds:
    """Tests for head-to-head fund comparison."""

    def test_compare_fund_a_wins_on_ter(self, mock_fund_provider):
        """Fund with lower TER should win the TER metric."""
        service = FundComparisonService(mock_fund_provider)

        fund_a = _make_profile("A", FundCategory.EU_STOCKS, ter=0.12, aum=5_000_000_000, return_3y=8.0)
        fund_b = _make_profile("B", FundCategory.EU_STOCKS, ter=0.20, aum=10_000_000_000, return_3y=10.0)

        result = service.compare_two_funds(fund_a, fund_b)

        assert result["ter"]["winner"] == "a"
        assert result["aum"]["winner"] == "b"
        # TER takes priority in overall winner
        assert result["overall_winner"] == "a"

    def test_compare_tie_on_ter_aum_breaks(self, mock_fund_provider):
        """When TER is tied, AUM should determine the winner."""
        service = FundComparisonService(mock_fund_provider)

        fund_a = _make_profile("A", FundCategory.EU_STOCKS, ter=0.12, aum=10_000_000_000, return_3y=8.0)
        fund_b = _make_profile("B", FundCategory.EU_STOCKS, ter=0.12, aum=5_000_000_000, return_3y=10.0)

        result = service.compare_two_funds(fund_a, fund_b)

        assert result["ter"]["winner"] == "tie"
        assert result["aum"]["winner"] == "a"
        assert result["overall_winner"] == "a"

    def test_compare_all_tied(self, mock_fund_provider):
        """When all metrics are tied, overall winner should be 'tie'."""
        service = FundComparisonService(mock_fund_provider)

        fund_a = _make_profile("A", FundCategory.EU_STOCKS, ter=0.12, aum=5_000_000_000, return_3y=8.0)
        fund_b = _make_profile("B", FundCategory.EU_STOCKS, ter=0.12, aum=5_000_000_000, return_3y=8.0)

        result = service.compare_two_funds(fund_a, fund_b)

        assert result["ter"]["winner"] == "tie"
        assert result["aum"]["winner"] == "tie"
        assert result["return_3y"]["winner"] == "tie"
        assert result["overall_winner"] == "tie"
