"""Streamlit application entry point with navigation.

Provides sidebar navigation between Dashboard, Holdings,
Recommendations, Charts, and Analytics views.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Support running as `python app/main.py` by ensuring project root is importable.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import init_db


def main() -> None:
    """Main application entry point."""
    st.set_page_config(
        page_title="Investment Portfolio Tracker",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize database tables
    init_db()

    # Sidebar navigation
    st.sidebar.title("📈 Investment Portfolio Tracker")
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "Navigation",
        options=[
            "📊 Dashboard",
            "🎯 Goal Planner",
            "🇪🇺 EU Investments",
            "🎯 Four-Fund Portfolio",
            "💼 Holdings",
            "💡 Recommendations",
            "📉 Charts",
            "📐 Analytics",
        ],
        index=0,
    )

    st.sidebar.markdown("---")
    st.sidebar.caption("Local single-user mode | No authentication required")

    # Route to selected page
    if page == "📊 Dashboard":
        from app.ui.dashboard import render_dashboard
        render_dashboard()
    elif page == "🎯 Goal Planner":
        from app.ui.goal_planner import render_goal_planner
        render_goal_planner()
    elif page == "🇪🇺 EU Investments":
        from app.ui.eu_investments import render_eu_investments
        render_eu_investments()
    elif page == "🎯 Four-Fund Portfolio":
        from app.ui.four_fund import render_four_fund
        render_four_fund()
    elif page == "💼 Holdings":
        from app.ui.holdings import render_holdings
        render_holdings()
    elif page == "💡 Recommendations":
        from app.ui.recommendations import render_recommendations
        render_recommendations()
    elif page == "📉 Charts":
        from app.ui.charts import render_charts
        render_charts()
    elif page == "📐 Analytics":
        from app.ui.analytics import render_analytics
        render_analytics()


if __name__ == "__main__":
    main()
