"""Recommendation card component — displays a single recommendation."""

from __future__ import annotations

import streamlit as st

from app.services.recommendation_service import Recommendation
from app.utils.currency import format_money


def render_recommendation_card(rec: Recommendation) -> None:
    """Render a single recommendation as a card."""
    trend_icon = {"up": "📈", "down": "📉", "flat": "➡️"}
    icon = trend_icon.get(rec.trend_direction, "❓")

    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            label = f"### {icon} {rec.ticker}"
            if rec.in_portfolio:
                label += " ✅"
            st.markdown(label)
            st.caption(rec.sector)

        with col2:
            st.metric("Current Price", format_money(rec.current_price, rec.currency))

        with col3:
            st.metric("Monthly Change", f"{rec.change_percent:+.2f}%")

        with col4:
            st.metric("Confidence", f"{rec.confidence_score:.0%}")

        st.markdown(f"*{rec.rationale}*")