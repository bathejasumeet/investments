"""End-to-end tests for critical user journeys."""

from __future__ import annotations

from datetime import datetime

import pytest

from app.repositories.holding_repository import HoldingRepository
from app.services.portfolio_service import PortfolioService


@pytest.mark.e2e
class TestAddHoldingToDashboard:
    """E2E: Add a holding and verify it appears in portfolio summary."""

    def test_add_holding_then_verify_dashboard_update(
        self, db_session, mock_provider
    ):
        """Adding a holding MUST be reflected in the portfolio summary."""
        # Step 1: Add a holding
        repo = HoldingRepository(db_session)
        holding = repo.add(
            ticker="AAPL",
            quantity=10.0,
            purchase_price=150.00,
        )
        assert holding.id is not None

        # Step 2: Verify it appears in portfolio summary
        service = PortfolioService(None, None, mock_provider, db_session)
        holdings = repo.get_all()
        assert len(holdings) == 1

        summary = service.get_portfolio_summary(holdings)
        assert len(summary.holdings) == 1
        assert summary.holdings[0].ticker == "AAPL"
        assert summary.total_value > 0


@pytest.mark.e2e
class TestRefreshRecommendations:
    """E2E: Open recommendations and refresh to get new data."""

    def test_refresh_recommendations_returns_data(
        self, mock_provider
    ):
        """Refreshing recommendations MUST return new data."""
        from app.services.recommendation_service import RecommendationService

        service = RecommendationService(provider=mock_provider)
        recommendations = service.get_recommendations()
        assert len(recommendations) > 0

        # Verify last fetch time is set
        last_fetch = service.get_last_fetch_time()
        assert last_fetch is not None