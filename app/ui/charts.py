"""Charts view — interactive price trend charts."""

from __future__ import annotations

import streamlit as st

from app.database import get_session
from app.providers.yfinance_provider import YFinanceProvider
from app.repositories.holding_repository import HoldingRepository
from app.services.chart_service import ChartService
from app.ui.components.state_indicators import empty_state, error_message


def render_charts() -> None:
    """Render the charts view."""
    st.title("📉 Price Charts")

    session = get_session()
    holding_repo = HoldingRepository(session)
    provider = YFinanceProvider()
    chart_service = ChartService(provider)

    portfolio_tickers = holding_repo.get_all_tickers()
    default_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
    all_tickers = sorted(set(portfolio_tickers + default_tickers))

    if not all_tickers:
        empty_state(title="No tickers available", message="Add holdings to your portfolio to view their charts.")
        session.close()
        return

    selected_ticker = st.selectbox("Select Ticker", options=all_tickers, index=0)

    col1, col2 = st.columns([3, 2])
    with col2:
        time_ranges = ["1D", "1W", "1M", "3M", "1Y"]
        selected_range = st.radio("Time Range", options=time_ranges, index=2, horizontal=True)
    with col1:
        chart_type = st.radio("Chart Type", options=["Line", "Candlestick"], index=0, horizontal=True)

    st.markdown("---")

    if not selected_ticker:
        empty_state(title="No ticker selected", message="Select a ticker above to view its price chart.")
        session.close()
        return

    with st.spinner(f"Loading price data for {selected_ticker}..."):
        chart_data = chart_service.prepare_chart_data(selected_ticker, selected_range)

    if chart_data is None:
        error_message(
            title="No data available",
            message=f"Could not retrieve price history for {selected_ticker}. The ticker may be invalid or market data is unavailable.",
            recovery_hint="Try a different ticker or time range.",
        )
        session.close()
        return

    if chart_type == "Candlestick":
        fig = chart_service.create_candlestick_chart(chart_data)
    else:
        fig = chart_service.create_line_chart(chart_data)

    st.plotly_chart(fig, width="stretch")

    st.markdown("---")
    st.subheader("Data Summary")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Data Points", len(chart_data["dates"]))
    with col2:
        st.metric("Latest Close", f"${chart_data['closes'][-1]:.2f}")
    with col3:
        st.metric("Period High", f"${max(chart_data['highs']):.2f}")
    with col4:
        st.metric("Period Low", f"${min(chart_data['lows']):.2f}")

    session.close()