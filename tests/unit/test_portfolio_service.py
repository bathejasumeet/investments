"""Unit tests for PortfolioService — TDD tests written FIRST.

Tests MUST FAIL before implementation (Red-Green-Refactor).
Covers: portfolio value calculation, gain/loss, empty portfolio,
and stale data detection.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.services.portfolio_service import PortfolioService


@pytest.mark.unit
class TestPortfolioValueCalculation:
    """Tests for total portfolio value calculation."""

    def test_total_value_is_sum_of_holding_current_values(
        self, db_session, sample_holdings, mock_provider
    ):
        """Total portfolio value MUST equal sum of all holding current values."""
        service = PortfolioService(
            holding_repo=None,  # Will use db_session directly
            price_repo=None,
            provider=mock_provider,
            session=db_session,
        )
        # Mock provider returns 175.00 for AAPL
        # We need to set up prices for all tickers
        mock_provider.get_current_prices.return_value = {
            "AAPL": type(mock_provider.get_current_price.return_value)(
                ticker="AAPL", price=175.00, currency="USD",
                timestamp=datetime.utcnow()
            ),
            "MSFT": type(mock_provider.get_current_price.return_value)(
                ticker="MSFT", price=380.00, currency="USD",
                timestamp=datetime.utcnow()
            ),
            "GOOGL": type(mock_provider.get_current_price.return_value)(
                ticker="GOOGL", price=145.00, currency="USD",
                timestamp=datetime.utcnow()
            ),
        }

        result = service.calculate_total_value(sample_holdings)

        # AAPL: 10 * 175 = 1750
        # MSFT: 5 * 380 = 1900
        # GOOGL: 8 * 145 = 1160
        # Total: 4810
        assert result == pytest.approx(4810.0)

    def test_single_holding_value_calculation(
        self, db_session, sample_holding, mock_provider
    ):
        """Single holding value MUST be quantity * current_price."""
        service = PortfolioService(
            holding_repo=None,
            price_repo=None,
            provider=mock_provider,
            session=db_session,
        )
        result = service.calculate_total_value([sample_holding])
        # 10 shares * 175.00 = 1750
        assert result == pytest.approx(1750.0)


@pytest.mark.unit
class TestGainLossCalculation:
    """Tests for gain/loss calculation per holding."""

    def test_absolute_gain_loss_for_holding(
        self, db_session, sample_holding, mock_provider
    ):
        """Absolute gain/loss MUST be (current_price - purchase_price) * quantity."""
        service = PortfolioService(
            holding_repo=None,
            price_repo=None,
            provider=mock_provider,
            session=db_session,
        )
        # purchase_price=150, current=175, quantity=10
        # gain = (175 - 150) * 10 = 250
        result = service.calculate_gain_loss(sample_holding)
        assert result.absolute_gain == pytest.approx(250.0)

    def test_percentage_gain_loss_for_holding(
        self, db_session, sample_holding, mock_provider
    ):
        """Percentage gain/loss MUST be ((current - purchase) / purchase) * 100."""
        service = PortfolioService(
            holding_repo=None,
            price_repo=None,
            provider=mock_provider,
            session=db_session,
        )
        # (175 - 150) / 150 * 100 = 16.67%
        result = service.calculate_gain_loss(sample_holding)
        assert result.percentage_gain == pytest.approx(16.67, rel=1e-2)

    def test_loss_when_current_below_purchase(
        self, db_session, mock_provider
    ):
        """Gain/loss MUST be negative when current price < purchase price."""
        from app.models.holding import Holding
        holding = Holding(
            ticker="TEST",
            quantity=10.0,
            purchase_price=200.00,
            date_acquired=datetime(2024, 1, 1),
        )
        db_session.add(holding)
        db_session.commit()

        service = PortfolioService(
            holding_repo=None,
            price_repo=None,
            provider=mock_provider,
            session=db_session,
        )
        # current price = 175, purchase = 200
        # loss = (175 - 200) * 10 = -250
        result = service.calculate_gain_loss(holding)
        assert result.absolute_gain == pytest.approx(-250.0)
        assert result.percentage_gain < 0


@pytest.mark.unit
class TestEmptyPortfolio:
    """Tests for empty portfolio handling."""

    def test_empty_portfolio_returns_zero_value(
        self, db_session, mock_provider
    ):
        """Empty portfolio MUST return zero total value without crashing."""
        service = PortfolioService(
            holding_repo=None,
            price_repo=None,
            provider=mock_provider,
            session=db_session,
        )
        result = service.calculate_total_value([])
        assert result == 0.0

    def test_empty_portfolio_summary_has_no_holdings(
        self, db_session, mock_provider
    ):
        """Empty portfolio summary MUST have empty holdings list."""
        service = PortfolioService(
            holding_repo=None,
            price_repo=None,
            provider=mock_provider,
            session=db_session,
        )
        summary = service.get_portfolio_summary([])
        assert summary.holdings == []
        assert summary.total_value == 0.0
        assert summary.total_gain_loss == 0.0


@pytest.mark.unit
class TestStaleDataDetection:
    """Tests for stale data detection."""

    def test_data_older_than_one_hour_is_stale(
        self, db_session, mock_provider
    ):
        """Data fetched more than 1 hour ago MUST be flagged as stale."""
        service = PortfolioService(
            holding_repo=None,
            price_repo=None,
            provider=mock_provider,
            session=db_session,
        )
        old_timestamp = datetime.utcnow() - timedelta(hours=2)
        is_stale = service.check_data_freshness(old_timestamp)
        assert is_stale is True

    def test_recent_data_is_not_stale(
        self, db_session, mock_provider
    ):
        """Data fetched within the last hour MUST NOT be flagged as stale."""
        service = PortfolioService(
            holding_repo=None,
            price_repo=None,
            provider=mock_provider,
            session=db_session,
        )
        recent_timestamp = datetime.utcnow() - timedelta(minutes=30)
        is_stale = service.check_data_freshness(recent_timestamp)
        assert is_stale is False

    def test_none_timestamp_is_stale(
        self, db_session, mock_provider
    ):
        """None timestamp (no data) MUST be flagged as stale."""
        service = PortfolioService(
            holding_repo=None,
            price_repo=None,
            provider=mock_provider,
            session=db_session,
        )
        is_stale = service.check_data_freshness(None)
        assert is_stale is True