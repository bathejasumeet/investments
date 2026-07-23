"""Holding card component — displays a single holding with metrics."""

from __future__ import annotations

import streamlit as st

from app.services.portfolio_service import HoldingSummary
from app.utils.currency import format_money


def render_holding_card(summary: HoldingSummary) -> None:
    """Render a single holding as a card with metrics."""
    gain_icon = "📈" if summary.absolute_gain >= 0 else "📉"

    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(f"### {summary.ticker}")
            st.caption(f"Qty: {summary.quantity:.2f} shares")

        with col2:
            st.metric(
                label="Current Price",
                value=format_money(summary.current_price, summary.currency),
            )

        with col3:
            st.metric(
                label="Total Value",
                value=format_money(summary.current_value, summary.currency),
            )

        with col4:
            st.metric(
                label=f"{gain_icon} Gain/Loss",
                value=format_money(summary.absolute_gain, summary.currency),
                delta=f"{summary.percentage_gain:+.2f}%",
                delta_color="normal" if summary.absolute_gain >= 0 else "inverse",
            )