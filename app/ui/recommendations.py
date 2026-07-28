"""Recommendations view — display investment suggestions."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from app.database import get_session
from app.providers.yfinance_provider import YFinanceProvider
from app.repositories.holding_repository import HoldingRepository
from app.services.recommendation_service import Recommendation, RecommendationService
from app.ui.components.recommendation_card import render_recommendation_card
from app.ui.components.state_indicators import data_freshness_indicator, empty_state, error_message

_CACHE_RECS_KEY = "recommendations_cache"
_CACHE_FETCH_KEY = "rec_last_fetch"
_CACHE_ERROR_KEY = "recommendations_error"


def render_recommendations() -> None:
    """Render the recommendations view."""
    st.title("💡 Investment Recommendations")

    session = get_session()
    holding_repo = HoldingRepository(session)
    provider = YFinanceProvider()
    rec_service = RecommendationService(provider)

    portfolio_tickers = holding_repo.get_all_tickers()

    col1, col2 = st.columns([4, 1])
    with col2:
        force_refresh = st.button("🔄 Refresh")

    if force_refresh:
        _clear_recommendation_cache()

    recommendations, last_fetch, fetch_error = _load_recommendations(
        rec_service,
        portfolio_tickers,
        force_refresh=force_refresh,
    )

    if fetch_error:
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

    last_fetch_str = last_fetch.strftime("%Y-%m-%d %H:%M:%S") if last_fetch else "Never"
    is_stale = rec_service.check_freshness(last_fetch)
    data_freshness_indicator(is_stale, last_fetch_str)

    st.markdown("---")
    st.markdown(f"**{len(recommendations)}** recommendations found")

    in_portfolio_count = sum(1 for r in recommendations if r.in_portfolio)
    if in_portfolio_count > 0:
        st.info(
            f"ℹ️ {in_portfolio_count} recommendation(s) are already in your "
            "portfolio (marked with ✅)."
        )

    with st.expander("🔍 How are recommendations scored?"):
        st.markdown(
            """
Every recommendation's **confidence score** is a transparent, weighted
combination of five explainable factors — no black-box AI. This is a
deterministic weighted score, not a simulation-based probability like the
Goal Planner's Monte Carlo projections.

| Factor | Weight | What it measures |
| --- | --- | --- |
| 🚀 **Momentum** | 30% | Recent price change (past month). Higher change → higher score. |
| 💰 **Valuation** | 20% | Position within the recent price range. Near the low → better value. |
| 📊 **Volatility** | 15% | Daily return std-dev. Lower volatility → higher stability score. |
| 📈 **Volume** | 15% | Average daily trading volume. Higher volume → higher liquidity. |
| 🎯 **Concentration** | 20% | Portfolio overlap. New tickers score 100%; held tickers score 0%. |

The **confidence score** = Σ (factor score × factor weight). Expand any
recommendation card below to see the full breakdown.
            """
        )

    st.markdown("---")

    for rec in recommendations:
        render_recommendation_card(rec)

    session.close()


def _clear_recommendation_cache() -> None:
    """Drop cached recommendation payloads so the next load refetches."""
    for key in (_CACHE_RECS_KEY, _CACHE_FETCH_KEY, _CACHE_ERROR_KEY):
        st.session_state.pop(key, None)


def _load_recommendations(
    rec_service: RecommendationService,
    portfolio_tickers: list[str],
    *,
    force_refresh: bool,
) -> tuple[list[Recommendation], datetime | None, bool]:
    """Return cached recommendations unless missing or force-refresh.

    Caching is critical: Streamlit reruns the script on expander toggles and
    other widget interactions. Without a cache, each interaction re-hits
    Yahoo Finance and freezes the page.
    """
    if (
        not force_refresh
        and _CACHE_RECS_KEY in st.session_state
        and st.session_state[_CACHE_RECS_KEY] is not None
    ):
        return (
            list(st.session_state[_CACHE_RECS_KEY]),
            st.session_state.get(_CACHE_FETCH_KEY),
            bool(st.session_state.get(_CACHE_ERROR_KEY, False)),
        )

    with st.spinner("Fetching market trends and recommendations..."):
        try:
            recommendations = rec_service.get_recommendations(
                portfolio_tickers=portfolio_tickers
            )
            fetch_error = False
        except Exception:
            recommendations = []
            fetch_error = True

    last_fetch = rec_service.get_last_fetch_time()
    st.session_state[_CACHE_RECS_KEY] = recommendations
    st.session_state[_CACHE_FETCH_KEY] = last_fetch
    st.session_state[_CACHE_ERROR_KEY] = fetch_error
    return recommendations, last_fetch, fetch_error
