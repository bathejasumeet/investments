"""Unit tests for GoalService — Monte Carlo simulation and probability of success.

Tests cover: goal current value calculation, Monte Carlo projection,
probability of success, percentile calculation, edge cases, and labels.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

import pytest

from app.models.goal import Goal
from app.models.goal_holding_mapping import GoalHoldingMapping
from app.repositories.goal_repository import GoalRepository
from app.repositories.holding_repository import HoldingRepository
from app.services.goal_service import GoalService
from app.services.monte_carlo_service import summarize_monte_carlo


@pytest.mark.unit
class TestGoalCurrentValue:
    """Tests for calculating current value of holdings mapped to a goal."""

    def test_current_value_with_full_allocation(
        self, db_session, sample_goal, sample_holding, sample_goal_mapping, mock_provider
    ):
        """Current value MUST equal holding value when allocation is 100%."""
        goal_repo = GoalRepository(db_session)
        holding_repo = HoldingRepository(db_session)
        service = GoalService(goal_repo, holding_repo, mock_provider, db_session)

        value, tickers = service.calculate_goal_current_value(
            sample_goal.id, [sample_holding]
        )
        # 10 shares * 175.00 = 1750.0
        assert value == pytest.approx(1750.0)
        assert tickers == ["AAPL"]

    def test_current_value_with_partial_allocation(
        self, db_session, sample_holding, mock_provider
    ):
        """Current value MUST reflect partial allocation percentage."""
        goal = Goal(
            name="Test Goal",
            target_amount=100000.0,
            target_date=datetime(2035, 1, 1),
            monthly_contribution=0.0,
        )
        db_session.add(goal)
        db_session.commit()
        db_session.refresh(goal)

        mapping = GoalHoldingMapping(
            goal_id=goal.id,
            holding_id=sample_holding.id,
            allocation_pct=50.0,
        )
        db_session.add(mapping)
        db_session.commit()

        goal_repo = GoalRepository(db_session)
        holding_repo = HoldingRepository(db_session)
        service = GoalService(goal_repo, holding_repo, mock_provider, db_session)

        value, _ = service.calculate_goal_current_value(goal.id, [sample_holding])
        # 10 shares * 175.00 * 50% = 875.0
        assert value == pytest.approx(875.0)

    def test_current_value_with_no_mappings(
        self, db_session, sample_goal, sample_holding, mock_provider
    ):
        """Current value MUST be 0 when no holdings are mapped."""
        goal_repo = GoalRepository(db_session)
        holding_repo = HoldingRepository(db_session)
        service = GoalService(goal_repo, holding_repo, mock_provider, db_session)

        value, tickers = service.calculate_goal_current_value(
            sample_goal.id, [sample_holding]
        )
        assert value == 0.0
        assert tickers == []


@pytest.mark.unit
class TestMonteCarloProjection:
    """Tests for Monte Carlo projection and probability of success."""

    def test_projection_returns_goal_projection(
        self, db_session, sample_goal, sample_holding, sample_goal_mapping, mock_provider
    ):
        """project_goal MUST return a GoalProjection with all fields populated."""
        goal_repo = GoalRepository(db_session)
        holding_repo = HoldingRepository(db_session)
        service = GoalService(goal_repo, holding_repo, mock_provider, db_session)

        rng = random.Random(42)
        projection = service.project_goal(
            goal=sample_goal,
            holdings=[sample_holding],
            num_simulations=100,
            rng=rng,
        )

        assert projection.goal_id == sample_goal.id
        assert projection.goal_name == "Retire at 60"
        assert projection.current_value == pytest.approx(1750.0)
        assert projection.target_amount == 500000.0
        assert 0.0 <= projection.probability_of_success <= 1.0
        assert projection.projected_value_median > 0
        assert projection.projected_value_p10 > 0
        assert projection.projected_value_p90 > 0
        assert projection.currency == "EUR"
        assert "AAPL" in projection.mapped_tickers

    def test_probability_zero_when_target_far_above_current(
        self, db_session, sample_holding, mock_provider
    ):
        """Probability MUST be near 0 when target is unreachable."""
        goal = Goal(
            name="Impossible Goal",
            target_amount=10_000_000.0,  # 10M target
            target_date=datetime.utcnow() + timedelta(days=365),
            monthly_contribution=0.0,
        )
        db_session.add(goal)
        db_session.commit()
        db_session.refresh(goal)

        mapping = GoalHoldingMapping(
            goal_id=goal.id, holding_id=sample_holding.id, allocation_pct=100.0
        )
        db_session.add(mapping)
        db_session.commit()

        goal_repo = GoalRepository(db_session)
        holding_repo = HoldingRepository(db_session)
        service = GoalService(goal_repo, holding_repo, mock_provider, db_session)

        rng = random.Random(42)
        projection = service.project_goal(
            goal=goal,
            holdings=[sample_holding],
            num_simulations=100,
            rng=rng,
        )
        assert projection.probability_of_success == pytest.approx(0.0, abs=0.05)

    def test_probability_high_when_target_below_current(
        self, db_session, sample_holding, mock_provider
    ):
        """Probability MUST be near 1 when current value already exceeds target."""
        goal = Goal(
            name="Easy Goal",
            target_amount=100.0,  # Very low target
            target_date=datetime.utcnow() + timedelta(days=365),
            monthly_contribution=0.0,
        )
        db_session.add(goal)
        db_session.commit()
        db_session.refresh(goal)

        mapping = GoalHoldingMapping(
            goal_id=goal.id, holding_id=sample_holding.id, allocation_pct=100.0
        )
        db_session.add(mapping)
        db_session.commit()

        goal_repo = GoalRepository(db_session)
        holding_repo = HoldingRepository(db_session)
        service = GoalService(goal_repo, holding_repo, mock_provider, db_session)

        rng = random.Random(42)
        projection = service.project_goal(
            goal=goal,
            holdings=[sample_holding],
            num_simulations=100,
            rng=rng,
        )
        assert projection.probability_of_success == pytest.approx(1.0, abs=0.05)

    def test_zero_months_returns_current_value(
        self, db_session, sample_holding, mock_provider
    ):
        """When target date is in the past, projected value MUST equal current."""
        goal = Goal(
            name="Past Goal",
            target_amount=1000.0,
            target_date=datetime.utcnow() - timedelta(days=365),
            monthly_contribution=0.0,
        )
        db_session.add(goal)
        db_session.commit()
        db_session.refresh(goal)

        mapping = GoalHoldingMapping(
            goal_id=goal.id, holding_id=sample_holding.id, allocation_pct=100.0
        )
        db_session.add(mapping)
        db_session.commit()

        goal_repo = GoalRepository(db_session)
        holding_repo = HoldingRepository(db_session)
        service = GoalService(goal_repo, holding_repo, mock_provider, db_session)

        rng = random.Random(42)
        projection = service.project_goal(
            goal=goal,
            holdings=[sample_holding],
            num_simulations=50,
            rng=rng,
        )
        # With 0 months, all sims return current_value
        assert projection.projected_value_median == pytest.approx(1750.0)
        assert projection.years_to_target == 0.0

    def test_deterministic_with_same_seed(
        self, db_session, sample_goal, sample_holding, sample_goal_mapping, mock_provider
    ):
        """Same RNG seed MUST produce identical projections."""
        goal_repo = GoalRepository(db_session)
        holding_repo = HoldingRepository(db_session)
        service = GoalService(goal_repo, holding_repo, mock_provider, db_session)

        rng1 = random.Random(123)
        proj1 = service.project_goal(
            goal=sample_goal, holdings=[sample_holding], num_simulations=100, rng=rng1
        )

        rng2 = random.Random(123)
        proj2 = service.project_goal(
            goal=sample_goal, holdings=[sample_holding], num_simulations=100, rng=rng2
        )

        assert proj1.projected_value_median == pytest.approx(proj2.projected_value_median)
        assert proj1.probability_of_success == pytest.approx(proj2.probability_of_success)

    def test_percentile_ordering(
        self, db_session, sample_goal, sample_holding, sample_goal_mapping, mock_provider
    ):
        """P10 MUST be <= median MUST be <= P90."""
        goal_repo = GoalRepository(db_session)
        holding_repo = HoldingRepository(db_session)
        service = GoalService(goal_repo, holding_repo, mock_provider, db_session)

        rng = random.Random(42)
        projection = service.project_goal(
            goal=sample_goal, holdings=[sample_holding], num_simulations=200, rng=rng
        )

        assert projection.projected_value_p10 <= projection.projected_value_median
        assert projection.projected_value_median <= projection.projected_value_p90


@pytest.mark.unit
class TestProjectAllGoals:
    """Tests for projecting all goals at once."""

    def test_project_all_goals_returns_all(
        self, db_session, sample_goals, sample_holdings, mock_provider
    ):
        """project_all_goals MUST return a projection for each goal."""
        goal_repo = GoalRepository(db_session)
        # Map first holding to first goal
        goal_repo.add_mapping(sample_goals[0].id, sample_holdings[0].id, 100.0)

        holding_repo = HoldingRepository(db_session)
        service = GoalService(goal_repo, holding_repo, mock_provider, db_session)

        rng = random.Random(42)
        projections = service.project_all_goals(
            holdings=sample_holdings, num_simulations=50, rng=rng
        )

        assert len(projections) == 3
        assert all(p.goal_name for p in projections)

    def test_project_all_goals_empty(
        self, db_session, sample_holdings, mock_provider
    ):
        """project_all_goals MUST return empty list when no goals exist."""
        goal_repo = GoalRepository(db_session)
        holding_repo = HoldingRepository(db_session)
        service = GoalService(goal_repo, holding_repo, mock_provider, db_session)

        projections = service.project_all_goals(holdings=sample_holdings)
        assert projections == []


@pytest.mark.unit
class TestPercentile:
    """Tests for shared Monte Carlo percentile summarization used by goals."""

    def test_median_of_odd_list(self):
        """Median of odd-length sorted list MUST be the middle value."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        summary = summarize_monte_carlo(values, target_amount=0.0)
        assert summary.projected_value_median == pytest.approx(3.0)

    def test_median_of_even_list(self):
        """Median of even-length sorted list MUST be average of middle two."""
        values = [1.0, 2.0, 3.0, 4.0]
        summary = summarize_monte_carlo(values, target_amount=0.0)
        assert summary.projected_value_median == pytest.approx(2.5)

    def test_p10_of_list(self):
        """P10 MUST return the 10th percentile value."""
        values = [float(i) for i in range(1, 11)]  # 1..10
        summary = summarize_monte_carlo(values, target_amount=0.0)
        assert 1.0 <= summary.projected_value_p10 <= 2.0

    def test_empty_list_returns_zero(self):
        """Empty list MUST return 0.0."""
        summary = summarize_monte_carlo([], target_amount=0.0)
        assert summary.projected_value_median == 0.0

    def test_single_element(self):
        """Single element list MUST return that element for any percentile."""
        summary = summarize_monte_carlo([42.0], target_amount=0.0)
        assert summary.projected_value_median == 42.0
        assert summary.projected_value_p10 == 42.0
        assert summary.projected_value_p90 == 42.0


