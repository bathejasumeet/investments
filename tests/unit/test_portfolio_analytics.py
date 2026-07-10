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