"""Unit tests for InvestmentOptionService.

Tests cover ticker universe loading, price fetching, categorization,
performance delta calculation, benefit score calculation, sorting,
and filtering of European investment options.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from unittest.mock import MagicMock

import pytest

from app.data.eu_ticker_universes import AssetClass, get_all_entries
from app.models.investment_option import (
    BenefitScore,
    InvestmentOption,
    PerformanceDelta,
)
from app.providers.base import MarketDataProvider, PriceHistory, PriceQuote
from app.services.investment_option_service import InvestmentOptionService


@pytest.fixture
def eu_price_quotes():
    """Return sample price quotes for EU tickers."""
    return {
        "SAP.DE": PriceQuote("SAP.DE", 180.50, "EUR", datetime.utcnow()),
        "ASML.AS": PriceQuote("ASML.AS", 650.00, "EUR", datetime.utcnow()),
        "IWDA.AS": PriceQuote("IWDA.AS", 75.20, "EUR", datetime.utcnow()),
        "VETY.L": PriceQuote("VETY.L", 25.50, "GBP", datetime.utcnow()),
    }


@pytest.fixture
def eu_price_history():
    """Return a 5-year price history for testing."""
    base_date = datetime(2021, 7, 11)
    dates = [base_date + timedelta(days=30 * i) for i in range(60)]  # ~5 years
    closes = [100.0 + i * 2.0 for i in range(60)]  # Rising from 100 to 218
    return PriceHistory(
        ticker="SAP.DE",
        dates=dates,
        opens=closes,
        highs=[c + 2 for c in closes],
        lows=[c - 2 for c in closes],
        closes=closes,
        volumes=[1000000 + i * 10000 for i in range(60)],
    )


@pytest.fixture
def mock_eu_provider(eu_price_quotes, eu_price_history):
    """Return a mock provider configured for EU market tests."""
    provider = MagicMock(spec=MarketDataProvider)
    provider.get_current_prices.return_value = eu_price_quotes
    provider.get_price_history_5y.return_value = eu_price_history
    provider.get_exchange_rate.return_value = None
    return provider


@pytest.fixture
def eu_service(mock_eu_provider):
    """Return an InvestmentOptionService with mock provider."""
    return InvestmentOptionService(mock_eu_provider)


class TestLoadTickerUniverse:
    """Tests for load_ticker_universe (T012)."""

    def test_load_returns_all_entries(self, eu_service):
        """Test that load_ticker_universe returns all curated entries."""
        entries = eu_service.load_ticker_universe()
        all_expected = get_all_entries()
        assert len(entries) == len(all_expected)

    def test_entries_have_required_fields(self, eu_service):
        """Test that each entry has ticker, name, exchange, sector, asset_class."""
        entries = eu_service.load_ticker_universe()
        for entry in entries:
            assert entry.ticker is not None and len(entry.ticker) > 0
            assert entry.name is not None and len(entry.name) > 0
            assert entry.exchange is not None
            assert entry.sector is not None
            assert entry.asset_class in AssetClass

    def test_correct_counts_per_category(self, eu_service):
        """Test that each category has the expected number of entries."""
        entries = eu_service.load_ticker_universe()
        stocks = [e for e in entries if e.asset_class == AssetClass.STOCK]
        etfs = [e for e in entries if e.asset_class == AssetClass.ETF]
        bonds = [e for e in entries if e.asset_class == AssetClass.BOND_ETF]

        assert len(stocks) >= 20, f"Expected >=20 stocks, got {len(stocks)}"
        assert len(etfs) >= 10, f"Expected >=10 ETFs, got {len(etfs)}"
        assert len(bonds) >= 8, f"Expected >=8 bond ETFs, got {len(bonds)}"


class TestFetchAllOptions:
    """Tests for fetch_all_options (T013)."""

    def test_fetch_returns_options_with_prices(self, eu_service, eu_price_quotes):
        """Test that fetch_all_options returns options with current prices."""
        options = eu_service.fetch_all_options()
        assert len(options) > 0

        for option in options:
            assert option.current_price > 0
            assert option.currency in ("EUR", "GBP", "USD", "CHF", "SEK")

    def test_fetch_handles_provider_failures(self, mock_eu_provider):
        """Test that fetch_all_options handles provider failures gracefully."""
        mock_eu_provider.get_current_prices.return_value = {}
        service = InvestmentOptionService(mock_eu_provider)
        options = service.fetch_all_options()
        assert options == []

    def test_fetch_marks_portfolio_overlap(self, eu_service):
        """Test that options already in portfolio are marked."""
        options = eu_service.fetch_all_options(
            portfolio_tickers=["SAP.DE", "ASML.AS"]
        )
        sap = next(o for o in options if o.ticker == "SAP.DE")
        asml = next(o for o in options if o.ticker == "ASML.AS")
        assert sap.in_portfolio is True
        assert asml.in_portfolio is True


class TestGetOptionsByCategory:
    """Tests for get_options_by_category (T014)."""

    def test_filter_by_stock_class(self, eu_service):
        """Test filtering by STOCK asset class."""
        options = eu_service.fetch_all_options()
        stocks = eu_service.get_options_by_category(options, AssetClass.STOCK)
        assert len(stocks) > 0
        for s in stocks:
            assert s.asset_class == AssetClass.STOCK

    def test_filter_by_etf_class(self, eu_service):
        """Test filtering by ETF asset class."""
        options = eu_service.fetch_all_options()
        etfs = eu_service.get_options_by_category(options, AssetClass.ETF)
        assert len(etfs) > 0
        for e in etfs:
            assert e.asset_class == AssetClass.ETF

    def test_filter_by_bond_etf_class(self, eu_service):
        """Test filtering by BOND_ETF asset class."""
        options = eu_service.fetch_all_options()
        bonds = eu_service.get_options_by_category(options, AssetClass.BOND_ETF)
        assert len(bonds) > 0
        for b in bonds:
            assert b.asset_class == AssetClass.BOND_ETF


class TestCalculatePerformanceDeltas:
    """Tests for calculate_performance_deltas (T020, T021)."""

    def test_returns_deltas_for_all_periods(self, eu_service):
        """Test that deltas are returned for 1Y, 3Y, and 5Y."""
        deltas = eu_service.calculate_performance_deltas("SAP.DE")
        periods = {d.period for d in deltas}
        assert "1Y" in periods
        assert "3Y" in periods
        assert "5Y" in periods

    def test_delta_calculation_correctness(self, eu_service, eu_price_history):
        """Test that delta values are calculated correctly."""
        deltas = eu_service.calculate_performance_deltas("SAP.DE")
        five_y = next(d for d in deltas if d.period == "5Y")
        assert five_y.start_price > 0
        assert five_y.end_price > 0
        expected_pct = ((five_y.end_price - five_y.start_price) / five_y.start_price) * 100
        assert abs(five_y.percentage_change - round(expected_pct, 2)) < 0.1

    def test_handles_no_history(self, mock_eu_provider):
        """Test that empty history returns empty deltas."""
        mock_eu_provider.get_price_history_5y.return_value = None
        service = InvestmentOptionService(mock_eu_provider)
        deltas = service.calculate_performance_deltas("INVALID.TICKER")
        assert deltas == []

    def test_partial_data_marks_unavailable(self, mock_eu_provider):
        """Test that partial data marks longer periods as unavailable."""
        # Only 6 months of data
        base_date = datetime(2026, 1, 11)
        dates = [base_date + timedelta(days=30 * i) for i in range(6)]
        closes = [100.0 + i for i in range(6)]
        mock_eu_provider.get_price_history_5y.return_value = PriceHistory(
            ticker="NEW.ETF",
            dates=dates,
            opens=closes,
            highs=closes,
            lows=closes,
            closes=closes,
            volumes=[100000] * 6,
        )
        service = InvestmentOptionService(mock_eu_provider)
        deltas = service.calculate_performance_deltas("NEW.ETF")
        five_y = next((d for d in deltas if d.period == "5Y"), None)
        if five_y:
            assert five_y.available is False


class TestCalculateBenefitScore:
    """Tests for calculate_benefit_score (T028)."""

    def test_score_in_valid_range(self, eu_service):
        """Test that composite score is between 0.0 and 1.0."""
        score = eu_service.calculate_benefit_score("SAP.DE")
        assert 0.0 <= score.composite_score <= 1.0

    def test_score_is_deterministic(self, eu_service):
        """Test that identical inputs produce identical scores."""
        score1 = eu_service.calculate_benefit_score("SAP.DE")
        score2 = eu_service.calculate_benefit_score("SAP.DE")
        assert score1.composite_score == score2.composite_score

    def test_component_breakdown_exists(self, eu_service):
        """Test that component breakdown string is populated."""
        score = eu_service.calculate_benefit_score("SAP.DE")
        assert "Momentum" in score.component_breakdown
        assert "5Y Return" in score.component_breakdown
        assert "Volume" in score.component_breakdown

    def test_weights_sum_correctly(self):
        """Test that default weights produce correct composite."""
        score = BenefitScore(momentum=1.0, return_5y=1.0, volume=1.0)
        # 1.0*0.4 + 1.0*0.4 + 1.0*0.2 = 1.0
        assert abs(score.composite_score - 1.0) < 0.001

    def test_zero_scores_produce_zero_composite(self):
        """Test that all-zero components produce zero composite."""
        score = BenefitScore(momentum=0.0, return_5y=0.0, volume=0.0)
        assert score.composite_score == 0.0


class TestSortOptions:
    """Tests for sort_options (T029)."""

    def test_default_sort_by_benefit_score(self, eu_service):
        """Test that default sort is by benefit score descending."""
        options = [
            InvestmentOption(
                ticker="A", name="A", exchange="XETRA",
                asset_class=AssetClass.STOCK, sector="Tech",
                current_price=100.0, currency="EUR", benefit_score=0.5,
            ),
            InvestmentOption(
                ticker="B", name="B", exchange="XETRA",
                asset_class=AssetClass.STOCK, sector="Tech",
                current_price=100.0, currency="EUR", benefit_score=0.9,
            ),
            InvestmentOption(
                ticker="C", name="C", exchange="XETRA",
                asset_class=AssetClass.STOCK, sector="Tech",
                current_price=100.0, currency="EUR", benefit_score=0.3,
            ),
        ]
        sorted_opts = eu_service.sort_options(options)
        assert sorted_opts[0].benefit_score == 0.9
        assert sorted_opts[1].benefit_score == 0.5
        assert sorted_opts[2].benefit_score == 0.3


class TestFilterOptions:
    """Tests for filter_options (T039, T040)."""

    @pytest.fixture
    def sample_options(self):
        """Return sample options for filtering tests."""
        return [
            InvestmentOption(
                ticker="SAP.DE", name="SAP SE", exchange="XETRA",
                asset_class=AssetClass.STOCK, sector="Technology",
                current_price=180.0, currency="EUR",
            ),
            InvestmentOption(
                ticker="ASML.AS", name="ASML Holding", exchange="Euronext",
                asset_class=AssetClass.STOCK, sector="Technology",
                current_price=650.0, currency="EUR",
            ),
            InvestmentOption(
                ticker="AZN.L", name="AstraZeneca", exchange="LSE",
                asset_class=AssetClass.STOCK, sector="Healthcare",
                current_price=12000.0, currency="GBP",
            ),
        ]

    def test_search_by_ticker(self, eu_service, sample_options):
        """Test filtering by ticker substring."""
        result = eu_service.filter_options(sample_options, search="SAP")
        assert len(result) == 1
        assert result[0].ticker == "SAP.DE"

    def test_search_by_name(self, eu_service, sample_options):
        """Test filtering by name substring."""
        result = eu_service.filter_options(sample_options, search="Astra")
        assert len(result) == 1
        assert result[0].name == "AstraZeneca"

    def test_search_by_sector(self, eu_service, sample_options):
        """Test filtering by sector substring."""
        result = eu_service.filter_options(sample_options, search="Health")
        assert len(result) == 1
        assert result[0].sector == "Healthcare"

    def test_search_case_insensitive(self, eu_service, sample_options):
        """Test that search is case-insensitive."""
        result = eu_service.filter_options(sample_options, search="sap")
        assert len(result) == 1
        assert result[0].ticker == "SAP.DE"

    def test_filter_by_exchange(self, eu_service, sample_options):
        """Test filtering by exchange."""
        result = eu_service.filter_options(
            sample_options, exchanges=["XETRA"]
        )
        assert len(result) == 1
        assert result[0].exchange == "XETRA"

    def test_filter_by_multiple_exchanges(self, eu_service, sample_options):
        """Test filtering by multiple exchanges."""
        result = eu_service.filter_options(
            sample_options, exchanges=["XETRA", "LSE"]
        )
        assert len(result) == 2

    def test_filter_by_sector_list(self, eu_service, sample_options):
        """Test filtering by sector list."""
        result = eu_service.filter_options(
            sample_options, sectors=["Technology"]
        )
        assert len(result) == 2
        for r in result:
            assert r.sector == "Technology"

    def test_clear_filter_returns_all(self, eu_service, sample_options):
        """Test that empty filters return all options."""
        result = eu_service.filter_options(sample_options)
        assert len(result) == len(sample_options)


class TestPrepareEuChartData:
    """Tests for prepare_eu_chart_data (T022)."""

    def test_returns_chart_data_dict(self, eu_service):
        """Test that chart data is returned in correct format."""
        chart_data = eu_service.prepare_eu_chart_data("SAP.DE", "5Y")
        assert chart_data is not None
        assert "ticker" in chart_data
        assert "dates" in chart_data
        assert "closes" in chart_data
        assert "pct_changes" in chart_data
        assert len(chart_data["dates"]) == len(chart_data["closes"])

    def test_1y_filter_returns_subset(self, eu_service):
        """Test that 1Y period returns fewer data points than 5Y."""
        data_5y = eu_service.prepare_eu_chart_data("SAP.DE", "5Y")
        data_1y = eu_service.prepare_eu_chart_data("SAP.DE", "1Y")
        assert len(data_1y["dates"]) <= len(data_5y["dates"])

    def test_pct_changes_start_at_zero(self, eu_service):
        """Test that first percentage change is 0.0."""
        chart_data = eu_service.prepare_eu_chart_data("SAP.DE", "5Y")
        assert chart_data["pct_changes"][0] == 0.0

    def test_returns_none_for_no_data(self, mock_eu_provider):
        """Test that None is returned when no history available."""
        mock_eu_provider.get_price_history_5y.return_value = None
        service = InvestmentOptionService(mock_eu_provider)
        assert service.prepare_eu_chart_data("INVALID", "5Y") is None