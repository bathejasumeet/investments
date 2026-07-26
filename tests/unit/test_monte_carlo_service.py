"""Unit tests for Monte Carlo projection helpers."""

from __future__ import annotations

import random

import pytest

from app.services.monte_carlo_service import run_monte_carlo_projection, summarize_monte_carlo


@pytest.mark.unit
class TestMonteCarloService:
    """Core simulation and summary behavior."""

    def test_projection_returns_expected_count(self) -> None:
        outcomes = run_monte_carlo_projection(
            current_value=10_000.0,
            monthly_contribution=200.0,
            years=5.0,
            expected_return=0.07,
            volatility=0.15,
            num_simulations=500,
            rng=random.Random(42),
        )

        assert len(outcomes) == 500
        assert all(v >= 0 for v in outcomes)

    def test_zero_years_returns_current_value(self) -> None:
        outcomes = run_monte_carlo_projection(
            current_value=12_345.0,
            monthly_contribution=200.0,
            years=0.0,
            expected_return=0.07,
            volatility=0.15,
            num_simulations=3,
            rng=random.Random(42),
        )

        assert outcomes == [12_345.0, 12_345.0, 12_345.0]

    def test_summary_calculates_probability_and_percentiles(self) -> None:
        summary = summarize_monte_carlo([100.0, 200.0, 300.0, 400.0], target_amount=250.0)

        assert summary.probability_of_success == 0.5
        assert summary.projected_value_median == 250.0
        assert summary.projected_value_p10 == 130.0
        assert summary.projected_value_p90 == 370.0
        assert summary.shortfall == 0.0

    def test_empty_summary_returns_zeros(self) -> None:
        summary = summarize_monte_carlo([], target_amount=50_000.0)

        assert summary.probability_of_success == 0.0
        assert summary.projected_value_median == 0.0
        assert summary.shortfall == 50_000.0
