"""Four-fund portfolio builder view — Bogleheads strategy page.

Provides tabbed categories (EU Stocks, Developed World, Emerging
Markets, Bonds), fund comparison cards with TER/AUM/returns, a
portfolio builder with allocation weights, and weighted portfolio
TER calculation.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from app.config import config
from app.data.four_fund_universe import FundCategory
from app.database import get_session
from app.models.fund_profile import FundProfile, PortfolioSelection
from app.providers.yfinance_provider import YFinanceProvider
from app.repositories.four_fund_plan_repository import FourFundPlanRepository
from app.services.fund_comparison_service import FundComparisonService
from app.services.monte_carlo_service import (
    MonteCarloSummary,
    run_monte_carlo_projection,
    summarize_monte_carlo,
)
from app.ui.components.fund_comparison_card import (
    _format_aum,
    render_fund_comparison_card,
)
from app.ui.components.state_indicators import (
    data_freshness_indicator,
    empty_state,
    error_message,
    render_info_popover,
    success_toast,
)
from app.utils.currency import format_money

# Category display configuration
_CATEGORY_CONFIG: dict[FundCategory, dict[str, str]] = {
    FundCategory.EU_STOCKS: {
        "label": "EU Stocks (Domestic)",
        "icon": "eu",
        "description": "Broad European equity indices — your home market",
    },
    FundCategory.DEVELOPED_WORLD: {
        "label": "Developed World",
        "icon": "world",
        "description": "Global developed markets (US, Japan, etc.)",
    },
    FundCategory.EMERGING_MARKETS: {
        "label": "Emerging Markets",
        "icon": "em",
        "description": "China, India, Brazil, and other emerging economies",
    },
    FundCategory.BONDS_DOMESTIC: {
        "label": "Bonds (Domestic EUR)",
        "icon": "bonds_d",
        "description": "EUR-denominated government and corporate bonds",
    },
    FundCategory.BONDS_INTERNATIONAL: {
        "label": "Bonds (International)",
        "icon": "bonds_i",
        "description": "Global aggregate bonds (EUR-hedged)",
    },
}

_FOUR_FUND_PRIMER = """
#### What Bogleheads means in practice
Bogleheads investing focuses on broad diversification, low costs, and long-term
discipline instead of stock picking or market timing.

#### What is a four-fund portfolio?
It is a simple portfolio split across four building blocks:

1. EU stocks (home-market equities)
2. Developed world stocks
3. Emerging markets stocks
4. Bonds (domestic or international)

This gives global equity exposure plus a stabilizing bond allocation, while
staying easy to manage and rebalance.

