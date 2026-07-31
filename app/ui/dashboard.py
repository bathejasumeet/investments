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
from app.ui.components.styles import section_header, styled_divider
from app.utils.currency import format_money


def _render_goals_preview() -> None:
    """Render a preview of investment goals on the dashboard."""
    styled_divider()
    section_header("Goal Progress", "🎯")

    from app.repositories.goal_repository import GoalRepository
    from app.services.goal_service import GoalService

    session = get_session()
    goal_repo = GoalRepository(session)
    goals = goal_repo.get_all()

    if not goals:
        st.info(
            "No goals defined yet. Visit the **🎯 Goal Planner** page to define "
            "your investment goals and see your probability of success."
        )
        session.close()
        return

    holding_repo = HoldingRepository(session)
    provider = YFinanceProvider()
    goal_service = GoalService(goal_repo, holding_repo, provider, session)

    holdings = holding_repo.get_all()
    with st.spinner("Running goal projections..."):
        projections = goal_service.project_all_goals(
            holdings=holdings,
            num_simulations=500,  # Fewer sims for dashboard preview
        )

    for projection in projections:
        prob_pct = projection.probability_of_success * 100
        col1, col2, col3 = st.columns([3, 2, 2])
        with col1:
            st.markdown(f"**{projection.goal_name}**")
            target_date_str = projection.target_date.strftime("%Y-%m-%d")
            st.caption(f"Target: {format_money(projection.target_amount, projection.currency)} by {target_date_str}")
        with col2:
            st.metric("Current", format_money(projection.current_value, projection.currency))
        with col3:
            color = "normal" if prob_pct >= 70 else "inverse"
            st.metric(
                "Success Probability",
                f"{prob_pct:.0f}%",
                delta_color=color,
            )
        st.progress(projection.probability_of_success)

    st.info("💡 Visit the **🎯 Goal Planner** page for detailed projections and to manage your goals.")

    session.close()


def _render_eu_investments_preview() -> None:
    """Render a preview of European investment options on the dashboard."""
    styled_divider()
    section_header("European Investment Options", "🇪🇺")

    from app.data.eu_ticker_universes import AssetClass
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

    # Show top 3 from each category in compact metric cards
    for asset_class, label, icon in [
        (AssetClass.STOCK, "Top Stocks", "📊"),
        (AssetClass.ETF, "Top ETFs", "📈"),
        (AssetClass.BOND_ETF, "Top Bond ETFs", "🏦"),
    ]:
        category = option_service.get_options_by_category(all_options, asset_class)
        if category:
            st.markdown(f"**{icon} {label}**")
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

    styled_divider()

    # Hero metrics row
    gain_positive = summary.total_gain_loss >= 0
    delta_color = "normal" if gain_positive else "inverse"
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(
            label="Total Portfolio Value",
            value=format_money(summary.total_value, summary.currency),
        )
    with c2:
        st.metric(
            label="Total Cost Basis",
            value=format_money(summary.total_cost_basis, summary.currency),
        )
    with c3:
        st.metric(
            label="Total Gain / Loss",
            value=format_money(summary.total_gain_loss, summary.currency),
            delta=f"{summary.total_percentage_gain:+.2f}%",
            delta_color=delta_color,
        )

    styled_divider()
    section_header("Your Holdings", "💼")

    for holding_summary in summary.holdings:
        render_holding_card(holding_summary)

    # Goal planner preview
    _render_goals_preview()

    # European Investment Options preview
    _render_eu_investments_preview()

    session.close()
