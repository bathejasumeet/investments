"""Database engine, session factory, and declarative base for SQLAlchemy."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


def _get_db_path() -> str:
    """Resolve the SQLite database path from environment or default."""
    db_path = os.getenv("DB_PATH", "data/portfolio.db")
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


def _create_engine() -> object:
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


def init_db() -> None:
    """Create all tables in the database."""
    # Import ORM models so SQLAlchemy registers their tables on Base metadata.
    from app.models.four_fund_plan import FourFundPlan  # noqa: F401
    from app.models.goal import Goal  # noqa: F401
    from app.models.goal_holding_mapping import GoalHoldingMapping  # noqa: F401
    from app.models.holding import Holding  # noqa: F401
    from app.models.price_point import PricePoint  # noqa: F401

    Base.metadata.create_all(bind=engine)