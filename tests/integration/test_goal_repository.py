"""Integration tests for GoalRepository — CRUD operations for goals and mappings.

Covers: add, get_by_id, get_all, update, delete goals,
and add/get/update/delete goal-holding mappings.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from app.repositories.goal_repository import GoalRepository


@pytest.mark.integration
class TestGoalRepositoryAdd:
    """Tests for adding goals to the repository."""

    def test_add_goal_persists_to_db(self, db_session):
        """Adding a goal MUST persist it to the database."""
        repo = GoalRepository(db_session)
        goal = repo.add(
            name="Retire at 60",
            target_amount=500000.0,
            target_date=datetime(2040, 1, 1),
            monthly_contribution=500.0,
        )
        assert goal.id is not None
        assert goal.name == "Retire at 60"
        assert goal.target_amount == 500000.0
        assert goal.monthly_contribution == 500.0

    def test_add_goal_strips_name(self, db_session):
        """Goal name MUST be stripped of whitespace."""
        repo = GoalRepository(db_session)
        goal = repo.add(
            name="  House Down Payment  ",
            target_amount=100000.0,
            target_date=datetime(2030, 1, 1),
        )
        assert goal.name == "House Down Payment"


@pytest.mark.integration
class TestGoalRepositoryUpdate:
    """Tests for updating goals."""

    def test_update_goal_name(self, db_session, sample_goal):
        """Updating name MUST change the value."""
        repo = GoalRepository(db_session)
        updated = repo.update(sample_goal.id, name="Retire at 65")
        assert updated is not None
        assert updated.name == "Retire at 65"

    def test_update_goal_target_amount(self, db_session, sample_goal):
        """Updating target amount MUST change the value."""
        repo = GoalRepository(db_session)
        updated = repo.update(sample_goal.id, target_amount=750000.0)
        assert updated is not None
        assert updated.target_amount == 750000.0

    def test_update_goal_monthly_contribution(self, db_session, sample_goal):
        """Updating monthly contribution MUST change the value."""
        repo = GoalRepository(db_session)
        updated = repo.update(sample_goal.id, monthly_contribution=1000.0)
        assert updated is not None
        assert updated.monthly_contribution == 1000.0

    def test_update_nonexistent_returns_none(self, db_session):
        """Updating a non-existent goal MUST return None."""
        repo = GoalRepository(db_session)
        result = repo.update(99999, name="Nonexistent")
        assert result is None


@pytest.mark.integration
class TestGoalRepositoryDelete:
    """Tests for deleting goals."""

    def test_delete_goal_removes_from_db(self, db_session, sample_goal):
        """Deleting a goal MUST remove it from the database."""
        repo = GoalRepository(db_session)
        goal_id = sample_goal.id
        result = repo.delete(goal_id)
        assert result is True
        assert repo.get_by_id(goal_id) is None

    def test_delete_nonexistent_returns_false(self, db_session):
        """Deleting a non-existent goal MUST return False."""
        repo = GoalRepository(db_session)
        result = repo.delete(99999)
        assert result is False

    def test_delete_goal_cascades_mappings(
        self, db_session, sample_goal, sample_holding, sample_goal_mapping
    ):
        """Deleting a goal MUST cascade-delete its mappings."""
        repo = GoalRepository(db_session)
        goal_id = sample_goal.id

        # Verify mapping exists
        mappings = repo.get_mappings_for_goal(goal_id)
        assert len(mappings) == 1

        # Delete goal
        repo.delete(goal_id)

        # Mapping should be gone
        mappings_after = repo.get_mappings_for_goal(goal_id)
        assert len(mappings_after) == 0


@pytest.mark.integration
class TestGoalRepositoryQueries:
    """Tests for querying goals."""

    def test_get_by_id_finds_goal(self, db_session, sample_goal):
        """get_by_id MUST find a goal by its primary key."""
        repo = GoalRepository(db_session)
        found = repo.get_by_id(sample_goal.id)
        assert found is not None
        assert found.id == sample_goal.id

    def test_get_all_returns_all_goals_ordered_by_date(
        self, db_session, sample_goals
    ):
        """get_all MUST return all goals ordered by target date."""
        repo = GoalRepository(db_session)
        all_goals = repo.get_all()
        assert len(all_goals) == 3
        dates = [g.target_date for g in all_goals]
        assert dates == sorted(dates)


@pytest.mark.integration
class TestGoalHoldingMapping:
    """Tests for goal-holding mapping CRUD."""

    def test_add_mapping(self, db_session, sample_goal, sample_holding):
        """Adding a mapping MUST persist it."""
        repo = GoalRepository(db_session)
        mapping = repo.add_mapping(sample_goal.id, sample_holding.id, 100.0)
        assert mapping.id is not None
        assert mapping.goal_id == sample_goal.id
        assert mapping.holding_id == sample_holding.id
        assert mapping.allocation_pct == 100.0

    def test_add_mapping_clamps_allocation(self, db_session, sample_goals, sample_holding):
        """Allocation percentage MUST be clamped to 0–100."""
        repo = GoalRepository(db_session)
        mapping_high = repo.add_mapping(sample_goals[0].id, sample_holding.id, 150.0)
        assert mapping_high.allocation_pct == 100.0

        mapping_low = repo.add_mapping(sample_goals[1].id, sample_holding.id, -50.0)
        assert mapping_low.allocation_pct == 0.0

    def test_get_mappings_for_goal(self, db_session, sample_goal, sample_holdings):
        """get_mappings_for_goal MUST return all mappings for a goal."""
        repo = GoalRepository(db_session)
        repo.add_mapping(sample_goal.id, sample_holdings[0].id, 60.0)
        repo.add_mapping(sample_goal.id, sample_holdings[1].id, 40.0)

        mappings = repo.get_mappings_for_goal(sample_goal.id)
        assert len(mappings) == 2

    def test_get_mappings_for_holding(self, db_session, sample_goals, sample_holding):
        """get_mappings_for_holding MUST return all mappings for a holding."""
        repo = GoalRepository(db_session)
        repo.add_mapping(sample_goals[0].id, sample_holding.id, 50.0)
        repo.add_mapping(sample_goals[1].id, sample_holding.id, 50.0)

        mappings = repo.get_mappings_for_holding(sample_holding.id)
        assert len(mappings) == 2

    def test_update_mapping_allocation(self, db_session, sample_goal_mapping):
        """Updating a mapping's allocation MUST change the value."""
        repo = GoalRepository(db_session)
        updated = repo.update_mapping(sample_goal_mapping.id, allocation_pct=75.0)
        assert updated is not None
        assert updated.allocation_pct == 75.0

    def test_update_nonexistent_mapping_returns_none(self, db_session):
        """Updating a non-existent mapping MUST return None."""
        repo = GoalRepository(db_session)
        result = repo.update_mapping(99999, allocation_pct=50.0)
        assert result is None

    def test_delete_mapping(self, db_session, sample_goal_mapping):
        """Deleting a mapping MUST remove it."""
        repo = GoalRepository(db_session)
        mapping_id = sample_goal_mapping.id
        result = repo.delete_mapping(mapping_id)
        assert result is True
        assert repo.delete_mapping(mapping_id) is False

    def test_delete_nonexistent_mapping_returns_false(self, db_session):
        """Deleting a non-existent mapping MUST return False."""
        repo = GoalRepository(db_session)
        result = repo.delete_mapping(99999)
        assert result is False
