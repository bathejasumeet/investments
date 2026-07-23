"""GoalHoldingMapping ORM model — links a Holding to a Goal with an allocation %."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GoalHoldingMapping(Base):
    """Maps a Holding to a Goal with a percentage allocation.

    A holding can be shared across multiple goals. The allocation_pct
    represents what fraction of the holding's value is earmarked for
    a particular goal (0–100).

    Attributes:
        id: Primary key.
        goal_id: Foreign key to goals table.
        holding_id: Foreign key to holdings table.
        allocation_pct: Percentage of the holding allocated to this goal (0–100).
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
    """

    __tablename__ = "goal_holding_mappings"
    __table_args__ = (
        UniqueConstraint("goal_id", "holding_id", name="uq_goal_holding"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    goal_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    holding_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("holdings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    allocation_pct: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return (
            f"<GoalHoldingMapping(goal_id={self.goal_id}, "
            f"holding_id={self.holding_id}, pct={self.allocation_pct})>"
        )
