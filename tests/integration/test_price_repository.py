"""Integration tests for PriceRepository — TDD tests written FIRST."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.providers.base import PriceHistory
from app.repositories.price_repository import PriceRepository


@pytest.mark.integration
class TestPriceRepository:
    """Tests for price repository operations."""

    def test_get_history_by_ticker_returns_chronological(self, db_session, sample_price_points):
        """get_history_by_ticker MUST return points in chronological order."""
        repo = PriceRepository(db_session)
        history = repo.get_history_by_ticker("AAPL", days=10000)
        assert len(history) == 5
        dates = [p.date for p in history]
        assert dates == sorted(dates)

    def test_get_latest_price_returns_most_recent(self, db_session, sample_price_points):
        """get_latest_price MUST return the most recent price point."""
        repo = PriceRepository(db_session)
        latest = repo.get_latest_price("AAPL")
        assert latest is not None
        assert latest.close == 176.0  # Last point in sample data

    def test_get_latest_price_nonexistent_returns_none(self, db_session):
        """get_latest_price for non-existent ticker MUST return None."""
        repo = PriceRepository(db_session)
        result = repo.get_latest_price("NONEXIST")
        assert result is None

    def test_save_price_points_persists_data(self, db_session):
        """save_price_points MUST persist all points to the database."""
        repo = PriceRepository(db_session)
        history = PriceHistory(
            ticker="MSFT",
            dates=[datetime(2024, 6, 1) + timedelta(days=i) for i in range(3)],
            opens=[380.0, 381.0, 382.0],
            highs=[385.0, 386.0, 387.0],
            lows=[378.0, 379.0, 380.0],
            closes=[382.0, 383.0, 384.0],
            volumes=[1000000, 1100000, 1200000],
        )
        count = repo.save_price_points(history)
        assert count == 3
        saved = repo.get_history_by_ticker("MSFT", days=10000)
        assert len(saved) == 3

    def test_save_price_points_upserts_existing_ticker_dates(self, db_session):
        """Refreshing an unchanged history MUST not create duplicate cache rows."""
        repo = PriceRepository(db_session)
        history = PriceHistory(
            ticker="MSFT",
            dates=[datetime(2024, 6, 1) + timedelta(days=index) for index in range(3)],
            opens=[380.0, 381.0, 382.0],
            highs=[385.0, 386.0, 387.0],
            lows=[378.0, 379.0, 380.0],
            closes=[382.0, 383.0, 384.0],
            volumes=[1000000, 1100000, 1200000],
        )

        assert repo.save_price_points(history) == 3
        assert repo.save_price_points(history) == 0

        saved = repo.get_history_by_ticker("MSFT", days=10000)
        assert len(saved) == 3