#### How to use this page
- Pick one ETF for each slot.
- Set weights that match your risk tolerance and time horizon.
- Keep costs low (TER), diversify broadly, and rebalance periodically.
"""


def render_four_fund() -> None:
    """Render the four-fund portfolio builder view."""
    st.title("Four-Fund Portfolio Builder")
    st.markdown(
        "Build a simple, low-cost Bogleheads portfolio using four index ETFs. "
        "Compare funds by **TER (cost)**, **fund size**, and **returns** to "
        "choose the best option for each slot."
    )
    render_info_popover(
        "What is a four-fund portfolio?",
        _FOUR_FUND_PRIMER,
        icon="📘",
    )

    provider = YFinanceProvider()
    service = FundComparisonService(provider)
    session = get_session()
    plan_repo = FourFundPlanRepository(session)

    try:
        # Refresh button
        col1, col2 = st.columns([4, 1])
        with col2:
            if st.button("Refresh Data"):
                st.session_state["four_fund_profiles"] = None
                st.rerun()

        # Fetch all fund profiles
        profiles = st.session_state.get("four_fund_profiles")
        if profiles is None:
            with st.spinner("Fetching fund data (TER, AUM, returns)..."):
                try:
                    profiles = service.fetch_all_profiles()
                    st.session_state["four_fund_profiles"] = profiles
                except Exception:
                    profiles = []
                    error_message(
                        title="Unable to fetch fund data",
                        message="Could not retrieve ETF metadata from the market data provider.",
                        recovery_hint="Check your internet connection and try refreshing.",
                    )

        if not profiles:
            empty_state(
                title="No fund data available",
                message="Market data could not be retrieved. Try refreshing later.",
            )
            return

        # Data freshness indicator
        last_fetch = service.get_last_fetch_time()
        last_fetch_str = (
            last_fetch.strftime("%Y-%m-%d %H:%M:%S") if last_fetch else "Never"
        )
        data_freshness_indicator(False, last_fetch_str)

        st.markdown("---")

        # Calculate best in class
        best_in_class = service.best_in_class(profiles)

        # Tabbed categories
        tab_eu, tab_dev, tab_em, tab_bonds = st.tabs([
            "EU Stocks (Domestic)",
            "Developed World",
            "Emerging Markets",
            "Bonds",
        ])

        with tab_eu:
            _render_category(
                profiles, FundCategory.EU_STOCKS, service, best_in_class
            )

        with tab_dev:
            _render_category(
                profiles, FundCategory.DEVELOPED_WORLD, service, best_in_class
            )

        with tab_em:
            _render_category(
                profiles, FundCategory.EMERGING_MARKETS, service, best_in_class
            )

        with tab_bonds:
            st.markdown("**Bonds (Domestic EUR)**")
            _render_category(
                profiles, FundCategory.BONDS_DOMESTIC, service, best_in_class
            )
            st.markdown("---")
            st.markdown("**Bonds (International, EUR-hedged)**")
            _render_category(
                profiles, FundCategory.BONDS_INTERNATIONAL, service, best_in_class
            )

        st.markdown("---")
        _render_portfolio_builder(profiles, service, plan_repo)
    finally:
        session.close()


def _render_category(
    profiles: list[FundProfile],
    category: FundCategory,
    service: FundComparisonService,
    best_in_class: dict[FundCategory, FundProfile],
) -> None:
    """Render a single fund category with sorted comparison cards.

    Args:
        profiles: All fund profiles.
        category: FundCategory to render.
        service: FundComparisonService for sorting.
        best_in_class: Best-in-class mapping for highlighting.
    """
    config = _CATEGORY_CONFIG.get(category, {})
    description = config.get("description", "")
    if description:
        st.caption(description)

    category_profiles = service.get_by_category(profiles, category)

    if not category_profiles:
        st.info("No funds available in this category.")
        return

    # Sort selector
    sort_col1, sort_col2 = st.columns([3, 1])
    with sort_col2:
        sort_criterion = st.selectbox(
            "Sort by",
            options=["TER (lowest)", "3Y Return (highest)", "Fund Size (largest)"],
            index=0,
            key=f"sort_{category.value}",
        )

    # Sort profiles
    if sort_criterion == "TER (lowest)":
        sorted_profiles = service.rank_by_ter(category_profiles)
    elif sort_criterion == "3Y Return (highest)":
        sorted_profiles = service.rank_by_return(category_profiles, "3y")
    else:
        sorted_profiles = service.rank_by_aum(category_profiles)

    available_count = sum(1 for p in sorted_profiles if p.is_available)
    st.markdown(f"**{available_count}** funds available")

    best_fund = best_in_class.get(category)

    for profile in sorted_profiles:
        is_best = (
            best_fund is not None
            and profile.ticker == best_fund.ticker
            and profile.is_available
        )
        is_selected = _is_fund_selected(profile, category)

        render_fund_comparison_card(
            profile=profile,
            is_selected=is_selected,
            is_best_in_class=is_best,
            on_select=lambda p, cat=category: _select_fund(p, cat),
            key_prefix=category.value,
        )


def _is_fund_selected(profile: FundProfile, category: FundCategory) -> bool:
    """Check if a fund is currently selected for its category slot.

    Args:
        profile: The FundProfile to check.
        category: The FundCategory slot.

    Returns:
        True if this fund is selected for the slot.
    """
    slot_key = _get_slot_key(category)
    selected_ticker = st.session_state.get(slot_key)
    return selected_ticker == profile.ticker


def _get_slot_key(category: FundCategory) -> str:
    """Get the session state key for a category's selected fund.

    Args:
        category: FundCategory slot.

    Returns:
        Session state key string.
    """
    return f"four_fund_selected_{category.value}"


def _select_fund(profile: FundProfile, category: FundCategory) -> None:
    """Select a fund for a portfolio slot.

    Args:
        profile: The FundProfile to select.
        category: The FundCategory slot to fill.
    """
    st.session_state[_get_slot_key(category)] = profile.ticker
    st.rerun()


def _get_selected_profile(
    profiles: list[FundProfile], category: FundCategory
) -> FundProfile | None:
    """Get the currently selected FundProfile for a category.

    Args:
        profiles: All fund profiles.
        category: FundCategory slot.

    Returns:
        Selected FundProfile, or None if not selected.
    """
    slot_key = _get_slot_key(category)
    selected_ticker = st.session_state.get(slot_key)
    if selected_ticker is None:
        return None

    for p in profiles:
        if p.ticker == selected_ticker and p.category == category:
            return p
    return None


def _render_portfolio_builder(
    profiles: list[FundProfile],
    service: FundComparisonService,
    plan_repo: FourFundPlanRepository,
) -> None:
    """Render the portfolio builder section with selected funds and weights.

    Args:
        profiles: All fund profiles.
        service: FundComparisonService for calculations.
    """
    st.subheader("Your Selected Portfolio")
    st.caption("Load, save, and simulate your four-fund allocation from this section.")

    _render_saved_plan_controls(profiles, plan_repo)

    # Get selected funds
    eu_stocks = _get_selected_profile(profiles, FundCategory.EU_STOCKS)
    developed = _get_selected_profile(profiles, FundCategory.DEVELOPED_WORLD)
    emerging = _get_selected_profile(profiles, FundCategory.EMERGING_MARKETS)
    bonds_domestic = _get_selected_profile(profiles, FundCategory.BONDS_DOMESTIC)
    bonds_intl = _get_selected_profile(
        profiles, FundCategory.BONDS_INTERNATIONAL
    )

    # For bonds, use whichever is selected (domestic or international)
    bonds = bonds_domestic if bonds_domestic is not None else bonds_intl

    # Allocation weight inputs
    st.markdown("**Allocation Weights** (must sum to 100%)")
    w_col1, w_col2, w_col3, w_col4 = st.columns(4)

    with w_col1:
        eu_weight = st.number_input(
            "EU Stocks (%)", min_value=0, max_value=100, value=30, step=5,
            key="weight_eu",
        )
    with w_col2:
        dev_weight = st.number_input(
            "Developed World (%)", min_value=0, max_value=100, value=30, step=5,
            key="weight_dev",
        )
    with w_col3:
        em_weight = st.number_input(
            "Emerging Markets (%)", min_value=0, max_value=100, value=10, step=5,
            key="weight_em",
        )
    with w_col4:
        bonds_weight = st.number_input(
            "Bonds (%)", min_value=0, max_value=100, value=30, step=5,
            key="weight_bonds",
        )

    total_weight = eu_weight + dev_weight + em_weight + bonds_weight

    _render_plan_save_controls(
        plan_repo=plan_repo,
        eu_stocks=eu_stocks,
        developed=developed,
        emerging=emerging,
        bonds=bonds,
        eu_weight=eu_weight,
        dev_weight=dev_weight,
        em_weight=em_weight,
        bonds_weight=bonds_weight,
        total_weight=total_weight,
    )

    # Display selected funds
    with st.container(border=True):
        _render_selected_slot("EU Stocks (Domestic)", eu_stocks, eu_weight)
        _render_selected_slot("Developed World", developed, dev_weight)
        _render_selected_slot("Emerging Markets", emerging, em_weight)
        _render_selected_slot("Bonds", bonds, bonds_weight)

        st.markdown("---")

        # Weight validation
        if total_weight != 100:
            st.warning(f"Weights sum to {total_weight}% — adjust to total 100%.")
        else:
            st.success("Weights sum to 100%.")

        # Calculate portfolio TER
        selection = PortfolioSelection(
            eu_stocks=eu_stocks,
            developed_world=developed,
            emerging_markets=emerging,
            bonds=bonds,
            eu_stocks_weight=eu_weight / 100,
            developed_world_weight=dev_weight / 100,
            emerging_markets_weight=em_weight / 100,
            bonds_weight=bonds_weight / 100,
        )

        portfolio_ter = service.calculate_portfolio_ter(selection)
        portfolio_aum = service.calculate_portfolio_aum(selection)

        ter_col1, ter_col2 = st.columns(2)
        with ter_col1:
            st.metric(
                "Weighted Avg TER",
                f"{portfolio_ter:.4f}%" if portfolio_ter > 0 else "N/A",
                help="Lower is better — this is your portfolio's annual cost",
            )
        with ter_col2:
            st.metric(
                "Combined Fund Size",
                _format_aum(portfolio_aum) if portfolio_aum > 0 else "N/A",
                help="Total AUM across all selected funds",
            )

    _render_monte_carlo_section(
        selection=selection,
        total_weight=total_weight,
    )

    # Bogleheads tips
    st.markdown("---")
    st.subheader("Bogleheads Principles")
    with st.expander("Learn about the four-fund portfolio strategy"):
        st.markdown(
            """
