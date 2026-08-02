"""Alembic environment configuration for the local SQLite database."""

from __future__ import annotations

import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.database import Base
from app.models.four_fund_plan import FourFundPlan  # noqa: F401
from app.models.goal import Goal  # noqa: F401
from app.models.goal_holding_mapping import GoalHoldingMapping  # noqa: F401
from app.models.holding import Holding  # noqa: F401
from app.models.price_point import PricePoint  # noqa: F401

config = context.config
if database_path := os.getenv("DB_PATH"):
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without creating an Engine."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against the configured database."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"check_same_thread": False},
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
