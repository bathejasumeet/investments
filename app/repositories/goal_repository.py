"""Goal repository — CRUD operations for Goal and GoalHoldingMapping entities.

Implements the Repository pattern to separate persistence logic
from business logic, consistent with HoldingRepository.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.models.goal_holding_mapping import GoalHoldingMapping


class GoalRepository:
    """Repository for managing Goal entities in the database."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository with a database session.

        Args:
            session: SQLAlchemy session for database operations.
        """
        self._session = session

    # --- Goal CRUD ---

    def add(
        self,
        name: str,
        target_amount: float,
        target_date: datetime,
        monthly_contribution: float = 0.0,
    ) -> Goal:
        """Add a new goal to the database.

        Args:
            name: Human-readable goal name.
            target_amount: The amount of money needed.
            target_date: The date by which the goal should be reached.
            monthly_contribution: Optional recurring monthly contribution.

        Returns:
            The created Goal instance.
        """
        goal = Goal(
            name=name.strip(),
            target_amount=target_amount,
            target_date=target_date,
            monthly_contribution=monthly_contribution,
        )
        self._session.add(goal)
        self._session.commit()
        self._session.refresh(goal)
        return goal

    def get_by_id(self, goal_id: int) -> Goal | None:
        """Retrieve a goal by its primary key.

        Args:
            goal_id: The goal's primary key.

        Returns:
            Goal if found, None otherwise.
        """
        return self._session.get(Goal, goal_id)

    def get_all(self) -> list[Goal]:
        """Retrieve all goals ordered by target date.

        Returns:
            List of all Goal instances.
        """
        return self._session.query(Goal).order_by(Goal.target_date).all()

    def update(
        self,
        goal_id: int,
        name: str | None = None,
        target_amount: float | None = None,
        target_date: datetime | None = None,
        monthly_contribution: float | None = None,
    ) -> Goal | None:
        """Update a goal's fields.

        Args:
            goal_id: The goal's primary key.
            name: New name (if provided).
            target_amount: New target amount (if provided).
            target_date: New target date (if provided).
            monthly_contribution: New monthly contribution (if provided).

        Returns:
            Updated Goal if found, None otherwise.
        """
        goal = self.get_by_id(goal_id)
        if goal is None:
            return None

        if name is not None:
            goal.name = name.strip()
        if target_amount is not None:
            goal.target_amount = target_amount
        if target_date is not None:
            goal.target_date = target_date
        if monthly_contribution is not None:
            goal.monthly_contribution = monthly_contribution

        goal.updated_at = datetime.utcnow()
        self._session.commit()
        self._session.refresh(goal)
        return goal

    def delete(self, goal_id: int) -> bool:
        """Delete a goal by its primary key.

        Explicitly removes all associated GoalHoldingMapping rows first,
        since SQLite does not enforce FK cascade deletes by default.

        Args:
            goal_id: The goal's primary key.

        Returns:
            True if deleted, False if not found.
        """
        goal = self.get_by_id(goal_id)
        if goal is None:
            return False

        # Explicitly delete mappings (SQLite doesn't enforce FK cascade)
        mappings = self.get_mappings_for_goal(goal_id)
        for mapping in mappings:
            self._session.delete(mapping)

        self._session.delete(goal)
        self._session.commit()
        return True

    # --- GoalHoldingMapping CRUD ---

    def add_mapping(
        self, goal_id: int, holding_id: int, allocation_pct: float = 100.0
    ) -> GoalHoldingMapping:
        """Map a holding to a goal with an allocation percentage.

        Args:
            goal_id: The goal's primary key.
            holding_id: The holding's primary key.
            allocation_pct: Percentage of the holding allocated to this goal (0–100).

        Returns:
            The created GoalHoldingMapping instance.
        """
        mapping = GoalHoldingMapping(
            goal_id=goal_id,
            holding_id=holding_id,
            allocation_pct=max(0.0, min(100.0, allocation_pct)),
        )
        self._session.add(mapping)
        self._session.commit()
        self._session.refresh(mapping)
        return mapping

    def get_mappings_for_goal(self, goal_id: int) -> list[GoalHoldingMapping]:
        """Retrieve all holding mappings for a given goal.

        Args:
            goal_id: The goal's primary key.

        Returns:
            List of GoalHoldingMapping instances for the goal.
        """
        return (
            self._session.query(GoalHoldingMapping)
            .filter(GoalHoldingMapping.goal_id == goal_id)
            .all()
        )

    def get_mappings_for_holding(self, holding_id: int) -> list[GoalHoldingMapping]:
        """Retrieve all goal mappings for a given holding.

        Args:
            holding_id: The holding's primary key.

        Returns:
            List of GoalHoldingMapping instances for the holding.
        """
        return (
            self._session.query(GoalHoldingMapping)
            .filter(GoalHoldingMapping.holding_id == holding_id)
            .all()
        )

    def update_mapping(
        self, mapping_id: int, allocation_pct: float | None = None
    ) -> GoalHoldingMapping | None:
        """Update a goal-holding mapping's allocation percentage.

        Args:
            mapping_id: The mapping's primary key.
            allocation_pct: New allocation percentage (if provided).

        Returns:
            Updated GoalHoldingMapping if found, None otherwise.
        """
        mapping = self._session.get(GoalHoldingMapping, mapping_id)
        if mapping is None:
            return None

        if allocation_pct is not None:
            mapping.allocation_pct = max(0.0, min(100.0, allocation_pct))

        mapping.updated_at = datetime.utcnow()
        self._session.commit()
        self._session.refresh(mapping)
        return mapping

    def delete_mapping(self, mapping_id: int) -> bool:
        """Delete a goal-holding mapping.

        Args:
            mapping_id: The mapping's primary key.

        Returns:
            True if deleted, False if not found.
        """
        mapping = self._session.get(GoalHoldingMapping, mapping_id)
        if mapping is None:
            return False

        self._session.delete(mapping)
        self._session.commit()
        return True
