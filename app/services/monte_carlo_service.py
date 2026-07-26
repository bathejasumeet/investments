"""Generic Monte Carlo projection helpers for portfolio simulations."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class MonteCarloSummary:
    """Summary statistics for simulation outcomes."""

    probability_of_success: float
    projected_value_median: float
    projected_value_p10: float
    projected_value_p90: float
    shortfall: float


def run_monte_carlo_projection(
    *,
    current_value: float,
    monthly_contribution: float,
    years: float,
    expected_return: float,
    volatility: float,
    num_simulations: int,
    rng: random.Random | None = None,
) -> list[float]:
    """Project a portfolio forward using geometric Brownian motion."""
    if rng is None:
        rng = random.Random()

    months = int(math.ceil(max(0.0, years) * 12.0))
    if months <= 0:
        return [max(0.0, current_value)] * num_simulations

    monthly_return = expected_return / 12.0
    monthly_vol = volatility / math.sqrt(12.0)

    final_values: list[float] = []
    for _ in range(num_simulations):
        value = max(0.0, current_value)
        for _month in range(months):
            value += max(0.0, monthly_contribution)
            shock = rng.gauss(0.0, 1.0)
            growth = monthly_return + monthly_vol * shock
            value *= (1.0 + growth)
            value = max(0.0, value)
        final_values.append(value)

    return final_values


def summarize_monte_carlo(
    final_values: list[float],
    *,
    target_amount: float,
) -> MonteCarloSummary:
    """Compute success probability and percentile summary."""
    if not final_values:
        return MonteCarloSummary(
            probability_of_success=0.0,
            projected_value_median=0.0,
            projected_value_p10=0.0,
            projected_value_p90=0.0,
            shortfall=max(0.0, target_amount),
        )

    sorted_values = sorted(final_values)
    successes = sum(1 for v in final_values if v >= target_amount)
    probability = successes / len(final_values)
    median = _percentile(sorted_values, 50)
    p10 = _percentile(sorted_values, 10)
    p90 = _percentile(sorted_values, 90)

    return MonteCarloSummary(
        probability_of_success=probability,
        projected_value_median=median,
        projected_value_p10=p10,
        projected_value_p90=p90,
        shortfall=target_amount - median,
    )


def _percentile(sorted_values: list[float], percentile: float) -> float:
    """Linear-interpolated percentile for ascending values."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]

    rank = (percentile / 100.0) * (len(sorted_values) - 1)
    lower = int(math.floor(rank))
    upper = int(math.ceil(rank))
    if lower == upper:
        return sorted_values[lower]

    weight = rank - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight
