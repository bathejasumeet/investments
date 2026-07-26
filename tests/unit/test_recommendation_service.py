"""Unit tests for RecommendationService — TDD tests written FIRST."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.services.recommendation_service import (
    FactorBreakdown,
    FactorScore,
    RecommendationService,
)


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
            assert rec.currency == "EUR"


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


@pytest.mark.unit
class TestExplainableFactorBreakdown:
    """Tests for explainable factor breakdown in recommendations."""

    def test_every_recommendation_has_factor_breakdown(self, mock_provider):
        """Every recommendation MUST include a FactorBreakdown."""
        service = RecommendationService(provider=mock_provider)
        recommendations = service.get_recommendations()
        assert len(recommendations) > 0
        for rec in recommendations:
            assert rec.factors is not None
            assert isinstance(rec.factors, FactorBreakdown)

    def test_factor_breakdown_contains_all_five_factors(self, mock_provider):
        """FactorBreakdown MUST contain momentum, valuation, volatility, volume, concentration."""
        service = RecommendationService(provider=mock_provider)
        recommendations = service.get_recommendations()
        for rec in recommendations:
            factors = rec.factors
            assert isinstance(factors.momentum, FactorScore)
            assert isinstance(factors.valuation, FactorScore)
            assert isinstance(factors.volatility, FactorScore)
            assert isinstance(factors.volume, FactorScore)
            assert isinstance(factors.concentration, FactorScore)

    def test_factor_scores_are_normalized_to_0_1(self, mock_provider):
        """Each factor score MUST be normalized to the 0.0-1.0 range."""
        service = RecommendationService(provider=mock_provider)
        recommendations = service.get_recommendations()
        for rec in recommendations:
            for factor in rec.factors.all_factors():
                assert 0.0 <= factor.score <= 1.0, (
                    f"{factor.name} score {factor.score} out of range"
                )

    def test_composite_score_equals_weighted_sum(self, mock_provider):
        """Composite confidence score MUST equal the weighted sum of factor scores."""
        service = RecommendationService(provider=mock_provider)
        recommendations = service.get_recommendations()
        for rec in recommendations:
            factors = rec.factors
            expected = (
                factors.momentum.score * factors.momentum.weight
                + factors.valuation.score * factors.valuation.weight
                + factors.volatility.score * factors.volatility.weight
                + factors.volume.score * factors.volume.weight
                + factors.concentration.score * factors.concentration.weight
            )
            assert abs(rec.confidence_score - expected) < 0.01

    def test_factor_weights_sum_to_one(self, mock_provider):
        """Factor weights MUST sum to 1.0."""
        service = RecommendationService(provider=mock_provider)
        recommendations = service.get_recommendations()
        for rec in recommendations:
            total_weight = sum(f.weight for f in rec.factors.all_factors())
            assert abs(total_weight - 1.0) < 0.001

    def test_factor_has_human_readable_explanation(self, mock_provider):
        """Each FactorScore MUST have a human-readable explanation."""
        service = RecommendationService(provider=mock_provider)
        recommendations = service.get_recommendations()
        for rec in recommendations:
            for factor in rec.factors.all_factors():
                assert factor.name
                assert factor.explanation
                assert len(factor.explanation) > 5

    def test_concentration_impact_reflects_portfolio_overlap(self, mock_provider):
        """Concentration factor MUST penalize tickers already in portfolio."""
        service = RecommendationService(provider=mock_provider)
        recommendations = service.get_recommendations(
            portfolio_tickers=["AAPL", "MSFT"]
        )
        for rec in recommendations:
            if rec.in_portfolio:
                assert rec.factors.concentration.score < 0.5
            else:
                assert rec.factors.concentration.score >= 0.5

    def test_momentum_factor_reflects_price_change(self, mock_provider):
        """Momentum factor MUST be higher for stronger upward price changes."""
        service = RecommendationService(provider=mock_provider)
        recommendations = service.get_recommendations()
        assert len(recommendations) >= 2
        # NVDA has +12.5% change, AAPL has +5.2% change
        nvda = next(r for r in recommendations if r.ticker == "NVDA")
        aapl = next(r for r in recommendations if r.ticker == "AAPL")
        assert nvda.factors.momentum.score > aapl.factors.momentum.score
