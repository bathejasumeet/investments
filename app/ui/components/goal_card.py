"""Goal card component — displays a single goal projection with probability of success."""

from __future__ import annotations

import streamlit as st

from app.services.goal_service import GoalProjection
from app.utils.currency import format_money


def _probability_color(probability: float) -> str:
    """Return a color indicator based on probability of success."""
    if probability >= 0.70:
        return "green"
    elif probability >= 0.50:
        return "orange"
    else:
        return "red"


def _probability_emoji(probability: float) -> str:
    """Return an emoji indicator based on probability of success."""
    if probability >= 0.80:
        return "✅"
    elif probability >= 0.50:
        return "⚠️"
    else:
        return "🚨"


def render_goal_card(projection: GoalProjection) -> None:
    """Render a single goal projection as a card.

    Args:
        projection: GoalProjection data for the goal to display.
    """
    prob_pct = projection.probability_of_success * 100
    emoji = _probability_emoji(projection.probability_of_success)
    color = _probability_color(projection.probability_of_success)

    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            st.markdown(f"### {emoji} {projection.goal_name}")
            target_date_str = projection.target_date.strftime("%Y-%m-%d")
            st.caption(f"🎯 Target: {format_money(projection.target_amount, projection.currency)} by {target_date_str}")
            if projection.mapped_tickers:
                st.caption(f"📊 Mapped: {', '.join(projection.mapped_tickers)}")
            else:
                st.caption("📊 No holdings mapped to this goal yet")

        with col2:
            st.metric(
                label="Current Value",
                value=format_money(projection.current_value, projection.currency),
            )
            st.metric(
                label="Years to Target",
                value=f"{projection.years_to_target:.1f}y",
            )

        with col3:
            st.metric(
                label="Probability of Success",
                value=f"{prob_pct:.0f}%",
                delta=f"{color.title()}",
                delta_color="normal" if color == "green" else "inverse",
                help=(
                    "Out of 1,000 simulated future scenarios, this is the percentage "
                    "that reached your target amount by your target date."
                ),
            )

        # Progress bar for probability
        st.progress(projection.probability_of_success, text=f"Success Probability: {prob_pct:.0f}%")

        # Projection details
        st.markdown("---")
        detail_col1, detail_col2, detail_col3 = st.columns(3)
        with detail_col1:
            st.metric(
                label="Projected (Median)",
                value=format_money(projection.projected_value_median, projection.currency),
                help=(
                    "The typical outcome — half of simulated scenarios ended above "
                    "this value, half below."
                ),
            )
        with detail_col2:
            st.metric(
                label="Worst Case (P10)",
                value=format_money(projection.projected_value_p10, projection.currency),
                help=(
                    "A pessimistic outcome — only 10% of simulated scenarios were "
                    "worse than this."
                ),
            )
        with detail_col3:
            st.metric(
                label="Best Case (P90)",
                value=format_money(projection.projected_value_p90, projection.currency),
                help=(
                    "An optimistic outcome — only 10% of simulated scenarios were "
                    "better than this."
                ),
            )

        # Shortfall / surplus
        if projection.shortfall > 0:
            st.warning(
                f"📉 **Shortfall:** You may need "
                f"{format_money(projection.shortfall, projection.currency)} more "
                f"to reach your goal."
            )
        else:
            st.success(
                f"📈 **Surplus:** You're projected to have "
                f"{format_money(abs(projection.shortfall), projection.currency)} "
                f"above your target."
            )
