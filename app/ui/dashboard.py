"""Dashboard view — portfolio summary at a glance."""

from __future__ import annotations

import streamlit as st

from app.database import get_session
from app.providers.yfinance_provider import YFinanceProvider
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository
from app.services.market_data_service import MarketDataService
from app.services.portfolio_service import PortfolioService
from app.ui.components.holding_card import render_holding_card
from app.ui.components.state_indicators import (
    data_freshness_indicator,
    empty_state,
    error_message,
)
from app.utils.currency import format_money


def _render_eu_investments_preview() -> None:
    """Render a preview of European investment options on the dashboard."""
    st.markdown("---")
    st.subheader("🇪🇺 European Investment Options")

    from app.data.eu_ticker_universes import AssetClass, get_all_entries
    from app.providers.yfinance_provider import YFinanceProvider
    from app.services.investment_option_service import InvestmentOptionService

    provider = YFinanceProvider()
    option_service = InvestmentOptionService(provider)

    with st.spinner("Loading European investment options..."):
        try:
            all_options = option_service.fetch_all_options()
        except Exception:
            all_options = []

    if not all_options:
        st.info(
            "European investment options are currently unavailable. "
            "Visit the **🇪🇺 EU Investments** page for the full overview."
        )
        return

    # Show top 3 from each category
    for asset_class, label in [
        (AssetClass.STOCK, "📊 Top Stocks"),
        (AssetClass.ETF, "📈 Top ETFs"),
        (AssetClass.BOND_ETF, "🏦 Top Bond ETFs"),
    ]:
        category = option_service.get_options_by_category(all_options, asset_class)
        if category:
            st.markdown(f"**{label}**")
            cols = st.columns(min(3, len(category)))
            for i, option in enumerate(category[:3]):
                with cols[i]:
                    st.metric(
                        label=option.name,
                        value=f"{option.current_price:,.2f} {option.currency}",
                        delta=f"{option.exchange}",
                    )
            st.markdown("")

    st.info("💡 Visit the **🇪🇺 EU Investments** page for full details, charts, and filtering.")


def render_dashboard() -> None:
    """Render the portfolio dashboard view."""
    st.title("📊 Portfolio Dashboard")

    session = get_session()
    holding_repo = HoldingRepository(session)
    price_repo = PriceRepository(session)
    provider = YFinanceProvider()
    market_data_service = MarketDataService(provider, price_repo)
    portfolio_service = PortfolioService(holding_repo, price_repo, provider, session)

    holdings = holding_repo.get_all()

    if not holdings:
        empty_state(
            title="Your portfolio is empty",
            message="Start by adding your first investment holding. Navigate to the **💼 Holdings** page.",
            action_label="Go to Holdings",
        )
        session.close()
        return

    tickers = [h.ticker for h in holdings]
    with st.spinner("Fetching latest market prices..."):
        prices = market_data_service.fetch_current_prices(tickers)

    if not prices:
        error_message(
            title="Unable to fetch market data",
            message="Could not retrieve current prices. Showing last known data if available.",
            recovery_hint="Check your internet connection and try refreshing.",
        )

    summary = portfolio_service.get_portfolio_summary(holdings)

    last_updated_str = (
        summary.last_updated.strftime("%Y-%m-%d %H:%M:%S") if summary.last_updated else "Never"
    )
    data_freshness_indicator(summary.is_stale, last_updated_str)

    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="Total Portfolio Value",
            value=format_money(summary.total_value, summary.currency),
        )
    with col2:
        st.metric(
            label="Total Cost Basis",
            value=format_money(summary.total_cost_basis, summary.currency),
        )
    with col3:
        st.metric(
            label="Total Gain/Loss",
            value=format_money(summary.total_gain_loss, summary.currency),
            delta=f"{summary.total_percentage_gain:+.2f}%",
            delta_color="normal" if summary.total_gain_loss >= 0 else "inverse",
        )

    st.markdown("---")
    st.subheader("Your Holdings")

    for holding_summary in summary.holdings:
        render_holding_card(holding_summary)

    # European Investment Options preview
    _render_eu_investments_preview()

    session.close()
