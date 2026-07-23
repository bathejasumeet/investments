"""Goal service — business logic for goal-based investing and probability of success.

Uses Monte Carlo simulation to project portfolio growth toward each goal's
target amount and target date, computing the probability of success.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.models.holding import Holding
from app.providers.base import MarketDataProvider
from app.repositories.goal_repository import GoalRepository
from app.repositories.holding_repository import HoldingRepository
from app.utils.currency import convert_amount


@dataclass(frozen=True)
class GoalProjection:
    """Projection result for a single goal.

    Attributes:
        goal_id: The goal's primary key.
        goal_name: Human-readable goal name.
        current_value: Current value of holdings mapped to this goal (in base currency).
        target_amount: The amount of money needed.
        target_date: The date by which the goal should be reached.
        years_to_target: Years remaining until the target date.
        monthly_contribution: Recurring monthly contribution toward the goal.
        probability_of_success: Probability (0–1) of reaching the target.
        projected_value_median: Median projected value at target date.
        projected_value_p10: 10th percentile projected value (worst-case).
        projected_value_p90: 90th percentile projected value (best-case).
        shortfall: target_amount - projected_value_median (negative = surplus).
        currency: Base currency code.
    """

    goal_id: int
    goal_name: str
    current_value: float
    target_amount: float
    target_date: datetime
    years_to_target: float
    monthly_contribution: float
    probability_of_success: float
    projected_value_median: float
    projected_value_p10: float
    projected_value_p90: float
    shortfall: float
    currency: str = "EUR"
    mapped_tickers: list[str] = field(default_factory=list)


class GoalService:
    """Service for goal-based investing analysis with Monte Carlo simulation."""

    # Default market assumptions (can be overridden per call)
    DEFAULT_EXPECTED_RETURN = 0.07  # 7% annual expected return
    DEFAULT_VOLATILITY = 0.15  # 15% annual standard deviation
    DEFAULT_SIMULATIONS = 1000  # Monte Carlo simulation count

    def __init__(
        self,
        goal_repo: GoalRepository,
        holding_repo: HoldingRepository,
        provider: MarketDataProvider,
        session: Session,
        base_currency: str = "EUR",
    ) -> None:
        self._goal_repo = goal_repo
        self._holding_repo = holding_repo
        self._provider = provider
        self._session = session
        self._base_currency = base_currency.upper()

    def _to_base_currency(self, amount: float, source_currency: str) -> float:
        """Convert an amount from source currency into base currency."""
        return convert_amount(
            amount,
            source_currency=source_currency,
            target_currency=self._base_currency,
            provider=self._provider,
        )

    def _get_current_prices(self, tickers: list[str]) -> dict[str, float]:
        """Fetch current prices for tickers, converted to base currency."""
        if not tickers:
            return {}
        quotes = self._provider.get_current_prices(tickers)
        prices: dict[str, float] = {}
        for ticker, quote in quotes.items():
            prices[ticker] = self._to_base_currency(quote.price, quote.currency)
        return prices

    def calculate_goal_current_value(
        self, goal_id: int, holdings: list[Holding]
    ) -> tuple[float, list[str]]:
        """Calculate the current value of holdings mapped to a goal.

        Args:
            goal_id: The goal's primary key.
            holdings: All holdings in the portfolio.

        Returns:
            Tuple of (current_value_in_base_currency, list_of_mapped_tickers).
        """
        mappings = self._goal_repo.get_mappings_for_goal(goal_id)
        if not mappings:
            return 0.0, []

        holding_map = {h.id: h for h in holdings}
        tickers = [holding_map[m.holding_id].ticker for m in mappings if m.holding_id in holding_map]
        prices = self._get_current_prices(tickers)

        total = 0.0
        mapped_tickers: list[str] = []
        for mapping in mappings:
            holding = holding_map.get(mapping.holding_id)
            if holding is None:
                continue
            price = prices.get(holding.ticker, 0.0)
            value = holding.quantity * price * (mapping.allocation_pct / 100.0)
            total += value
            mapped_tickers.append(holding.ticker)

        return total, mapped_tickers

    def project_goal(
        self,
        goal: Goal,
        holdings: list[Holding],
        expected_return: float = DEFAULT_EXPECTED_RETURN,
        volatility: float = DEFAULT_VOLATILITY,
        num_simulations: int = DEFAULT_SIMULATIONS,
        rng: random.Random | None = None,
    ) -> GoalProjection:
        """Project a single goal using Monte Carlo simulation.

        Args:
            goal: The goal to project.
            holdings: All holdings in the portfolio.
            expected_return: Annual expected return (e.g., 0.07 for 7%).
            volatility: Annual standard deviation (e.g., 0.15 for 15%).
            num_simulations: Number of Monte Carlo simulations to run.
            rng: Optional random.Random instance for deterministic testing.

        Returns:
            GoalProjection with probability of success and percentile outcomes.
        """
        current_value, mapped_tickers = self.calculate_goal_current_value(goal.id, holdings)

        now = datetime.utcnow()
        years_to_target = max(
            0.0, (goal.target_date - now).total_seconds() / (365.25 * 24 * 3600)
        )
        months_to_target = int(math.ceil(years_to_target * 12))

        # Run Monte Carlo simulation
        final_values = self._run_monte_carlo(
            current_value=current_value,
            monthly_contribution=goal.monthly_contribution,
            months=months_to_target,
            expected_return=expected_return,
            volatility=volatility,
            num_simulations=num_simulations,
            rng=rng,
        )

        # Calculate probability of success
        successes = sum(1 for v in final_values if v >= goal.target_amount)
        probability = successes / num_simulations if num_simulations > 0 else 0.0

        # Calculate percentiles
        sorted_values = sorted(final_values)
        median = self._percentile(sorted_values, 50)
        p10 = self._percentile(sorted_values, 10)
        p90 = self._percentile(sorted_values, 90)
        shortfall = goal.target_amount - median

        return GoalProjection(
            goal_id=goal.id,
            goal_name=goal.name,
            current_value=current_value,
            target_amount=goal.target_amount,
            target_date=goal.target_date,
            years_to_target=years_to_target,
            monthly_contribution=goal.monthly_contribution,
            probability_of_success=probability,
            projected_value_median=median,
            projected_value_p10=p10,
            projected_value_p90=p90,
            shortfall=shortfall,
            currency=self._base_currency,
            mapped_tickers=mapped_tickers,
        )

    def project_all_goals(
        self,
        holdings: list[Holding] | None = None,
        expected_return: float = DEFAULT_EXPECTED_RETURN,
        volatility: float = DEFAULT_VOLATILITY,
        num_simulations: int = DEFAULT_SIMULATIONS,
        rng: random.Random | None = None,
    ) -> list[GoalProjection]:
        """Project all goals in the database.

        Args:
            holdings: All holdings (fetched from repo if not provided).
            expected_return: Annual expected return.
            volatility: Annual standard deviation.
            num_simulations: Number of Monte Carlo simulations.
            rng: Optional random.Random for deterministic testing.

        Returns:
            List of GoalProjection for all goals.
        """
        goals = self._goal_repo.get_all()
        if not goals:
            return []

        if holdings is None:
            holdings = self._holding_repo.get_all()

        projections: list[GoalProjection] = []
        for goal in goals:
            projection = self.project_goal(
                goal=goal,
                holdings=holdings,
                expected_return=expected_return,
                volatility=volatility,
                num_simulations=num_simulations,
                rng=rng,
            )
            projections.append(projection)

        return projections

    def _run_monte_carlo(
        self,
        current_value: float,
        monthly_contribution: float,
        months: int,
        expected_return: float,
        volatility: float,
        num_simulations: int,
        rng: random.Random | None = None,
    ) -> list[float]:
        """Run Monte Carlo simulation projecting portfolio value forward.

        Uses geometric Brownian motion with monthly time steps.

        Args:
            current_value: Starting portfolio value.
            monthly_contribution: Added at the start of each month.
            months: Number of months to project.
            expected_return: Annual expected return.
            volatility: Annual standard deviation.
            num_simulations: Number of simulation paths.
            rng: Optional random.Random for deterministic testing.

        Returns:
            List of final portfolio values from each simulation.
        """
        if rng is None:
            rng = random.Random()

        if months <= 0:
            return [current_value] * num_simulations

        # Convert annual parameters to monthly
        monthly_return = expected_return / 12.0
        monthly_vol = volatility / math.sqrt(12.0)

        final_values: list[float] = []
        for _ in range(num_simulations):
            value = current_value
            for _month in range(months):
                # Add monthly contribution at start of month
                value += monthly_contribution
                # Apply random return (geometric Brownian motion)
                shock = rng.gauss(0.0, 1.0)
                monthly_growth = monthly_return + monthly_vol * shock
                value *= (1.0 + monthly_growth)
                # Prevent negative values
                value = max(0.0, value)
            final_values.append(value)

        return final_values

    @staticmethod
    def _percentile(sorted_values: list[float], percentile: float) -> float:
        """Calculate the percentile of a sorted list of values.

        Args:
            sorted_values: Values sorted in ascending order.
            percentile: Percentile to calculate (0–100).

        Returns:
            The value at the given percentile.
        """
        if not sorted_values:
            return 0.0
        if len(sorted_values) == 1:
            return sorted_values[0]

        # Linear interpolation method
        rank = (percentile / 100.0) * (len(sorted_values) - 1)
        lower = int(math.floor(rank))
        upper = int(math.ceil(rank))
        if lower == upper:
            return sorted_values[lower]

        weight = rank - lower
        return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight

    def get_success_label(self, probability: float) -> str:
        """Return a human-readable label for a probability of success.

        Args:
            probability: Probability of success (0–1).

        Returns:
            Label string (e.g., "On Track", "At Risk", "Off Track").
        """
        if probability >= 0.80:
            return "On Track"
        elif probability >= 0.50:
            return "On Track" if probability >= 0.70 else "At Risk"
        elif probability >= 0.30:
            return "At Risk"
        else:
            return "Off Track"