**The Four-Fund Portfolio** extends the classic Bogleheads three-fund
portfolio by splitting bonds into domestic and international:

1. **Domestic Stocks (EU)** — Broad European equity index
2. **Developed World** — Global developed markets (US, Japan, etc.)
3. **Emerging Markets** — China, India, Brazil, etc.
4. **Bonds** — Government and/or corporate bonds (domestic + international)

**Key Principles:**
- **Costs matter** — Choose funds with the lowest TER (Total Expense Ratio)
- **Simplicity** — Four funds are enough for a diversified portfolio
- **Stay the course** — Don't time the market; rebalance periodically
- **Fund size matters** — Larger AUM means more stable and liquid funds
- **Past performance does not guarantee future results**

**Common Allocation Guidelines:**
- **Aggressive (young investor)**: 80% stocks / 20% bonds
- **Moderate**: 60% stocks / 40% bonds
- **Conservative (near retirement)**: 40% stocks / 60% bonds

**Stocks split**: Within your stock allocation, a common approach is
70% developed world / 20% domestic (EU) / 10% emerging markets.
            """
        )


def _render_selected_slot(
    label: str, profile: FundProfile | None, weight: int
) -> None:
    """Render a single selected portfolio slot.

    Args:
        label: Slot label (e.g., "EU Stocks (Domestic)").
        profile: Selected FundProfile, or None.
        weight: Allocation weight percentage.
    """
    col1, col2, col3 = st.columns([4, 2, 2])

    with col1:
        if profile is not None:
            st.markdown(f"**{label}**: {profile.name} (`{profile.ticker}`)")
        else:
            st.markdown(f"**{label}**: _Not selected — choose a fund above_")

    with col2:
        if profile is not None and profile.is_available:
            st.metric("TER", f"{profile.ter:.2f}%")
        else:
            st.metric("TER", "N/A")

    with col3:
        st.metric("Allocation", f"{weight}%")


def _render_saved_plan_controls(
    profiles: list[FundProfile],
    plan_repo: FourFundPlanRepository,
) -> None:
    """Render load/delete controls for saved plans."""
    plans = plan_repo.get_all()
    if not plans:
        st.caption("No saved four-fund plans yet.")
        return

    st.markdown("**Saved Plans**")
    plan_names = [p.name for p in plans]
    selected_name = st.selectbox(
        "Saved plan",
        options=plan_names,
        key="four_fund_saved_plan",
    )

    load_col, delete_col = st.columns(2)
    with load_col:
        if st.button("Load Saved Plan", key="load_saved_four_fund_plan"):
            plan = next((p for p in plans if p.name == selected_name), None)
            if plan is not None:
                _load_saved_plan_into_state(plan, profiles)
                success_toast(f"Loaded saved plan: {plan.name}")
                st.rerun()
    with delete_col:
        if st.button("Delete Saved Plan", key="delete_saved_four_fund_plan"):
            plan = next((p for p in plans if p.name == selected_name), None)
            if plan is not None and plan_repo.delete(plan.id):
                success_toast(f"Deleted saved plan: {plan.name}")
                st.rerun()


def _load_saved_plan_into_state(
    plan,
    profiles: list[FundProfile],
) -> None:
    """Apply a saved plan to current Streamlit session state."""
    st.session_state[_get_slot_key(FundCategory.EU_STOCKS)] = plan.eu_ticker
    st.session_state[_get_slot_key(FundCategory.DEVELOPED_WORLD)] = plan.developed_ticker
    st.session_state[_get_slot_key(FundCategory.EMERGING_MARKETS)] = plan.emerging_ticker

    bonds_profile = next((p for p in profiles if p.ticker == plan.bonds_ticker), None)
    if bonds_profile is not None and bonds_profile.category == FundCategory.BONDS_DOMESTIC:
        st.session_state[_get_slot_key(FundCategory.BONDS_DOMESTIC)] = plan.bonds_ticker
        st.session_state.pop(_get_slot_key(FundCategory.BONDS_INTERNATIONAL), None)
    else:
        st.session_state[_get_slot_key(FundCategory.BONDS_INTERNATIONAL)] = plan.bonds_ticker
        st.session_state.pop(_get_slot_key(FundCategory.BONDS_DOMESTIC), None)

    st.session_state["weight_eu"] = int(round(plan.eu_weight))
    st.session_state["weight_dev"] = int(round(plan.developed_weight))
    st.session_state["weight_em"] = int(round(plan.emerging_weight))
    st.session_state["weight_bonds"] = int(round(plan.bonds_weight))


def _render_plan_save_controls(
    *,
    plan_repo: FourFundPlanRepository,
    eu_stocks: FundProfile | None,
    developed: FundProfile | None,
    emerging: FundProfile | None,
    bonds: FundProfile | None,
    eu_weight: int,
    dev_weight: int,
    em_weight: int,
    bonds_weight: int,
    total_weight: int,
) -> None:
    """Render save controls for the current four-fund selection."""
    st.markdown("### Save Portfolio Plan")
    st.caption("Plans are stored locally in your SQLite database and can be reloaded anytime.")

    if "four_fund_plan_name" not in st.session_state:
        st.session_state["four_fund_plan_name"] = f"Plan {datetime.utcnow():%Y-%m-%d %H:%M}"

    plan_name = st.text_input("Plan Name", key="four_fund_plan_name")
    if st.button("Save / Update Plan", key="save_four_fund_plan"):
        if eu_stocks is None or developed is None or emerging is None or bonds is None:
            st.warning("Select one fund for each slot before saving.")
            return
        if total_weight != 100:
            st.warning("Allocation must sum to 100% before saving.")
            return

        cleaned_name = plan_name.strip()
        if not cleaned_name:
            st.warning("Please enter a plan name.")
            return

        plan_repo.save(
            name=cleaned_name,
            eu_ticker=eu_stocks.ticker,
            developed_ticker=developed.ticker,
            emerging_ticker=emerging.ticker,
            bonds_ticker=bonds.ticker,
            eu_weight=float(eu_weight),
            developed_weight=float(dev_weight),
            emerging_weight=float(em_weight),
            bonds_weight=float(bonds_weight),
        )
        success_toast(f"Saved plan: {cleaned_name}")
        st.rerun()


def _render_monte_carlo_section(
    *,
    selection: PortfolioSelection,
    total_weight: int,
) -> None:
    """Render Monte Carlo simulation controls based on current allocation."""
    st.markdown("### Monte Carlo Projection")

    if (
        selection.eu_stocks is None
        or selection.developed_world is None
        or selection.emerging_markets is None
        or selection.bonds is None
    ):
        st.info("Select one fund for each slot to run a simulation.")
        return
    if total_weight != 100:
        st.info("Set allocation weights to exactly 100% to run simulation.")
        return

    derived_expected = _derive_expected_return_from_selection(selection)
    if derived_expected is not None:
        st.caption(
            f"Using weighted 3Y return as a starting point: {derived_expected * 100:.2f}%"
        )

    default_expected_pct = 7.0 if derived_expected is None else max(0.0, min(15.0, derived_expected * 100))

    col1, col2 = st.columns(2)
    with col1:
        current_value = st.number_input(
            f"Current Portfolio Value ({config.base_currency})",
            min_value=0.0,
            value=25_000.0,
            step=1_000.0,
            key="four_fund_mc_current_value",
        )
        target_value = st.number_input(
            f"Target Value ({config.base_currency})",
            min_value=0.0,
            value=100_000.0,
            step=1_000.0,
            key="four_fund_mc_target_value",
        )
        monthly_contribution = st.number_input(
            f"Monthly Contribution ({config.base_currency})",
            min_value=0.0,
            value=500.0,
            step=50.0,
            key="four_fund_mc_monthly_contribution",
        )
    with col2:
        years = st.slider(
            "Years to Target",
            min_value=1,
            max_value=40,
            value=10,
            key="four_fund_mc_years",
        )
        expected_return_pct = st.slider(
            "Expected Annual Return (%)",
            min_value=0.0,
            max_value=15.0,
            value=float(default_expected_pct),
            step=0.5,
            key="four_fund_mc_expected_return",
        )
        volatility_pct = st.slider(
            "Annual Volatility (%)",
            min_value=5.0,
            max_value=40.0,
            value=15.0,
            step=1.0,
            key="four_fund_mc_volatility",
        )
        num_sims = st.select_slider(
            "Simulations",
            options=[100, 500, 1000, 5000],
            value=1000,
            key="four_fund_mc_simulations",
        )

    if st.button("Run Monte Carlo", key="run_four_fund_mc"):
        outcomes = run_monte_carlo_projection(
            current_value=current_value,
            monthly_contribution=monthly_contribution,
            years=float(years),
            expected_return=expected_return_pct / 100.0,
            volatility=volatility_pct / 100.0,
            num_simulations=num_sims,
        )
        st.session_state["four_fund_mc_summary"] = summarize_monte_carlo(
            outcomes,
            target_amount=target_value,
        )
        st.session_state["four_fund_mc_target_value"] = target_value

    summary = st.session_state.get("four_fund_mc_summary")
    if isinstance(summary, MonteCarloSummary):
        status = _success_label(summary.probability_of_success)
        st.markdown(f"**Status:** {status}")

        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Probability of Success", f"{summary.probability_of_success * 100:.0f}%")
        with m2:
            st.metric("Median Outcome", format_money(summary.projected_value_median, config.base_currency))
        with m3:
            st.metric(
                "Shortfall / Surplus",
                format_money(summary.shortfall, config.base_currency),
            )

        p1, p2 = st.columns(2)
        with p1:
            st.metric("P10 (Conservative)", format_money(summary.projected_value_p10, config.base_currency))
        with p2:
            st.metric("P90 (Optimistic)", format_money(summary.projected_value_p90, config.base_currency))


def _derive_expected_return_from_selection(selection: PortfolioSelection) -> float | None:
    """Derive weighted expected return from selected funds' 3Y returns."""
    components = [
        (selection.eu_stocks, selection.eu_stocks_weight),
        (selection.developed_world, selection.developed_world_weight),
        (selection.emerging_markets, selection.emerging_markets_weight),
        (selection.bonds, selection.bonds_weight),
    ]

    weighted_sum = 0.0
    used_weight = 0.0
    for fund, weight in components:
        if fund is None or fund.return_3y is None:
            continue
        weighted_sum += (fund.return_3y / 100.0) * weight
        used_weight += weight

    if used_weight <= 0:
        return None
    return weighted_sum / used_weight


def _success_label(probability: float) -> str:
    """Map probability of success to human-readable status label."""
    if probability >= 0.80:
        return "On Track"
    if probability >= 0.70:
        return "On Track"
    if probability >= 0.30:
        return "At Risk"
    return "Off Track"
