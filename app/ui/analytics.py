"""Analytics view — portfolio performance analytics."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from app.database import get_session
from app.providers.yfinance_provider import YFinanceProvider
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository
from app.services.portfolio_service import PortfolioService
from app.ui.components.state_indicators import empty_state
from app.ui.components.styles import card_container, section_header, styled_divider
from app.utils.currency import format_money


def render_analytics() -> None:
    """Render the portfolio analytics view."""
    st.title("📐 Portfolio Analytics")

    session = get_session()
    holding_repo = HoldingRepository(session)
    price_repo = PriceRepository(session)
    provider = YFinanceProvider()
    portfolio_service = PortfolioService(holding_repo, price_repo, provider, session)

    holdings = holding_repo.get_all()

    if not holdings:
        empty_state(title="No analytics available", message="Add holdings to your portfolio to view analytics.")
        session.close()
        return

    refresh_col, _ = st.columns([1, 5])
    with refresh_col:
        if st.button("🔄 Refresh Analytics", type="primary"):
            st.rerun()

    styled_divider()

    with st.spinner("Calculating portfolio analytics..."):
        allocation = portfolio_service.calculate_allocation(holdings)
        sector_exposure = portfolio_service.calculate_sector_exposure(holdings)
        performance = portfolio_service.compare_holding_performance(holdings)

    section_header("Asset Allocation", "🥧")
    if allocation:
        fig_pie = px.pie(
            values=list(allocation.values()),
            names=list(allocation.keys()),
            title="Portfolio Allocation by Holding",
            hole=0.45,
            color_discrete_sequence=px.colors.sequential.Blues_r,
        )
        fig_pie.update_layout(
            template="plotly_white",
            height=420,
            margin={"t": 60, "b": 40, "l": 40, "r": 40},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_pie, width="stretch")
    else:
        st.info("Unable to calculate allocation. Market data may be unavailable.")

    styled_divider()

    section_header("Sector Exposure", "🏭")
    if sector_exposure:
        fig_bar = px.bar(
            x=list(sector_exposure.keys()),
            y=list(sector_exposure.values()),
            title="Portfolio Exposure by Sector (%)",
            labels={"x": "Sector", "y": "Exposure (%)"},
            color=list(sector_exposure.values()),
            color_continuous_scale="Blues",
        )
        fig_bar.update_layout(
            template="plotly_white",
            height=420,
            margin={"t": 60, "b": 40, "l": 40, "r": 40},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_bar, width="stretch")
    else:
        st.info("Unable to calculate sector exposure. Market data may be unavailable.")

    styled_divider()

    section_header("Holding Performance Comparison", "📊")
    if performance:
        for p in performance:
            with card_container():
                c1, c2, c3, c4 = st.columns(4)
                c1.markdown(f"### {p.ticker}")
                c2.metric("Value", format_money(p.current_value, p.currency))
                c3.metric(
                    "Gain / Loss",
                    format_money(p.absolute_gain, p.currency),
                    delta_color="normal" if p.absolute_gain >= 0 else "inverse",
                )
                c4.metric("Return", f"{p.percentage_gain:+.2f}%", delta_color="normal" if p.percentage_gain >= 0 else "inverse")
    else:
        st.info("Unable to calculate performance. Market data may be unavailable.")

    styled_divider()

    section_header("Diversification", "🧩")
    if len(holdings) == 1:
        st.warning("⚠️ Your portfolio consists of a single holding (100% allocation). Consider diversifying across multiple stocks and sectors to reduce risk.")
    elif len(allocation) > 0:
        max_allocation = max(allocation.values())
        if max_allocation > 50.0:
            dominant_ticker = max(allocation, key=allocation.get)
            st.warning(f"⚠️ **{dominant_ticker}** represents **{max_allocation:.1f}%** of your portfolio. Consider rebalancing to reduce concentration risk.")
        else:
            st.success("✅ Your portfolio is well-diversified across holdings.")

    session.close()
