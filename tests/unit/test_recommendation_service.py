"""Unit tests for RecommendationService — TDD tests written FIRST."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.services.recommendation_service import RecommendationService


@pytest.mark.unit
class TestRecommendationRanking:
    """Tests for recommendation ranking by confidence score."""

    def test_recommendations_sorted_by_confidence_descending(self, mock_provider):
        """Recommendations MUST be sorted by confidence score descending."""
        service = RecommendationService(provider=mock_provider)
        recommendations = service.get_recommendations()
        assert len(recommendations) > 0
        for i in range(len(recommendations) - 1):
            assert recommendations[i].confidence_score >= recommendations[i + 1].confidence_score


@pytest.mark.unit
class TestTrendDirection:
    """Tests for trend direction calculation."""

    def test_trend_direction_from_price_history(self, mock_provider):
        """Trend direction MUST be derived from price history (up/down/flat)."""
        service = RecommendationService(provider=mock_provider)
        recommendations = service.get_recommendations()
        for rec in recommendations:
            assert rec.trend_direction in ("up", "down", "flat")


@pytest.mark.unit
class TestPortfolioOverlap:
    """Tests for portfolio overlap detection."""

    def test_recommendation_overlaps_with_portfolio(self, mock_provider, sample_holdings):
        """Recommendations already in portfolio MUST be flagged."""
        service = RecommendationService(provider=mock_provider)
        recommendations = service.get_recommendations(portfolio_tickers=["AAPL", "MSFT"])
        for rec in recommendations:
            if rec.ticker in ("AAPL", "MSFT"):
                assert rec.in_portfolio is True
            else:
                assert rec.in_portfolio is False


@pytest.mark.unit
class TestStaleRecommendationData:
    """Tests for stale recommendation data detection."""

    def test_freshness_warning_when_data_old(self, mock_provider):
        """Freshness warning MUST be set when data is > 1 hour old."""
        service = RecommendationService(provider=mock_provider)
        old_time = datetime.utcnow() - timedelta(hours=2)
        is_stale = service.check_freshness(old_time)
        assert is_stale is True

    def test_no_warning_when_data_fresh(self, mock_provider):
        """Freshness warning MUST NOT be set when data is < 1 hour old."""
        service = RecommendationService(provider=mock_provider)
        recent_time = datetime.utcnow() - timedelta(minutes=15)
        is_stale = service.check_freshness(recent_time)
        assert is_stale is False