"""European investment options view — displays stocks, ETFs, and bond ETFs.

Provides tabbed categories (Stocks/ETFs/Bonds), search and filter controls,
sort selector, interactive charts, and add-to-portfolio functionality.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from app.data.eu_ticker_universes import AssetClass
from app.database import get_session
from app.models.investment_option import InvestmentOption
from app.providers.yfinance_provider import YFinanceProvider
from app.repositories.holding_repository import HoldingRepository
from app.services.investment_option_service import InvestmentOptionService
from app.ui.components.investment_option_card import render_investment_option_card
from app.ui.components.state_indicators import (
    data_freshness_indicator,
    empty_state,
    error_message,
)


def render_eu_investments() -> None:
    """Render the European investment options view."""
    st.title("🇪🇺 European Investment Options")

    session = get_session()
    holding_repo = HoldingRepository(session)
    provider = YFinanceProvider()
    option_service = InvestmentOptionService(provider)

    portfolio_tickers = holding_repo.get_all_tickers()

    # Refresh button
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 Refresh"):
            st.session_state["eu_last_fetch"] = None
            st.rerun()

    # Fetch all options (current prices are fetched in parallel by the provider)
    with st.spinner("Fetching European market data..."):
        try:
            all_options = option_service.fetch_all_options(
                portfolio_tickers=portfolio_tickers
            )
        except Exception:
            all_options = []
            error_message(
                title="Unable to fetch European market data",
                message="Could not retrieve current prices for European investment options.",
                recovery_hint="Check your internet connection and try refreshing.",
            )

    if not all_options:
        empty_state(
            title="No European investment options available",
            message="Market data could not be retrieved. Try refreshing later.",
        )
        session.close()
        return

    # Pre-fetch all 5Y price histories in parallel (single batch)
    # This avoids ~94 sequential HTTP requests later in the render loop
    all_tickers = [o.ticker for o in all_options]
    with st.spinner("Loading performance data..."):
        option_service.prefetch_histories(all_tickers)

    # Data freshness indicator
    last_fetch = option_service.get_last_fetch_time()
    last_fetch_str = last_fetch.strftime("%Y-%m-%d %H:%M:%S") if last_fetch else "Never"
    is_stale = option_service.is_data_stale()
    data_freshness_indicator(is_stale, last_fetch_str)

    st.markdown("---")

    # Search and filter controls
    st.subheader("🔍 Search & Filter")
    filter_col1, filter_col2, filter_col3 = st.columns([2, 2, 2])

    with filter_col1:
        search_term = st.text_input(
            "Search by name, ticker, or sector",
            value="",
            key="eu_search",
        )

    with filter_col2:
        all_exchanges = sorted({o.exchange for o in all_options})
        selected_exchanges = st.multiselect(
            "Filter by exchange",
            options=all_exchanges,
            default=[],
            key="eu_exchange_filter",
        )

    with filter_col3:
        all_sectors = sorted({o.sector for o in all_options})
        selected_sectors = st.multiselect(
            "Filter by sector",
            options=all_sectors,
            default=[],
            key="eu_sector_filter",
        )

    # Sort selector
    sort_col1, sort_col2 = st.columns([3, 1])
    with sort_col2:
        sort_criterion = st.selectbox(
            "Sort by",
            options=["Benefit Score", "Highest 5Y Return", "Most Traded"],
            index=0,
            key="eu_sort",
        )

    # Clear filters button
    if search_term or selected_exchanges or selected_sectors:
        if st.button("Clear Filters", key="eu_clear_filters"):
            st.session_state["eu_search"] = ""
            st.session_state["eu_exchange_filter"] = []
            st.session_state["eu_sector_filter"] = []
            st.rerun()

    st.markdown("---")

    # Apply filters
    filtered = option_service.filter_options(
        all_options,
        search=search_term,
        exchanges=selected_exchanges if selected_exchanges else None,
        sectors=selected_sectors if selected_sectors else None,
    )

    # Tabbed categories
    tab_stocks, tab_etfs, tab_bonds = st.tabs(["📊 Stocks", "📈 ETFs", "🏦 Bond ETFs"])

    with tab_stocks:
        _render_category(
            filtered, AssetClass.STOCK, option_service, sort_criterion, session
        )

    with tab_etfs:
        _render_category(
            filtered, AssetClass.ETF, option_service, sort_criterion, session
        )

    with tab_bonds:
        _render_category(
            filtered, AssetClass.BOND_ETF, option_service, sort_criterion, session
        )

    session.close()


def _render_category(
    options: list[InvestmentOption],
    asset_class: AssetClass,
    service: InvestmentOptionService,
    sort_criterion: str,
    session: object,
) -> None:
    """Render a single asset class category with sorted options.

    Args:
        options: All filtered options.
        asset_class: Asset class to render.
        service: InvestmentOptionService for calculations.
        sort_criterion: Sort criterion string.
        session: Database session for add-to-portfolio.
    """
    category_options = service.get_options_by_category(options, asset_class)

    # Sort options
    criterion_map = {
        "Benefit Score": "benefit_score",
        "Highest 5Y Return": "return_5y",
        "Most Traded": "volume",
    }
    criterion = criterion_map.get(sort_criterion, "benefit_score")
    sorted_options = service.sort_options(category_options, criterion=criterion)

    if not sorted_options:
        st.info(f"No {asset_class.value.replace('_', ' ').title()}s match your filters.")
        return

    st.markdown(f"**{len(sorted_options)}** options found")

    for option in sorted_options:
        # Calculate deltas once, then pass to benefit_score to avoid
        # fetching 5Y history twice per ticker
        deltas = service.calculate_performance_deltas(option.ticker)
        benefit_score = service.calculate_benefit_score(
            option.ticker, deltas=deltas
        )

        render_investment_option_card(
            option=option,
            deltas=deltas,
            benefit_score=benefit_score,
            on_add_to_portfolio=lambda opt: _add_to_portfolio(opt, session),
        )

        # Expandable chart (uses cached history from prefetch)
        with st.expander(f"📈 View {option.ticker} price chart", expanded=False):
            _render_option_chart(option.ticker, service)


def _render_option_chart(ticker: str, service: InvestmentOptionService) -> None:
    """Render an interactive price chart for an option.

    Args:
        ticker: Ticker symbol to chart.
        service: InvestmentOptionService for data fetching.
    """
    period = st.radio(
        "Time period",
        options=["1Y", "3Y", "5Y"],
        horizontal=True,
        key=f"period_{ticker}",
    )

    chart_data = service.prepare_eu_chart_data(ticker, period)

    if chart_data is None:
        st.warning("No historical data available for this option.")
        return

    fig = go.Figure(
        data=[
            go.Scatter(
                x=chart_data["dates"],
                y=chart_data["closes"],
                mode="lines",
                name=ticker,
                line={"color": "#00d4aa", "width": 2},
                customdata=chart_data["pct_changes"],
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Price: %{y:.2f}<br>"
                    "Change: %{customdata:+.2f}%"
                    "<extra></extra>"
                ),
            )
        ]
    )
    fig.update_layout(
        title=f"{ticker} — {period} Price History",
        yaxis_title="Price",
        xaxis_title="Date",
        template="plotly_dark",
        height=400,
        hovermode="x unified",
    )
    st.plotly_chart(fig, width="stretch")


def _add_to_portfolio(option: InvestmentOption, session: object) -> None:
    """Handle adding an investment option to the portfolio.

    Args:
        option: The InvestmentOption to add.
        session: Database session.
    """
    st.session_state["eu_add_ticker"] = option.ticker
    st.session_state["eu_add_price"] = option.current_price
    st.session_state["eu_add_currency"] = option.currency

    # Show inline form
    with st.form(key=f"add_form_{option.ticker}"):
        st.write(f"**Add {option.name} ({option.ticker}) to Portfolio**")
        col1, col2 = st.columns(2)
        with col1:
            quantity = st.number_input(
                "Quantity",
                min_value=0.01,
                value=1.0,
                step=1.0,
                key=f"qty_{option.ticker}",
            )
        with col2:
            purchase_price = st.number_input(
                "Purchase Price (EUR)",
                min_value=0.01,
                value=option.current_price,
                step=0.01,
                key=f"price_{option.ticker}",
            )

        submitted = st.form_submit_button("Add to Portfolio")

        if submitted:
            if quantity <= 0 or purchase_price <= 0:
                st.error("Quantity and purchase price must be positive.")
            else:
                try:
                    repo = HoldingRepository(session)
                    repo.add(
                        ticker=option.ticker,
                        quantity=quantity,
                        purchase_price=purchase_price,
                    )
                    st.success(f"✅ Added {option.ticker} to your portfolio!")
                    st.session_state.pop("eu_add_ticker", None)
                except Exception as e:
                    st.error(f"Failed to add holding: {e}")
