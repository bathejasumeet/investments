"""Database engine, session factory, and declarative base for SQLAlchemy."""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

_BASELINE_REVISION = "20260731_01"
_APPLICATION_TABLES = {
    "four_fund_plans",
    "goal_holding_mappings",
    "goals",
    "holdings",
    "price_points",
}


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


def _get_db_path() -> str:
    """Resolve the SQLite database path from environment or default."""
    db_path = os.getenv("DB_PATH", "data/portfolio.db")
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


def _create_engine() -> Engine:
    """Create and return a SQLAlchemy engine."""
    engine = create_engine(
        _get_db_path(),
        echo=False,
        connect_args={"check_same_thread": False},
    )
    return engine


engine = _create_engine()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_session() -> Session:
    """Return a new database session."""
    return SessionLocal()


def upgrade_database(database_url: str | None = None) -> None:
    """Upgrade a new or legacy application database to the latest revision."""
    url = database_url or _get_db_path()
    migration_config = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    migration_config.set_main_option("sqlalchemy.url", url)

    migration_engine = create_engine(url, connect_args={"check_same_thread": False})
    try:
        table_names = set(inspect(migration_engine).get_table_names())
        is_legacy_database = "alembic_version" not in table_names and bool(
            table_names & _APPLICATION_TABLES
        )
        if is_legacy_database:
            command.stamp(migration_config, _BASELINE_REVISION)
        command.upgrade(migration_config, "head")
    finally:
        migration_engine.dispose()


def init_db() -> None:
    """Upgrade the local database schema to the latest revision."""
    upgrade_database()
