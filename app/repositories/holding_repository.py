"""Holding repository — CRUD operations for Holding entities.

Implements the Repository pattern to separate persistence logic
from business logic.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.holding import Holding


class HoldingRepository:
    """Repository for managing Holding entities in the database."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository with a database session.

        Args:
            session: SQLAlchemy session for database operations.
        """
        self._session = session

    def add(
        self,
        ticker: str,
        quantity: float,
        purchase_price: float,
        date_acquired: Optional[datetime] = None,
    ) -> Holding:
        """Add a new holding to the database.

        Args:
            ticker: Stock ticker symbol.
            quantity: Number of shares.
            purchase_price: Average purchase price per share.
            date_acquired: Date acquired (defaults to now).

        Returns:
            The created Holding instance.
        """
        holding = Holding(
            ticker=ticker.upper().strip(),
            quantity=quantity,
            purchase_price=purchase_price,
            date_acquired=date_acquired or datetime.utcnow(),
        )
        self._session.add(holding)
        self._session.commit()
        self._session.refresh(holding)
        return holding

    def get_by_id(self, holding_id: int) -> Optional[Holding]:
        """Retrieve a holding by its primary key.

        Args:
            holding_id: The holding's primary key.

        Returns:
            Holding if found, None otherwise.
        """
        return self._session.get(Holding, holding_id)

    def get_by_ticker(self, ticker: str) -> Optional[Holding]:
        """Retrieve a holding by its ticker symbol.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Holding if found, None otherwise.
        """
        return (
            self._session.query(Holding)
            .filter(Holding.ticker == ticker.upper().strip())
            .first()
        )

    def get_all(self) -> list[Holding]:
        """Retrieve all holdings ordered by ticker.

        Returns:
            List of all Holding instances.
        """
        return self._session.query(Holding).order_by(Holding.ticker).all()

    def update(
        self,
        holding_id: int,
        quantity: Optional[float] = None,
        purchase_price: Optional[float] = None,
    ) -> Optional[Holding]:
        """Update a holding's quantity and/or purchase price.

        Args:
            holding_id: The holding's primary key.
            quantity: New quantity (if provided).
            purchase_price: New purchase price (if provided).

        Returns:
            Updated Holding if found, None otherwise.
        """
        holding = self.get_by_id(holding_id)
        if holding is None:
            return None

        if quantity is not None:
            holding.quantity = quantity
        if purchase_price is not None:
            holding.purchase_price = purchase_price

        holding.updated_at = datetime.utcnow()
        self._session.commit()
        self._session.refresh(holding)
        return holding

    def delete(self, holding_id: int) -> bool:
        """Delete a holding by its primary key.

        Args:
            holding_id: The holding's primary key.

        Returns:
            True if deleted, False if not found.
        """
        holding = self.get_by_id(holding_id)
        if holding is None:
            return False

        self._session.delete(holding)
        self._session.commit()
        return True

    def get_all_tickers(self) -> list[str]:
        """Return all unique ticker symbols in the portfolio.

        Returns:
            List of ticker strings.
        """
        holdings = self.get_all()
        return [h.ticker for h in holdings]