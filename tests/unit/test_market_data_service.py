"""Unit tests for MarketDataService ticker validation — TDD tests written FIRST."""

from __future__ import annotations

import pytest

from app.services.market_data_service import MarketDataService


@pytest.mark.unit
class TestTickerValidation:
    """Tests for ticker validation via market data service."""

    def test_valid_ticker_accepted(self, mock_provider):
        """Valid ticker MUST be accepted by the validation."""
        service = MarketDataService(provider=mock_provider)
        mock_provider.validate_ticker.return_value = True
        assert service.validate_ticker("AAPL") is True

    def test_invalid_ticker_rejected(self, mock_provider):
        """Invalid ticker MUST be rejected by the validation."""
        service = MarketDataService(provider=mock_provider)
        mock_provider.validate_ticker.return_value = False
        assert service.validate_ticker("INVALID123") is False

    def test_validation_exception_returns_false(self, mock_provider):
        """If provider raises an exception, validation MUST return False."""
        service = MarketDataService(provider=mock_provider)
        mock_provider.validate_ticker.side_effect = Exception("API error")
        assert service.validate_ticker("AAPL") is False