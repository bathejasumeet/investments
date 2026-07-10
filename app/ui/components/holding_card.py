"""Holding card component — displays a single holding with metrics.

Reusable UI component for rendering a holding with current price,
value, and gain/loss with color coding.
"""

from __future__ import annotations

import streamlit as st

from app.services.portfolio_service import HoldingSummary


def render_holding_card(summary: HoldingSummary) -> None:
    """Render a single holding as a card with metrics.

    Args:
        summary: HoldingSummary with calculated values.
    """
    gain_color = "green" if summary.absolute_gain >= 0 else "red"
    gain_icon = "📈" if summary.absolute_gain >= 0 else "📉"

    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(f"### {summary.ticker}")
            st.caption(f"Qty: {summary.quantity:.2f} shares")

        with col2:
            st.metric(
                label="Current Price",
                value=f"${summary.current_price:.2f}",
            )

        with col3:
            st.metric(
                label="Total Value",
                value=f"${summary.current_value:.2f}",
            )

        with col4:
            st.metric(
                label=f"{gain_icon} Gain/Loss",
                value=f"${summary.absolute_gain:+.2f}",
                delta=f"{summary.percentage_gain:+.2f}%",
                delta_color="normal" if summary.absolute_gain >= 0 else "inverse",
            )