@pytest.mark.unit
class TestSuccessLabel:
    """Tests for the get_success_label method."""

    def test_high_probability_is_on_track(self, db_session, mock_provider):
        """Probability >= 0.80 MUST be labeled 'On Track'."""
        goal_repo = GoalRepository(db_session)
        holding_repo = HoldingRepository(db_session)
        service = GoalService(goal_repo, holding_repo, mock_provider, db_session)

        assert service.get_success_label(0.85) == "On Track"
        assert service.get_success_label(0.80) == "On Track"

    def test_moderate_probability_is_at_risk(self, db_session, mock_provider):
        """Probability 0.30–0.69 MUST be labeled 'At Risk' (except 0.70+)."""
        goal_repo = GoalRepository(db_session)
        holding_repo = HoldingRepository(db_session)
        service = GoalService(goal_repo, holding_repo, mock_provider, db_session)

        assert service.get_success_label(0.50) == "At Risk"
        assert service.get_success_label(0.30) == "At Risk"

    def test_low_probability_is_off_track(self, db_session, mock_provider):
        """Probability < 0.30 MUST be labeled 'Off Track'."""
        goal_repo = GoalRepository(db_session)
        holding_repo = HoldingRepository(db_session)
        service = GoalService(goal_repo, holding_repo, mock_provider, db_session)

        assert service.get_success_label(0.20) == "Off Track"
        assert service.get_success_label(0.0) == "Off Track"

    def test_seventy_percent_is_on_track(self, db_session, mock_provider):
        """Probability >= 0.70 MUST be labeled 'On Track'."""
        goal_repo = GoalRepository(db_session)
        holding_repo = HoldingRepository(db_session)
        service = GoalService(goal_repo, holding_repo, mock_provider, db_session)

        assert service.get_success_label(0.70) == "On Track"
