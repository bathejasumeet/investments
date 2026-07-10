"""Holding ORM model — represents a single investment position."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Holding(Base):
    """A single investment holding in the portfolio.

    Attributes:
        id: Primary key.
        ticker: Stock ticker symbol (e.g., AAPL, MSFT).
        quantity: Number of shares held.
        purchase_price: Average purchase price per share.
        date_acquired: Date the holding was acquired.
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
    """

    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True, unique=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    purchase_price: Mapped[float] = mapped_column(Float, nullable=False)
    date_acquired: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Holding(ticker={self.ticker!r}, quantity={self.quantity}, price={self.purchase_price})>"