"""Recommendations view — display investment suggestions.

Shows ranked list of recommended investments with metrics,
data freshness indicator, and manual refresh button.
"""

from __future__ import annotations

import streamlit as st

from app.database import get_session
from app.providers.yfinance_provider import YFinanceProvider
from app.repositories.holding_repository import HoldingRepository
from app.services.recommendation_service import RecommendationService
from app.ui.components.recommendation_card import render_recommendation_card
from app.ui.components.state_indicators import (
    data_freshness_indicator,
    empty_state,
    error_message,
)


def render_recommendations() -> None:
    """Render the recommendations view."""
    st.title("💡 Investment Recommendations")

    session = get_session()
    holding_repo = HoldingRepository(session)
    provider = YFinanceProvider()
    rec_service = RecommendationService(provider)

    # Get portfolio tickers for overlap detection
    portfolio_tickers = holding_repo.get_all_tickers()

    # Refresh button
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 Refresh"):
            st.session_state["rec_last_fetch"] = None
            st.rerun()

    # Fetch recommendations
    with st.spinner("Fetching market trends and recommendations..."):
        try:
            recommendations = rec_service.get_recommendations(
                portfolio_tickers=portfolio_tickers
            )
        except Exception:
            recommendations = []
            error_message(
                title="Unable to fetch recommendations",
                message="Could not retrieve market data for recommendations.",
                recovery_hint="Check your internet connection and try refreshing.",
            )

    if not recommendations:
        empty_state(
            title="No recommendations available",
            message="Market data could not be retrieved. Try refreshing later.",
        )
        session.close()
        return

    # Data freshness indicator
    last_fetch = rec_service.get_last_fetch_time()
    last_fetch_str = (
        last_fetch.strftime("%Y-%m-%d %H:%M:%S") if last_fetch else "Never"
    )
    is_stale = rec_service.check_freshness(last_fetch)
    data_freshness_indicator(is_stale, last_fetch_str)

    st.markdown("---")

    # Summary stats
    st.markdown(f"**{len(recommendations)}** recommendations found")

    in_portfolio_count = sum(1 for r in recommendations if r.in_portfolio)
    if in_portfolio_count > 0:
        st.info(
            f"ℹ️ {in_portfolio_count} recommendation(s) are already "
            "in your portfolio (marked with ✅)."
        )

    st.markdown("---")

    # Render recommendation cards
    for rec in recommendations:
        render_recommendation_card(rec)

    session.close()