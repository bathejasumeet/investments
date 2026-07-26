"""Recommendation card component — displays a single recommendation.

Renders the recommendation header (ticker, price, change, confidence)
followed by an **explainable factor breakdown** showing each factor's
score, weight, and human-readable explanation so users understand
*why* a ticker was recommended.
"""

from __future__ import annotations

import streamlit as st

from app.services.recommendation_service import (
    FactorBreakdown,
    FactorScore,
    Recommendation,
)
from app.utils.currency import format_money

# Factor display icons (color is NOT the sole signal — icons + text too)
_FACTOR_ICONS = {
    "Momentum": "🚀",
    "Valuation": "💰",
    "Volatility": "📊",
    "Volume": "📈",
    "Concentration": "🎯",
}


def render_recommendation_card(rec: Recommendation) -> None:
    """Render a single recommendation as a card with factor breakdown."""
    trend_icon = {"up": "📈", "down": "📉", "flat": "➡️"}
    icon = trend_icon.get(rec.trend_direction, "❓")

    with st.container(border=True):
        _render_header(rec, icon)
        _render_metrics(rec)
        st.markdown(f"*{rec.rationale}*")

        if rec.factors is not None:
            _render_factor_breakdown(rec.factors)


def _render_header(rec: Recommendation, icon: str) -> None:
    """Render the ticker header row."""
    label = f"### {icon} {rec.ticker}"
    if rec.in_portfolio:
        label += " ✅"
    st.markdown(label)
    st.caption(rec.sector)


def _render_metrics(rec: Recommendation) -> None:
    """Render the key metrics row."""
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current Price", format_money(rec.current_price, rec.currency))
    with col2:
        st.metric("Monthly Change", f"{rec.change_percent:+.2f}%")
    with col3:
        st.metric(
            "Confidence",
            f"{rec.confidence_score:.0%}",
            help=(
                "A weighted score (0–100%) combining the 5 factors below — not a "
                "statistical probability like the Goal Planner's Monte Carlo simulation."
            ),
        )


def _render_factor_breakdown(factors: FactorBreakdown) -> None:
    """Render the explainable factor breakdown section."""
    st.markdown("##### 🔍 Why this recommendation?")
    st.caption("Confidence score is a weighted sum of the factors below.")

    for factor in factors.all_factors():
        _render_factor_row(factor)

    _render_score_composition(factors)


def _render_factor_row(factor: FactorScore) -> None:
    """Render a single factor with its score bar and explanation."""
    icon = _FACTOR_ICONS.get(factor.name, "▪️")
    contribution = factor.score * factor.weight

    cols = st.columns([2, 3, 2])
    with cols[0]:
        st.markdown(f"**{icon} {factor.name}**")
        st.caption(f"Weight: {factor.weight:.0%} · Contribution: {contribution:.0%}")
    with cols[1]:
        _render_score_bar(factor.score)
    with cols[2]:
        st.caption(factor.explanation)


def _render_score_bar(score: float) -> None:
    """Render a visual score bar (text-based, accessible).

    Uses a 10-segment bar where filled segments represent the score.
    Color is accompanied by a textual percentage for accessibility.
    """
    filled = int(round(score * 10))
    bar = "█" * filled + "░" * (10 - filled)
    st.markdown(f"`{bar}` **{score:.0%}**")


def _render_score_composition(factors: FactorBreakdown) -> None:
    """Render a summary table showing how each factor contributes."""
    rows = []
    for f in factors.all_factors():
        rows.append({
            "Factor": f.name,
            "Score": f"{f.score:.0%}",
            "Weight": f"{f.weight:.0%}",
            "Contribution": f"{f.score * f.weight:.0%}",
        })
    rows.append({
        "Factor": "**Total**",
        "Score": "",
        "Weight": "**100%**",
        "Contribution": f"**{factors.composite_score:.0%}**",
    })
    st.table(rows)
