"""Price repository — CRUD operations for PricePoint entities.

Handles caching and retrieval of historical price data.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.price_point import PricePoint
from app.providers.base import PriceHistory


class PriceRepository:
    """Repository for managing PricePoint entities in the database."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository with a database session.

        Args:
            session: SQLAlchemy session for database operations.
        """
        self._session = session

    def save_price_points(self, history: PriceHistory) -> int:
        """Save price history data points to the database.

        Args:
            history: PriceHistory object from a market data provider.

        Returns:
            Number of price points saved.
        """
        count = 0
        for i, date in enumerate(history.dates):
            point = PricePoint(
                ticker=history.ticker,
                date=date,
                open=history.opens[i],
                high=history.highs[i],
                low=history.lows[i],
                close=history.closes[i],
                volume=history.volumes[i],
                fetched_at=datetime.utcnow(),
            )
            self._session.add(point)
            count += 1

        self._session.commit()
        return count

    def get_history_by_ticker(
        self, ticker: str, days: int = 30
    ) -> list[PricePoint]:
        """Retrieve price history for a ticker within a date range.

        Args:
            ticker: Stock ticker symbol.
            days: Number of days of history to retrieve.

        Returns:
            List of PricePoint instances ordered by date ascending.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        return (
            self._session.query(PricePoint)
            .filter(PricePoint.ticker == ticker.upper().strip())
            .filter(PricePoint.date >= cutoff)
            .order_by(PricePoint.date.asc())
            .all()
        )

    def get_latest_price(self, ticker: str) -> Optional[PricePoint]:
        """Retrieve the most recent price point for a ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Latest PricePoint if available, None otherwise.
        """
        return (
            self._session.query(PricePoint)
            .filter(PricePoint.ticker == ticker.upper().strip())
            .order_by(desc(PricePoint.date))
            .first()
        )

    def get_last_fetch_time(self, ticker: str) -> Optional[datetime]:
        """Retrieve the timestamp of the last price fetch for a ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Datetime of last fetch if available, None otherwise.
        """
        latest = self.get_latest_price(ticker)
        return latest.fetched_at if latest else None

    def get_all_latest_prices(self) -> dict[str, PricePoint]:
        """Retrieve the latest price point for each ticker in the database.

        Returns:
            Dictionary mapping ticker to its latest PricePoint.
        """
        all_points = self._session.query(PricePoint).all()
        latest_map: dict[str, PricePoint] = {}
        for point in all_points:
            existing = latest_map.get(point.ticker)
            if existing is None or point.date > existing.date:
                latest_map[point.ticker] = point
        return latest_map