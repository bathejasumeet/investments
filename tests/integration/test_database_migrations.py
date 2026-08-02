"""Integration tests for application database migrations."""

from __future__ import annotations

from sqlalchemy import create_engine, inspect, text

from app.database import upgrade_database


def test_upgrade_database_creates_current_schema(tmp_path) -> None:
    """A fresh database MUST upgrade to the latest application schema."""
    database_url = f"sqlite:///{tmp_path / 'portfolio.db'}"

    upgrade_database(database_url)

    engine = create_engine(database_url)
    inspector = inspect(engine)
    assert {"holdings", "price_points", "goals", "goal_holding_mappings", "four_fund_plans"} <= set(
        inspector.get_table_names()
    )
    assert any(
        index["name"] == "uq_price_points_ticker_date"
        for index in inspector.get_indexes("price_points")
    )


def test_upgrade_database_migrates_legacy_price_cache(tmp_path) -> None:
    """An unversioned price cache MUST be deduplicated before indexing."""
    database_url = f"sqlite:///{tmp_path / 'legacy.db'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE price_points ("
                "id INTEGER PRIMARY KEY, ticker VARCHAR(10) NOT NULL, "
                "date DATETIME NOT NULL, open FLOAT NOT NULL, high FLOAT NOT NULL, "
                "low FLOAT NOT NULL, close FLOAT NOT NULL, volume INTEGER, "
                "fetched_at DATETIME NOT NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO price_points "
                "(ticker, date, open, high, low, close, volume, fetched_at) VALUES "
                "('MSFT', '2024-06-01', 380, 385, 378, 382, 1000000, '2024-06-01'), "
                "('MSFT', '2024-06-01', 380, 385, 378, 382, 1000000, '2024-06-02')"
            )
        )

    upgrade_database(database_url)

    with engine.connect() as connection:
        assert connection.scalar(text("SELECT COUNT(*) FROM price_points")) == 1
    assert any(
        index["name"] == "uq_price_points_ticker_date"
        for index in inspect(engine).get_indexes("price_points")
    )
