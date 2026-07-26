"""FourFundPlan ORM model — persisted saved allocations for the four-fund builder."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FourFundPlan(Base):
    """A saved four-fund portfolio configuration.

    Stores selected tickers and allocation weights so users can save,
    reload, and run simulations on consistent portfolio setups.
    """

    __tablename__ = "four_fund_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    eu_ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    developed_ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    emerging_ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    bonds_ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    eu_weight: Mapped[float] = mapped_column(Float, nullable=False)
    developed_weight: Mapped[float] = mapped_column(Float, nullable=False)
    emerging_weight: Mapped[float] = mapped_column(Float, nullable=False)
    bonds_weight: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<FourFundPlan(name={self.name!r})>"
