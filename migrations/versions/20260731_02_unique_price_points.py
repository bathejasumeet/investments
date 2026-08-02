"""Enforce one cached price point for each ticker and timestamp.

Revision ID: 20260731_02
Revises: 20260731_01
Create Date: 2026-07-31
"""

from __future__ import annotations

from alembic import op


revision = "20260731_02"
down_revision = "20260731_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Deduplicate legacy rows before creating the unique cache index."""
    op.execute(
        "DELETE FROM price_points "
        "WHERE id NOT IN ("
        "SELECT MIN(id) FROM price_points GROUP BY ticker, date"
        ")"
    )
    op.create_index(
        "uq_price_points_ticker_date",
        "price_points",
        ["ticker", "date"],
        unique=True,
    )


def downgrade() -> None:
    """Remove the unique cache index."""
    op.drop_index("uq_price_points_ticker_date", table_name="price_points")
