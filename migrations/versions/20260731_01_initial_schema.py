"""Create the initial application schema.

Revision ID: 20260731_01
Revises:
Create Date: 2026-07-31
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260731_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the tables used by the initial application release."""
    op.create_table(
        "holdings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticker", sa.String(length=10), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("purchase_price", sa.Float(), nullable=False),
        sa.Column("date_acquired", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker"),
    )
    op.create_index("ix_holdings_ticker", "holdings", ["ticker"], unique=False)

    op.create_table(
        "price_points",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticker", sa.String(length=10), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Integer(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_price_points_ticker", "price_points", ["ticker"], unique=False)
    op.create_index("ix_price_points_date", "price_points", ["date"], unique=False)

    op.create_table(
        "goals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("target_amount", sa.Float(), nullable=False),
        sa.Column("target_date", sa.DateTime(), nullable=False),
        sa.Column("monthly_contribution", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "goal_holding_mappings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("goal_id", sa.Integer(), nullable=False),
        sa.Column("holding_id", sa.Integer(), nullable=False),
        sa.Column("allocation_pct", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["holding_id"], ["holdings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("goal_id", "holding_id", name="uq_goal_holding"),
    )
    op.create_index(
        "ix_goal_holding_mappings_goal_id",
        "goal_holding_mappings",
        ["goal_id"],
        unique=False,
    )
    op.create_index(
        "ix_goal_holding_mappings_holding_id",
        "goal_holding_mappings",
        ["holding_id"],
        unique=False,
    )

    op.create_table(
        "four_fund_plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("eu_ticker", sa.String(length=20), nullable=False),
        sa.Column("developed_ticker", sa.String(length=20), nullable=False),
        sa.Column("emerging_ticker", sa.String(length=20), nullable=False),
        sa.Column("bonds_ticker", sa.String(length=20), nullable=False),
        sa.Column("eu_weight", sa.Float(), nullable=False),
        sa.Column("developed_weight", sa.Float(), nullable=False),
        sa.Column("emerging_weight", sa.Float(), nullable=False),
        sa.Column("bonds_weight", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_four_fund_plans_name", "four_fund_plans", ["name"], unique=False)


def downgrade() -> None:
    """Drop the initial application schema."""
    op.drop_index("ix_four_fund_plans_name", table_name="four_fund_plans")
    op.drop_table("four_fund_plans")
    op.drop_index("ix_goal_holding_mappings_holding_id", table_name="goal_holding_mappings")
    op.drop_index("ix_goal_holding_mappings_goal_id", table_name="goal_holding_mappings")
    op.drop_table("goal_holding_mappings")
    op.drop_table("goals")
    op.drop_index("ix_price_points_date", table_name="price_points")
    op.drop_index("ix_price_points_ticker", table_name="price_points")
    op.drop_table("price_points")
    op.drop_index("ix_holdings_ticker", table_name="holdings")
    op.drop_table("holdings")
