"""Unit tests for PortfolioService analytics — TDD tests written FIRST.

Tests for allocation, sector exposure, return comparison,
and diversification suggestion.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from app.services.portfolio_service import PortfolioService


@pytest.mark.unit
class TestAllocationCalculation:
    """Tests for asset allocation calculation."""

    def test_allocation_percentages_sum_to_100(self, db_session, sample_holdings, mock_provider):
        """Allocation percentages MUST sum to 100%."""
        mock_provider.get_current_prices.return_value = {
            "AAPL": type(mock_provider.get_current_price.return_value)(
                ticker="AAPL", price=175.0, currency="USD", timestamp=datetime.utcnow()
            ),
            "MSFT": type(mock_provider.get_current_price.return_value)(
                ticker="MSFT", price=380.0, currency="USD", timestamp=datetime.utcnow()
            ),
            "GOOGL": type(mock_provider.get_current_price.return_value)(
                ticker="GOOGL", price=145.0, currency="USD", timestamp=datetime.utcnow()
            ),
        }
        service = PortfolioService(None, None, mock_provider, db_session)
        allocation = service.calculate_allocation(sample_holdings)
        assert sum(allocation.values()) == pytest.approx(100.0)

    def test_empty_holdings_allocation_returns_empty(self, db_session, mock_provider):
        """Empty holdings MUST return empty allocation dict."""
        service = PortfolioService(None, None, mock_provider, db_session)
        allocation = service.calculate_allocation([])
        assert allocation == {}


@pytest.mark.unit
class TestSectorExposure:
    """Tests for sector exposure calculation."""

    def test_sector_breakdown_groups_by_sector(self, db_session, sample_holdings, mock_provider):
        """Sector breakdown MUST group holdings by sector."""
        mock_provider.get_current_prices.return_value = {
            "AAPL": type(mock_provider.get_current_price.return_value)(
                ticker="AAPL", price=175.0, currency="USD", timestamp=datetime.utcnow()
            ),
            "MSFT": type(mock_provider.get_current_price.return_value)(
                ticker="MSFT", price=380.0, currency="USD", timestamp=datetime.utcnow()
            ),
            "GOOGL": type(mock_provider.get_current_price.return_value)(
                ticker="GOOGL", price=145.0, currency="USD", timestamp=datetime.utcnow()
            ),
        }
        service = PortfolioService(None, None, mock_provider, db_session)
        exposure = service.calculate_sector_exposure(sample_holdings)
        assert len(exposure) > 0
        assert sum(exposure.values()) == pytest.approx(100.0)


@pytest.mark.unit
class TestReturnComparison:
    """Tests for holding performance comparison."""

    def test_holdings_ranked_by_return(self, db_session, sample_holdings, mock_provider):
        """Holdings MUST be ranked by percentage return descending."""
        mock_provider.get_current_price.side_effect = lambda t: type(
            mock_provider.get_current_price.return_value
        )(ticker=t, price=175.0, currency="USD", timestamp=datetime.utcnow())
        service = PortfolioService(None, None, mock_provider, db_session)
        ranked = service.compare_holding_performance(sample_holdings)
        for i in range(len(ranked) - 1):
            assert ranked[i].percentage_gain >= ranked[i + 1].percentage_gain


@pytest.mark.unit
class TestDiversificationSuggestion:
    """Tests for diversification suggestion."""

    def test_single_holding_triggers_diversify_suggestion(
        self, db_session, sample_holding, mock_provider
    ):
        """100% allocation in single holding MUST trigger diversify suggestion."""
        service = PortfolioService(None, None, mock_provider, db_session)
        allocation = service.calculate_allocation([sample_holding])
        assert len(allocation) == 1
        assert allocation[sample_holding.ticker] == pytest.approx(100.0)


@pytest.mark.unit
class TestValuationPeRatio:
    """Tests for P/E ratio (valuation) calculation."""

    def test_weighted_pe_uses_value_weights(self, db_session, sample_holdings, mock_provider):
        """Weighted-average P/E MUST weight each holding's P/E by its portfolio value."""
        mock_provider.get_current_prices.return_value = {
            "AAPL": type(mock_provider.get_current_price.return_value)(
                ticker="AAPL", price=175.0, currency="USD", timestamp=datetime.utcnow()
            ),
            "MSFT": type(mock_provider.get_current_price.return_value)(
                ticker="MSFT", price=380.0, currency="USD", timestamp=datetime.utcnow()
            ),
            "GOOGL": type(mock_provider.get_current_price.return_value)(
                ticker="GOOGL", price=145.0, currency="USD", timestamp=datetime.utcnow()
            ),
        }
        mock_provider.get_pe_ratio.side_effect = lambda t: 30.0 if t == "AAPL" else 20.0
        service = PortfolioService(None, None, mock_provider, db_session)
        summary = service.calculate_valuation(sample_holdings)

        # AAPL: 10 * 175 = 1750, P/E 30 → weight 1750/4810
        # MSFT: 5 * 380 = 1900, P/E 20 → weight 1900/4810
        # GOOGL: 8 * 145 = 1160, P/E 20 → weight 1160/4810
        # weighted = (1750*30 + 1900*20 + 1160*20) / 4810
        expected = (1750 * 30 + 1900 * 20 + 1160 * 20) / 4810
        assert summary.weighted_avg_pe == pytest.approx(expected, rel=1e-2)

    def test_holdings_without_pe_excluded_from_weighted_avg(
        self, db_session, sample_holdings, mock_provider
    ):
        """Holdings where P/E is None (e.g., bonds) MUST be excluded from the weighted average."""
        mock_provider.get_current_prices.return_value = {
            "AAPL": type(mock_provider.get_current_price.return_value)(
                ticker="AAPL", price=175.0, currency="USD", timestamp=datetime.utcnow()
            ),
            "MSFT": type(mock_provider.get_current_price.return_value)(
                ticker="MSFT", price=380.0, currency="USD", timestamp=datetime.utcnow()
            ),
            "GOOGL": type(mock_provider.get_current_price.return_value)(
                ticker="GOOGL", price=145.0, currency="USD", timestamp=datetime.utcnow()
            ),
        }
        # Only AAPL has a P/E; MSFT and GOOGL return None (e.g., bond ETFs)
        mock_provider.get_pe_ratio.side_effect = lambda t: 30.0 if t == "AAPL" else None
        service = PortfolioService(None, None, mock_provider, db_session)
        summary = service.calculate_valuation(sample_holdings)

        # Only AAPL counted → weighted avg is just AAPL's P/E
        assert summary.weighted_avg_pe == pytest.approx(30.0)
        assert summary.holding_pe["MSFT"] is None
        assert summary.holding_pe["GOOGL"] is None

    def test_all_holdings_no_pe_returns_none_weighted(self, db_session, sample_holdings, mock_provider):
        """When NO holdings have a valid P/E, weighted average MUST be None."""
        mock_provider.get_current_prices.return_value = {
            "AAPL": type(mock_provider.get_current_price.return_value)(
                ticker="AAPL", price=175.0, currency="USD", timestamp=datetime.utcnow()
            ),
        }
        mock_provider.get_pe_ratio.return_value = None
        service = PortfolioService(None, None, mock_provider, db_session)
        summary = service.calculate_valuation(sample_holdings)

        assert summary.weighted_avg_pe is None

    def test_empty_holdings_returns_empty_valuation(self, db_session, mock_provider):
        """Empty holdings MUST return a valuation with None weighted average."""
        service = PortfolioService(None, None, mock_provider, db_session)
        summary = service.calculate_valuation([])

        assert summary.weighted_avg_pe is None
        assert summary.holding_pe == {}

    def test_per_holding_pe_included(self, db_session, sample_holdings, mock_provider):
        """Each holding's P/E MUST appear in the holding_pe dict, even if None."""
        mock_provider.get_current_prices.return_value = {
            "AAPL": type(mock_provider.get_current_price.return_value)(
                ticker="AAPL", price=175.0, currency="USD", timestamp=datetime.utcnow()
            ),
            "MSFT": type(mock_provider.get_current_price.return_value)(
                ticker="MSFT", price=380.0, currency="USD", timestamp=datetime.utcnow()
            ),
            "GOOGL": type(mock_provider.get_current_price.return_value)(
                ticker="GOOGL", price=145.0, currency="USD", timestamp=datetime.utcnow()
            ),
        }
        mock_provider.get_pe_ratio.side_effect = lambda t: 25.0
        service = PortfolioService(None, None, mock_provider, db_session)
        summary = service.calculate_valuation(sample_holdings)

        assert set(summary.holding_pe.keys()) == {"AAPL", "MSFT", "GOOGL"}
        assert all(v == 25.0 for v in summary.holding_pe.values())
