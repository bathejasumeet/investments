"""Unit tests for Monte Carlo projection helpers."""

from __future__ import annotations

import math
import random

import pytest

from app.services.monte_carlo_service import (
    MonteCarloConfig,
    build_covariance_from_prices,
    estimate_portfolio_params,
    estimate_return_and_vol_from_prices,
    percentiles_to_csv,
    run_monte_carlo,
    run_monte_carlo_projection,
    run_multi_asset_monte_carlo,
    solve_required_contribution,
    summarize_monte_carlo,
)


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

    def test_summary_includes_rich_stats(self) -> None:
        values = [100.0, 200.0, 300.0, 400.0, 500.0]
        summary = summarize_monte_carlo(
            values,
            target_amount=250.0,
            percentiles=(5, 10, 25, 50, 75, 90, 95),
        )

        assert 5.0 in summary.percentiles
        assert 95.0 in summary.percentiles
        assert summary.mean == pytest.approx(300.0)
        assert summary.min_value == 100.0
        assert summary.max_value == 500.0
        assert summary.std > 0
        assert summary.var_5 <= summary.projected_value_median
        assert summary.cvar_5 <= summary.var_5

    def test_seed_makes_runs_reproducible(self) -> None:
        cfg = MonteCarloConfig(
            current_value=10_000.0,
            monthly_contribution=100.0,
            years=3.0,
            expected_return=0.06,
            volatility=0.12,
            num_simulations=200,
            target_amount=15_000.0,
            seed=123,
            store_yearly_paths=False,
        )
        a = run_monte_carlo(cfg)
        b = run_monte_carlo(cfg)
        assert a.final_values == b.final_values

    def test_fee_drag_reduces_median(self) -> None:
        base = run_monte_carlo(
            MonteCarloConfig(
                current_value=20_000.0,
                monthly_contribution=0.0,
                years=10.0,
                expected_return=0.08,
                volatility=0.0,
                num_simulations=20,
                seed=1,
                fee_drag=0.0,
                real_terms=False,
                store_yearly_paths=False,
            )
        )
        with_fees = run_monte_carlo(
            MonteCarloConfig(
                current_value=20_000.0,
                monthly_contribution=0.0,
                years=10.0,
                expected_return=0.08,
                volatility=0.0,
                num_simulations=20,
                seed=1,
                fee_drag=0.02,
                real_terms=False,
                store_yearly_paths=False,
            )
        )
        assert with_fees.summary.projected_value_median < base.summary.projected_value_median

    def test_inflation_real_terms_reduces_terminal(self) -> None:
        nominal = run_monte_carlo(
            MonteCarloConfig(
                current_value=10_000.0,
                monthly_contribution=0.0,
                years=10.0,
                expected_return=0.05,
                volatility=0.0,
                num_simulations=10,
                seed=7,
                inflation_rate=0.03,
                real_terms=False,
                store_yearly_paths=False,
            )
        )
        real = run_monte_carlo(
            MonteCarloConfig(
                current_value=10_000.0,
                monthly_contribution=0.0,
                years=10.0,
                expected_return=0.05,
                volatility=0.0,
                num_simulations=10,
                seed=7,
                inflation_rate=0.03,
                real_terms=True,
                store_yearly_paths=False,
            )
        )
        assert real.summary.mean < nominal.summary.mean

    def test_contribution_timing_end_differs_from_start(self) -> None:
        start = run_monte_carlo(
            MonteCarloConfig(
                current_value=1_000.0,
                monthly_contribution=500.0,
                years=2.0,
                expected_return=0.12,
                volatility=0.0,
                num_simulations=5,
                seed=2,
                contribution_timing="start",
                real_terms=False,
                store_yearly_paths=False,
            )
        )
        end = run_monte_carlo(
            MonteCarloConfig(
                current_value=1_000.0,
                monthly_contribution=500.0,
                years=2.0,
                expected_return=0.12,
                volatility=0.0,
                num_simulations=5,
                seed=2,
                contribution_timing="end",
                real_terms=False,
                store_yearly_paths=False,
            )
        )
        # Start-of-month contributions compound longer.
        assert start.summary.mean > end.summary.mean

    def test_yearly_bands_produced(self) -> None:
        result = run_monte_carlo(
            MonteCarloConfig(
                current_value=5_000.0,
                monthly_contribution=100.0,
                years=5.0,
                expected_return=0.07,
                volatility=0.1,
                num_simulations=100,
                seed=9,
                store_yearly_paths=True,
            )
        )
        assert len(result.yearly_bands) == 5
        assert result.yearly_bands[0].year == 1
        assert 50.0 in result.yearly_bands[0].percentiles

    def test_solve_required_contribution_monotonic(self) -> None:
        required = solve_required_contribution(
            current_value=10_000.0,
            years=5.0,
            expected_return=0.05,
            volatility=0.1,
            target_amount=50_000.0,
            target_probability=0.7,
            num_simulations=300,
            seed=11,
            real_terms=False,
            max_monthly=5_000.0,
        )
        assert required >= 0.0
        check = run_monte_carlo(
            MonteCarloConfig(
                current_value=10_000.0,
                monthly_contribution=required,
                years=5.0,
                expected_return=0.05,
                volatility=0.1,
                num_simulations=300,
                target_amount=50_000.0,
                seed=11,
                real_terms=False,
                store_yearly_paths=False,
            )
        )
        assert check.summary.probability_of_success >= 0.65

    def test_estimate_return_and_vol_from_prices(self) -> None:
        # Synthetic geometric path ~10% annual, mild noise.
        prices = [100.0]
        rng = random.Random(0)
        for _ in range(252):
            prices.append(prices[-1] * math.exp(0.10 / 252 + 0.01 * rng.gauss(0, 1) / math.sqrt(252)))
        estimated = estimate_return_and_vol_from_prices(prices)
        assert estimated is not None
        mu, sigma = estimated
        assert 0.0 < mu < 0.3
        assert sigma > 0.0

    def test_estimate_portfolio_params_blends_assets(self) -> None:
        rng = random.Random(3)
        a = [100.0]
        b = [50.0]
        for _ in range(300):
            a.append(a[-1] * math.exp(0.08 / 252 + 0.15 * rng.gauss(0, 1) / math.sqrt(252)))
            b.append(b[-1] * math.exp(0.03 / 252 + 0.05 * rng.gauss(0, 1) / math.sqrt(252)))
        result = estimate_portfolio_params(
            {"A": a, "B": b},
            {"A": 0.6, "B": 0.4},
        )
        assert result is not None
        mu, sigma = result
        assert sigma > 0.0
        assert -0.5 < mu < 0.5

    def test_multi_asset_runs(self) -> None:
        # Simple 2-asset identity-ish covariance.
        cov = [[0.04, 0.01], [0.01, 0.01]]
        result = run_multi_asset_monte_carlo(
            current_value=10_000.0,
            monthly_contribution=100.0,
            years=3.0,
            weights=[0.7, 0.3],
            expected_returns=[0.08, 0.03],
            covariance=cov,
            num_simulations=150,
            target_amount=12_000.0,
            seed=21,
            real_terms=False,
        )
        assert len(result.final_values) == 150
        assert 0.0 <= result.summary.probability_of_success <= 1.0
        assert result.summary.mean > 0

    def test_build_covariance_from_prices(self) -> None:
        rng = random.Random(5)
        a = [100.0]
        b = [100.0]
        for _ in range(200):
            z = rng.gauss(0, 1)
            a.append(a[-1] * math.exp(0.001 + 0.01 * z))
            b.append(b[-1] * math.exp(0.0005 + 0.008 * z + 0.004 * rng.gauss(0, 1)))
        cov = build_covariance_from_prices({"A": a, "B": b}, ["A", "B"])
        assert cov is not None
        assert len(cov) == 2
        assert cov[0][0] > 0
        assert cov[1][1] > 0

    def test_percentiles_to_csv_contains_headers(self) -> None:
        result = run_monte_carlo(
            MonteCarloConfig(
                current_value=1_000.0,
                monthly_contribution=50.0,
                years=2.0,
                expected_return=0.05,
                volatility=0.1,
                num_simulations=50,
                seed=4,
                target_amount=2_000.0,
            )
        )
        csv_text = percentiles_to_csv(result.summary, yearly_bands=result.yearly_bands)
        assert "percentile" in csv_text
        assert "P50" in csv_text or "P50.0" in csv_text
        assert "probability_of_success" in csv_text
