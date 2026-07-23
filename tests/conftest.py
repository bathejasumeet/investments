"""Shared test fixtures for pytest.

Provides in-memory SQLite engine, session fixtures, mock market data
provider, and sample holding factory for testing.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Generator
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models.holding import Holding
from app.models.price_point import PricePoint
from app.providers.base import (
    MarketDataProvider,
    PriceHistory,
    PriceQuote,
    TrendData,
)


@pytest.fixture
def db_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create a new database session for a test."""
    SessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_holding_data():
    """Return sample holding data for tests."""
    return {
        "ticker": "AAPL",
        "quantity": 10.0,
        "purchase_price": 150.00,
        "date_acquired": datetime(2024, 1, 15),
    }


@pytest.fixture
def sample_holding(db_session) -> Holding:
    """Create and return a sample holding in the database."""
    holding = Holding(
        ticker="AAPL",
        quantity=10.0,
        purchase_price=150.00,
        date_acquired=datetime(2024, 1, 15),
    )
    db_session.add(holding)
    db_session.commit()
    db_session.refresh(holding)
    return holding


@pytest.fixture
def sample_holdings(db_session) -> list[Holding]:
    """Create and return multiple sample holdings."""
    holdings = [
        Holding(
            ticker="AAPL",
            quantity=10.0,
            purchase_price=150.00,
            date_acquired=datetime(2024, 1, 15),
        ),
        Holding(
            ticker="MSFT",
            quantity=5.0,
            purchase_price=300.00,
            date_acquired=datetime(2024, 2, 1),
        ),
        Holding(
            ticker="GOOGL",
            quantity=8.0,
            purchase_price=140.00,
            date_acquired=datetime(2024, 3, 10),
        ),
    ]
    for h in holdings:
        db_session.add(h)
    db_session.commit()
    for h in holdings:
        db_session.refresh(h)
    return holdings


@pytest.fixture
def sample_price_points(db_session) -> list[PricePoint]:
    """Create and return sample price points for testing."""
    base_date = datetime(2024, 6, 1)
    points = []
    for i in range(5):
        point = PricePoint(
            ticker="AAPL",
            date=base_date + timedelta(days=i),
            open=170.0 + i,
            high=175.0 + i,
            low=168.0 + i,
            close=172.0 + i,
            volume=50000000 + i * 1000000,
            fetched_at=datetime.utcnow(),
        )
        points.append(point)
        db_session.add(point)
    db_session.commit()
    return points


@pytest.fixture
def mock_provider() -> MarketDataProvider:
    """Return a mock market data provider for testing."""
    provider = MagicMock(spec=MarketDataProvider)

    # Default: valid ticker returns a price quote
    provider.validate_ticker.return_value = True
    provider.get_current_price.return_value = PriceQuote(
        ticker="AAPL",
        price=175.00,
        currency="EUR",
        timestamp=datetime.utcnow(),
    )
    provider.get_current_prices.return_value = {
        "AAPL": PriceQuote(
            ticker="AAPL",
            price=175.00,
            currency="EUR",
            timestamp=datetime.utcnow(),
        )
    }
    provider.get_exchange_rate.return_value = type(
        "ExchangeRate",
        (),
        {"rate": 1.0},
    )()
    provider.get_price_history.return_value = PriceHistory(
        ticker="AAPL",
        dates=[datetime(2024, 6, 1) + timedelta(days=i) for i in range(5)],
        opens=[170.0, 171.0, 172.0, 173.0, 174.0],
        highs=[175.0, 176.0, 177.0, 178.0, 179.0],
        lows=[168.0, 169.0, 170.0, 171.0, 172.0],
        closes=[172.0, 173.0, 174.0, 175.0, 176.0],
        volumes=[50000000, 51000000, 52000000, 53000000, 54000000],
    )
    provider.get_trend_data.return_value = TrendData(
        ticker="AAPL",
        trend_direction="up",
        change_percent=5.2,
        sector="Technology",
        confidence_score=0.85,
    )
    provider.get_top_gainers.return_value = [
        TrendData(
            ticker="NVDA",
            trend_direction="up",
            change_percent=12.5,
            sector="Technology",
            confidence_score=0.95,
        ),
        TrendData(
            ticker="AAPL",
            trend_direction="up",
            change_percent=5.2,
            sector="Technology",
            confidence_score=0.85,
        ),
    ]

    return provider