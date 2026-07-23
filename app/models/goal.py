"""Goal ORM model — represents an investment goal (retirement, house, tuition)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Goal(Base):
    """A user-defined investment goal.

    Attributes:
        id: Primary key.
        name: Human-readable goal name (e.g., "Retire at 60", "House in 7 years").
        target_amount: The amount of money needed to achieve the goal.
        target_date: The date by which the goal should be reached.
        monthly_contribution: Optional recurring monthly contribution toward the goal.
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
    """

    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    target_amount: Mapped[float] = mapped_column(Float, nullable=False)
    target_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    monthly_contribution: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Goal(name={self.name!r}, target={self.target_amount}, date={self.target_date})>"
