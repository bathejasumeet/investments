"""Integration tests for HoldingRepository — TDD tests written FIRST.

Tests MUST FAIL before implementation (Red-Green-Refactor).
Covers: add, update, delete, get_by_id, get_by_ticker, get_all.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from app.repositories.holding_repository import HoldingRepository


@pytest.mark.integration
class TestHoldingRepositoryAdd:
    """Tests for adding holdings to the repository."""

    def test_add_holding_persists_to_db(self, db_session):
        """Adding a holding MUST persist it to the database."""
        repo = HoldingRepository(db_session)
        holding = repo.add(
            ticker="AAPL",
            quantity=10.0,
            purchase_price=150.00,
        )
        assert holding.id is not None
        assert holding.ticker == "AAPL"
        assert holding.quantity == 10.0
        assert holding.purchase_price == 150.00

    def test_add_holding_uppercases_ticker(self, db_session):
        """Ticker MUST be uppercased and stripped before saving."""
        repo = HoldingRepository(db_session)
        holding = repo.add(
            ticker=" aapl ",
            quantity=5.0,
            purchase_price=100.00,
        )
        assert holding.ticker == "AAPL"


@pytest.mark.integration
class TestHoldingRepositoryUpdate:
    """Tests for updating holdings."""

    def test_update_holding_quantity(self, db_session, sample_holding):
        """Updating quantity MUST change the value in the database."""
        repo = HoldingRepository(db_session)
        updated = repo.update(sample_holding.id, quantity=20.0)
        assert updated is not None
        assert updated.quantity == 20.0
        assert updated.purchase_price == sample_holding.purchase_price

    def test_update_holding_price(self, db_session, sample_holding):
        """Updating purchase price MUST change the value."""
        repo = HoldingRepository(db_session)
        updated = repo.update(sample_holding.id, purchase_price=160.00)
        assert updated is not None
        assert updated.purchase_price == 160.00

    def test_update_nonexistent_returns_none(self, db_session):
        """Updating a non-existent holding MUST return None."""
        repo = HoldingRepository(db_session)
        result = repo.update(99999, quantity=10.0)
        assert result is None


@pytest.mark.integration
class TestHoldingRepositoryDelete:
    """Tests for deleting holdings."""

    def test_delete_holding_removes_from_db(self, db_session, sample_holding):
        """Deleting a holding MUST remove it from the database."""
        repo = HoldingRepository(db_session)
        holding_id = sample_holding.id
        result = repo.delete(holding_id)
        assert result is True
        assert repo.get_by_id(holding_id) is None

    def test_delete_nonexistent_returns_false(self, db_session):
        """Deleting a non-existent holding MUST return False."""
        repo = HoldingRepository(db_session)
        result = repo.delete(99999)
        assert result is False


@pytest.mark.integration
class TestHoldingRepositoryQueries:
    """Tests for querying holdings."""

    def test_get_by_ticker_finds_holding(self, db_session, sample_holding):
        """get_by_ticker MUST find a holding by its ticker symbol."""
        repo = HoldingRepository(db_session)
        found = repo.get_by_ticker("AAPL")
        assert found is not None
        assert found.id == sample_holding.id

    def test_get_all_returns_all_holdings(self, db_session, sample_holdings):
        """get_all MUST return all holdings ordered by ticker."""
        repo = HoldingRepository(db_session)
        all_holdings = repo.get_all()
        assert len(all_holdings) == 3
        tickers = [h.ticker for h in all_holdings]
        assert tickers == sorted(tickers)

    def test_get_all_tickers_returns_ticker_list(self, db_session, sample_holdings):
        """get_all_tickers MUST return list of all ticker symbols."""
        repo = HoldingRepository(db_session)
        tickers = repo.get_all_tickers()
        assert set(tickers) == {"AAPL", "MSFT", "GOOGL"}