"""PricePoint ORM model — a timestamped price record for a ticker symbol."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PricePoint(Base):
    """A single price data point for a ticker symbol.

    Attributes:
        id: Primary key.
        ticker: Stock ticker symbol.
        date: Trading date for this price point.
        open: Opening price.
        high: Highest price during the period.
        low: Lowest price during the period.
        close: Closing price.
        volume: Trading volume.
        fetched_at: Timestamp when this record was fetched from the API.
    """

    __tablename__ = "price_points"
    __table_args__ = (Index("uq_price_points_ticker_date", "ticker", "date", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<PricePoint(ticker={self.ticker!r}, date={self.date}, close={self.close})>"
