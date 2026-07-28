"""Four-fund portfolio builder view — Bogleheads strategy page.

Provides tabbed categories (EU Stocks, Developed World, Emerging
Markets, Bonds), fund comparison cards with TER/AUM/returns, a
portfolio builder with allocation weights, and weighted portfolio
TER calculation.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.config import config
from app.data.four_fund_universe import FundCategory
from app.database import get_session
from app.models.fund_profile import FundProfile, PortfolioSelection
from app.providers.yfinance_provider import YFinanceProvider
from app.repositories.four_fund_plan_repository import FourFundPlanRepository
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository
from app.services.fund_comparison_service import FundComparisonService
from app.services.monte_carlo_service import (
    DEFAULT_PERCENTILES,
    MonteCarloConfig,
    MonteCarloResult,
    build_covariance_from_prices,
    estimate_portfolio_params,
    percentiles_to_csv,
    run_monte_carlo,
    run_multi_asset_monte_carlo,
    solve_required_contribution,
)
from app.services.portfolio_service import PortfolioService
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

_MONTE_CARLO_FORMULA = """
#### 🧮 The Monte Carlo Formula — Dumbed Down

Think of Monte Carlo like **rolling a loaded die 1,000 times** to see all the ways
your money could grow. Here's the recipe, step by step:

---

**Step 1 — Start with what you have today**
- You have **€X** today *(Current Portfolio Value)*
- You add **€Y** every month *(Monthly Contribution)*

---

**Step 2 — Each month, your money grows (or shrinks) randomly**

Most months you gain a little. Some months you lose. We simulate this with a
"bell curve" random number — usually near zero, sometimes bigger or smaller.

```
New Value = Old Value × (1 + growth)
```

Where `growth` has two parts:

| Part | What it means | Formula |
|------|---------------|---------|
| 📈 Average growth | Your expected yearly return, split into 12 monthly bits | `Expected Return ÷ 12` |
| 🎲 Random bump | The surprise part — how much returns swing | `Volatility ÷ √12 × random number` |

The **random number** comes from a bell curve (normal distribution). It's usually
close to 0, but sometimes it's +2 or -2, giving you a good or bad month.

---

**Step 3 — Repeat for every month, then repeat the whole thing 1,000 times**

- **One simulation** = walk through all the months (e.g., 120 months for 10 years),
  applying random growth each month
- We do this **1,000 times** (or more) to see the full range of possible outcomes —
  some great, some terrible, most in the middle

---

**Step 4 — Adjust for fees and inflation (optional but realistic)**

- **Fees (TER)**: subtract the fund cost from your expected return *before*
  simulating. If you expect 7% but pay 0.2% in fees, we simulate with 6.8%.
- **Inflation**: divide the final value by `(1 + inflation)^years` to show
  results in **today's money**. €100,000 in 10 years isn't worth €100,000 today
  if prices have risen!

---

**Step 5 — Count how many futures hit your target**

If **720 out of 1,000** simulated futures reached your target → **72% probability
of success**. Just like "70% chance of rain" — it rained in 70% of similar
conditions.

---

#### 🔬 The actual math (for the curious)

```
Monthly growth = (μ - fees) / 12 + (σ / √12) × Z

  μ     = expected annual return (e.g., 0.07 for 7%)
  σ     = annual volatility (e.g., 0.15 for 15%)
  Z     = random draw from standard normal distribution N(0, 1)
  fees  = annual fee drag / TER (e.g., 0.002 for 0.2%)
```

Each month:
```
value = value × (1 + monthly_growth) + contribution
```

After all months, adjust for inflation (if "real terms" is on):
```
real_value = final_value / (1 + inflation_rate) ^ years
```

For **multi-fund mode**, instead of one growth rate, we simulate each fund
separately using its own return and a **correlation matrix** (how the funds
move together), then combine them by your allocation weights.
"""


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

        # Auto-refresh stale session cache from older versions where prices
        # were still stored in trading currency (e.g., GBp for LSE tickers).
        base_ccy = config.base_currency.upper()
        has_non_base = any(
            p.is_available and str(p.currency).upper() != base_ccy
            for p in profiles
        )
        if has_non_base:
            with st.spinner("Normalizing fund prices to base currency..."):
                profiles = service.fetch_all_profiles()
                st.session_state["four_fund_profiles"] = profiles

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


def _ensure_weight_defaults() -> None:
    """Initialize allocation weight keys once (no widget default value=)."""
    defaults = {
        "weight_eu": 30,
        "weight_dev": 30,
        "weight_em": 10,
        "weight_bonds": 30,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


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

    # Allocation weight inputs (defaults via session_state only — avoids
    # Streamlit warning when loading a saved plan into the same keys).
    st.markdown("**Allocation Weights** (must sum to 100%)")
    _ensure_weight_defaults()
    w_col1, w_col2, w_col3, w_col4 = st.columns(4)

    with w_col1:
        eu_weight = st.number_input(
            "EU Stocks (%)", min_value=0, max_value=100, step=5,
            key="weight_eu",
        )
    with w_col2:
        dev_weight = st.number_input(
            "Developed World (%)", min_value=0, max_value=100, step=5,
            key="weight_dev",
        )
    with w_col3:
        em_weight = st.number_input(
            "Emerging Markets (%)", min_value=0, max_value=100, step=5,
            key="weight_em",
        )
    with w_col4:
        bonds_weight = st.number_input(
            "Bonds (%)", min_value=0, max_value=100, step=5,
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
        portfolio_ter=portfolio_ter,
        service=service,
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
    portfolio_ter: float,
    service: FundComparisonService,
) -> None:
    """Render Monte Carlo simulation controls based on current allocation."""
    st.markdown("### Monte Carlo Projection")
    render_info_popover(
        "About this simulation",
        """
Monte Carlo runs thousands of random market paths using geometric Brownian
motion. Results show a **percentile ladder** of outcomes, tail risk
(**VaR / CVaR**), optional **inflation-adjusted** (real) values, and
**fee drag** from your portfolio TER.

- **Blended GBM**: one portfolio μ/σ path (fast default)
- **Correlated multi-fund**: four asset paths with historical covariance
- **Contribution solver**: finds the monthly savings rate for a target success %
        """,
        icon="🎲",
    )
    render_info_popover(
        "Monte Carlo formula explained (dumbed down)",
        _MONTE_CARLO_FORMULA,
        icon="🧮",
    )

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
    holdings_value = _get_holdings_total_value()
    default_current = 25_000.0 if holdings_value <= 0 else float(holdings_value)

    fee_drag_default = max(0.0, portfolio_ter / 100.0)

    # Historical μ/σ estimate from fund price history (cached in session).
    hist_params = st.session_state.get("four_fund_mc_hist_params")
    if st.button("Estimate μ/σ from fund history", key="four_fund_mc_estimate_hist"):
        with st.spinner("Fetching 5Y histories and estimating portfolio parameters..."):
            hist_params = _estimate_params_from_history(selection)
            st.session_state["four_fund_mc_hist_params"] = hist_params

    if hist_params is not None:
        hist_mu, hist_sigma = hist_params
        st.caption(
            f"History-derived annual return ≈ {hist_mu * 100:.2f}%, "
            f"volatility ≈ {hist_sigma * 100:.2f}%"
        )
    elif derived_expected is not None:
        st.caption(
            f"Using weighted 3Y return as a starting point: {derived_expected * 100:.2f}%"
        )

    if holdings_value > 0:
        st.caption(
            f"Holdings total value available as starting point: "
            f"{format_money(holdings_value, config.base_currency)}"
        )

    if hist_params is not None:
        default_expected_pct = max(0.0, min(20.0, hist_params[0] * 100))
        default_vol_pct = max(5.0, min(40.0, hist_params[1] * 100))
    elif derived_expected is not None:
        default_expected_pct = max(0.0, min(20.0, derived_expected * 100))
        default_vol_pct = 15.0
    else:
        default_expected_pct = 7.0
        default_vol_pct = 15.0

    if "four_fund_mc_current_value" not in st.session_state:
        st.session_state["four_fund_mc_current_value"] = default_current

    col1, col2, col3 = st.columns(3)
    with col1:
        current_value = st.number_input(
            f"Current Portfolio Value ({config.base_currency})",
            min_value=0.0,
            step=1_000.0,
            key="four_fund_mc_current_value",
            help=(
                "How much your portfolio is worth today — the starting point for "
                "every simulated future. If you have holdings tracked in this app, "
                "their total value is used as the default."
            ),
        )
        target_value = st.number_input(
            f"Target Value ({config.base_currency})",
            min_value=0.0,
            value=100_000.0,
            step=1_000.0,
            key="four_fund_mc_target_value",
            help=(
                "The amount you want to reach by the end of the time horizon. "
                "The simulator counts how many of the 1,000 futures hit or exceed "
                "this number to calculate your probability of success."
            ),
        )
        monthly_contribution = st.number_input(
            f"Monthly Contribution ({config.base_currency})",
            min_value=0.0,
            value=500.0,
            step=50.0,
            key="four_fund_mc_monthly_contribution",
            help=(
                "How much you add to your portfolio every month. More "
                "contributions = higher ending values and a better probability "
                "of hitting your target."
            ),
        )
    with col2:
        years = st.slider(
            "Years to Target",
            min_value=1,
            max_value=40,
            value=10,
            key="four_fund_mc_years",
            help=(
                "How long you plan to invest before reaching your target. "
                "Longer horizons give compounding more time to work, but also "
                "mean more months of potential market swings."
            ),
        )
        expected_return_pct = st.slider(
            "Expected Annual Return (%)",
            min_value=0.0,
            max_value=20.0,
            value=float(default_expected_pct),
            step=0.5,
            key="four_fund_mc_expected_return",
            help=(
                "The average yearly growth rate you assume for your portfolio "
                "(e.g., 7% is a common long-term stock-market assumption). "
                "This is the 'μ' in the formula — the center of the bell curve. "
                "Higher = more growth, but be realistic!"
            ),
        )
        volatility_pct = st.slider(
            "Annual Volatility (%)",
            min_value=1.0,
            max_value=50.0,
            value=float(default_vol_pct),
            step=0.5,
            key="four_fund_mc_volatility",
            help=(
                "How much returns swing year to year — the 'σ' in the formula. "
                "Higher = a bumpier ride with wider outcome spread. Stocks ≈ "
                "15–20%, bonds ≈ 5–8%. This controls the size of the random bump."
            ),
        )
        num_sims = st.select_slider(
            "Simulations",
            options=[100, 500, 1000, 5000],
            value=1000,
            key="four_fund_mc_simulations",
            help=(
                "Number of possible futures we simulate. More = a smoother, "
                "more reliable probability estimate, but slower to compute. "
                "1,000 is a good balance; 5,000 is very precise."
            ),
        )
    with col3:
        inflation_pct = st.slider(
            "Inflation (%)",
            min_value=0.0,
            max_value=10.0,
            value=2.0,
            step=0.1,
            key="four_fund_mc_inflation",
            help=(
                "The rate at which prices rise each year (e.g., 2% is a common "
                "central-bank target). When 'real terms' is on, we divide the "
                "final value by inflation so results are shown in today's money."
            ),
        )
        fee_drag_pct = st.number_input(
            "Annual Fee Drag / TER (%)",
            min_value=0.0,
            max_value=5.0,
            value=float(round(fee_drag_default * 100, 4)),
            step=0.01,
            key="four_fund_mc_fee_drag",
            help=(
                "Defaults to weighted portfolio TER. This is the annual cost "
                "of your funds, subtracted from your expected return *before* "
                "simulating. If you expect 7% but pay 0.2% in fees, we simulate "
                "with 6.8%."
            ),
        )
        contribution_timing = st.selectbox(
            "Contribution Timing",
            options=["start", "end"],
            format_func=lambda x: "Start of month" if x == "start" else "End of month",
            key="four_fund_mc_timing",
            help=(
                "When in the month your contribution is added. 'Start of month' "
                "means the contribution grows for that month; 'End of month' "
                "means it's added after growth. Start = slightly higher results."
            ),
        )
        seed_enabled = st.checkbox(
            "Use fixed seed",
            value=True,
            key="four_fund_mc_seed_on",
            help=(
                "A fixed seed makes the random numbers reproducible — the same "
                "inputs always give the same results. Turn off for fresh random "
                "draws each run."
            ),
        )
        seed = st.number_input(
            "Seed",
            min_value=0,
            max_value=1_000_000,
            value=42,
            step=1,
            key="four_fund_mc_seed",
            disabled=not seed_enabled,
            help=(
                "The starting number for the random generator. Same seed = "
                "same simulation results. Change it to get a different random "
                "sample."
            ),
        )

    opt_col1, opt_col2 = st.columns(2)
    with opt_col1:
        real_terms = st.checkbox(
            "Show results in real (inflation-adjusted) terms",
            value=True,
            key="four_fund_mc_real",
            help=(
                "When on, results are shown in today's purchasing power — "
                "€100,000 in 10 years is divided by inflation so you see what "
                "it's really worth now. When off, results are in future nominal "
                "euros."
            ),
        )
        multi_asset = st.checkbox(
            "Correlated multi-fund paths",
            value=False,
            key="four_fund_mc_multi",
            help=(
                "Uses historical covariance across the four selected funds. "
                "Instead of one blended growth rate, each fund is simulated "
                "separately with its own return and how it moves relative to "
                "the others, then combined by your weights. More realistic, "
                "but slower."
            ),
        )
    with opt_col2:
        target_success_pct = st.slider(
            "Target success probability (%)",
            min_value=50,
            max_value=95,
            value=80,
            step=5,
            key="four_fund_mc_target_success",
            help=(
                "Used by the 'Solve contribution' button — it searches for the "
                "monthly savings rate that would give you this chance of "
                "hitting your target. 80% is a common planning threshold."
            ),
        )
        percentile_preset = st.selectbox(
            "Percentile ladder",
            options=["P5–P95 standard", "P10/P50/P90 only", "Deciles"],
            key="four_fund_mc_pct_preset",
            help=(
                "Which percentile bands to show in the results. 'P5–P95' shows "
                "the wide spread; 'P10/P50/P90' is a simpler worst/typical/best "
                "view; 'Deciles' splits outcomes into 10% buckets."
            ),
        )

    percentiles = _percentile_preset(percentile_preset)

    run_col, solve_col = st.columns(2)
    with run_col:
        run_clicked = st.button("Run Monte Carlo", key="run_four_fund_mc", type="primary")
    with solve_col:
        solve_clicked = st.button(
            f"Solve contribution for {target_success_pct}% success",
            key="solve_four_fund_mc",
        )

    rng_seed = int(seed) if seed_enabled else None
    expected_return = expected_return_pct / 100.0
    volatility = volatility_pct / 100.0
    inflation_rate = inflation_pct / 100.0
    fee_drag = fee_drag_pct / 100.0

    if solve_clicked:
        with st.spinner("Searching required monthly contribution..."):
            required = solve_required_contribution(
                current_value=current_value,
                years=float(years),
                expected_return=expected_return,
                volatility=volatility,
                target_amount=target_value,
                target_probability=target_success_pct / 100.0,
                num_simulations=min(int(num_sims), 1000),
                inflation_rate=inflation_rate,
                fee_drag=fee_drag,
                contribution_timing=str(contribution_timing),
                seed=rng_seed,
                real_terms=real_terms,
            )
            st.session_state["four_fund_mc_required_contrib"] = required

    required_contrib = st.session_state.get("four_fund_mc_required_contrib")
    if isinstance(required_contrib, (int, float)):
        st.info(
            f"Required monthly contribution for ~{target_success_pct}% success: "
            f"**{format_money(float(required_contrib), config.base_currency)}**"
        )

    if run_clicked:
        with st.spinner(f"Running {num_sims} simulations..."):
            try:
                if multi_asset:
                    result = _run_multi_asset_simulation(
                        selection=selection,
                        current_value=current_value,
                        monthly_contribution=monthly_contribution,
                        years=float(years),
                        target_amount=target_value,
                        num_simulations=int(num_sims),
                        inflation_rate=inflation_rate,
                        contribution_timing=str(contribution_timing),
                        seed=rng_seed,
                        percentiles=percentiles,
                        real_terms=real_terms,
                        fallback_mu=expected_return,
                        fallback_sigma=volatility,
                        fee_drag=fee_drag,
                    )
                else:
                    result = run_monte_carlo(
                        MonteCarloConfig(
                            current_value=current_value,
                            monthly_contribution=monthly_contribution,
                            years=float(years),
                            expected_return=expected_return,
                            volatility=volatility,
                            num_simulations=int(num_sims),
                            target_amount=target_value,
                            inflation_rate=inflation_rate,
                            fee_drag=fee_drag,
                            contribution_timing=str(contribution_timing),
                            seed=rng_seed,
                            percentiles=percentiles,
                            real_terms=real_terms,
                            store_yearly_paths=True,
                        )
                    )
                st.session_state["four_fund_mc_result"] = result
            except Exception as exc:
                error_message(
                    title="Simulation failed",
                    message=str(exc),
                    recovery_hint="Try blended mode or fewer simulations.",
                )

    result = st.session_state.get("four_fund_mc_result")
    if isinstance(result, MonteCarloResult):
        _render_monte_carlo_results(result, target_value=target_value)


def _render_monte_carlo_results(result: MonteCarloResult, *, target_value: float) -> None:
    """Render metrics, percentile table, histogram, fan chart, and CSV export."""
    summary = result.summary
    ccy = config.base_currency
    status = _success_label(summary.probability_of_success)
    st.markdown(f"**Status:** {status}")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(
            "Probability of Success",
            f"{summary.probability_of_success * 100:.0f}%",
            help=(
                "Out of all simulated futures, the percentage that reached or "
                "exceeded your target value. Like '70% chance of rain' — in "
                "70% of similar scenarios, it rained."
            ),
        )
    with m2:
        st.metric(
            "Median Outcome",
            format_money(summary.projected_value_median, ccy),
            help=(
                "The typical outcome — half of simulated futures ended above "
                "this value, half below. Also called P50. This is your 'most "
                "likely' landing spot."
            ),
        )
    with m3:
        st.metric(
            "Mean Outcome",
            format_money(summary.mean, ccy),
            help=(
                "The simple average of all simulated endings. Can be higher "
                "than the median because a few very good futures pull it up. "
                "Use median for 'typical', mean for 'average'."
            ),
        )
    with m4:
        st.metric(
            "Shortfall / Surplus",
            format_money(summary.shortfall, ccy),
            help=(
                "The gap between your target and the median projected outcome. "
                "Positive = you're short by this much; negative = you have a "
                "surplus above your target."
            ),
        )

    t1, t2, t3, t4 = st.columns(4)
    with t1:
        st.metric(
            "Std Dev",
            format_money(summary.std, ccy),
            help=(
                "Standard deviation — how spread out the outcomes are. Higher "
                "= more uncertainty. If this is large relative to the median, "
                "your results are very uncertain."
            ),
        )
    with t2:
        st.metric(
            "Min",
            format_money(summary.min_value, ccy),
            help=(
                "The worst single outcome across all simulations. This is the "
                "absolute floor — one very unlucky future. Don't plan around "
                "this, but it shows the downside extreme."
            ),
        )
    with t3:
        st.metric(
            "VaR (5%)",
            format_money(summary.var_5, ccy),
            help=(
                "Value at Risk (5%) — the outcome below which only the worst "
                "5% of futures fell. In plain English: 'There's a 5% chance "
                "you end up with less than this.' A key tail-risk metric."
            ),
        )
    with t4:
        st.metric(
            "CVaR (5%)",
            format_money(summary.cvar_5, ccy),
            help=(
                "Conditional Value at Risk (5%) — the average of the worst 5% "
                "of outcomes. If things go badly, this is what you'd expect. "
                "More conservative than VaR because it averages the tail, not "
                "just the cutoff."
            ),
        )

    # Percentile ladder metrics
    ordered = sorted(summary.percentiles.items())
    st.markdown("**Percentile ladder (terminal wealth)**")
    cols = st.columns(min(len(ordered), 7))
    for idx, (p, value) in enumerate(ordered):
        with cols[idx % len(cols)]:
            st.metric(
                f"P{p:g}",
                format_money(value, ccy),
                help=(
                    f"The P{p:g} percentile — {p:g}% of simulated futures ended "
                    f"below this value, {100 - p:g}% ended above. "
                    f"{'Low/worst case' if p <= 25 else ('Typical' if p == 50 else 'High/best case')}."
                ),
            )

    table_df = pd.DataFrame(
        {
            "Percentile": [f"P{p:g}" for p, _ in ordered],
            f"Value ({ccy})": [v for _, v in ordered],
        }
    )
    extra_df = pd.DataFrame(
        {
            "Percentile": ["Mean", "Std", "Min", "Max", "VaR 5%", "CVaR 5%", "Success %"],
            f"Value ({ccy})": [
                summary.mean,
                summary.std,
                summary.min_value,
                summary.max_value,
                summary.var_5,
                summary.cvar_5,
                summary.probability_of_success * 100.0,
            ],
        }
    )
    st.dataframe(pd.concat([table_df, extra_df], ignore_index=True), hide_index=True, width="stretch")

    chart_tab, fan_tab = st.tabs(["Terminal distribution", "Yearly confidence bands"])
    with chart_tab:
        if result.final_values:
            hist_df = pd.DataFrame({"Terminal value": result.final_values})
            fig = px.histogram(
                hist_df,
                x="Terminal value",
                nbins=40,
                title="Distribution of terminal portfolio values",
            )
            fig.add_vline(
                x=target_value,
                line_dash="dash",
                line_color="orange",
                annotation_text="Target",
            )
            fig.add_vline(
                x=summary.projected_value_median,
                line_dash="dot",
                line_color="green",
                annotation_text="Median",
            )
            fig.update_layout(yaxis_title="Simulations", xaxis_title=f"Value ({ccy})")
            st.plotly_chart(fig, width="stretch")

            box_fig = px.box(
                hist_df,
                x="Terminal value",
                title="Terminal value box plot",
                points=False,
            )
            st.plotly_chart(box_fig, width="stretch")

    with fan_tab:
        if result.yearly_bands:
            fig = go.Figure()
            years = [b.year for b in result.yearly_bands]
            band_keys = sorted({p for b in result.yearly_bands for p in b.percentiles})
            # Prefer outer bands for fill if present.
            lower_key = 10.0 if 10.0 in band_keys else (band_keys[0] if band_keys else None)
            mid_key = 50.0 if 50.0 in band_keys else None
            upper_key = 90.0 if 90.0 in band_keys else (band_keys[-1] if band_keys else None)

            if lower_key is not None and upper_key is not None:
                lower = [b.percentiles.get(lower_key, 0.0) for b in result.yearly_bands]
                upper = [b.percentiles.get(upper_key, 0.0) for b in result.yearly_bands]
                fig.add_trace(
                    go.Scatter(
                        x=years + years[::-1],
                        y=upper + lower[::-1],
                        fill="toself",
                        fillcolor="rgba(99, 110, 250, 0.2)",
                        line={"color": "rgba(255,255,255,0)"},
                        name=f"P{lower_key:g}–P{upper_key:g}",
                        hoverinfo="skip",
                    )
                )
            if mid_key is not None:
                mid = [b.percentiles.get(mid_key, 0.0) for b in result.yearly_bands]
                fig.add_trace(
                    go.Scatter(
                        x=years,
                        y=mid,
                        mode="lines",
                        name=f"P{mid_key:g}",
                        line={"color": "#636EFA", "width": 2},
                    )
                )
            for p in band_keys:
                if p in {lower_key, mid_key, upper_key}:
                    continue
                ys = [b.percentiles.get(p, 0.0) for b in result.yearly_bands]
                fig.add_trace(
                    go.Scatter(
                        x=years,
                        y=ys,
                        mode="lines",
                        name=f"P{p:g}",
                        line={"width": 1, "dash": "dot"},
                    )
                )
            fig.add_hline(
                y=target_value,
                line_dash="dash",
                line_color="orange",
                annotation_text="Target",
            )
            fig.update_layout(
                title="Yearly percentile fan chart",
                xaxis_title="Year",
                yaxis_title=f"Portfolio value ({ccy})",
            )
            st.plotly_chart(fig, width="stretch")
        else:
            st.caption("No yearly path bands available for this run.")

    csv_text = percentiles_to_csv(summary, yearly_bands=result.yearly_bands)
    st.download_button(
        "Download percentile CSV",
        data=csv_text,
        file_name="monte_carlo_percentiles.csv",
        mime="text/csv",
        key="four_fund_mc_csv",
    )


def _percentile_preset(name: str) -> tuple[float, ...]:
    if name == "P10/P50/P90 only":
        return (10.0, 50.0, 90.0)
    if name == "Deciles":
        return tuple(float(p) for p in range(10, 100, 10))
    return DEFAULT_PERCENTILES


def _get_holdings_total_value() -> float:
    """Best-effort portfolio holdings total in base currency."""
    session = get_session()
    try:
        holding_repo = HoldingRepository(session)
        price_repo = PriceRepository(session)
        provider = YFinanceProvider()
        service = PortfolioService(holding_repo, price_repo, provider, session)
        holdings = holding_repo.get_all()
        if not holdings:
            return 0.0
        return float(service.calculate_total_value(holdings))
    except Exception:
        return 0.0
    finally:
        session.close()


def _estimate_params_from_history(
    selection: PortfolioSelection,
) -> tuple[float, float] | None:
    """Estimate portfolio μ/σ from 5Y price history of selected funds."""
    components = _selection_components(selection)
    provider = YFinanceProvider()
    closes: dict[str, list[float]] = {}
    weights: dict[str, float] = {}
    for fund, weight in components:
        if fund is None or weight <= 0:
            continue
        history = provider.get_price_history_5y(fund.ticker)
        if history is None or len(history.closes) < 10:
            continue
        closes[fund.ticker] = list(history.closes)
        weights[fund.ticker] = weight
    if len(closes) < 1:
        return None
    return estimate_portfolio_params(closes, weights)


def _run_multi_asset_simulation(
    *,
    selection: PortfolioSelection,
    current_value: float,
    monthly_contribution: float,
    years: float,
    target_amount: float,
    num_simulations: int,
    inflation_rate: float,
    contribution_timing: str,
    seed: int | None,
    percentiles: tuple[float, ...],
    real_terms: bool,
    fallback_mu: float,
    fallback_sigma: float,
    fee_drag: float,
) -> MonteCarloResult:
    """Run correlated multi-fund MC, falling back to blended GBM if needed."""
    components = _selection_components(selection)
    provider = YFinanceProvider()
    tickers: list[str] = []
    weights: list[float] = []
    mus: list[float] = []
    fees: list[float] = []
    closes: dict[str, list[float]] = {}

    for fund, weight in components:
        if fund is None or weight <= 0:
            continue
        history = provider.get_price_history_5y(fund.ticker)
        if history is None or len(history.closes) < 10:
            continue
        tickers.append(fund.ticker)
        weights.append(weight)
        closes[fund.ticker] = list(history.closes)
        if fund.return_3y is not None:
            mus.append(fund.return_3y / 100.0)
        else:
            mus.append(fallback_mu)
        fees.append((fund.ter or 0.0) / 100.0)

    if len(tickers) < 2:
        # Not enough history — blended path with fee drag.
        return run_monte_carlo(
            MonteCarloConfig(
                current_value=current_value,
                monthly_contribution=monthly_contribution,
                years=years,
                expected_return=fallback_mu,
                volatility=fallback_sigma,
                num_simulations=num_simulations,
                target_amount=target_amount,
                inflation_rate=inflation_rate,
                fee_drag=fee_drag,
                contribution_timing=contribution_timing,
                seed=seed,
                percentiles=percentiles,
                real_terms=real_terms,
                store_yearly_paths=True,
            )
        )

    cov = build_covariance_from_prices(closes, tickers)
    if cov is None:
        return run_monte_carlo(
            MonteCarloConfig(
                current_value=current_value,
                monthly_contribution=monthly_contribution,
                years=years,
                expected_return=fallback_mu,
                volatility=fallback_sigma,
                num_simulations=num_simulations,
                target_amount=target_amount,
                inflation_rate=inflation_rate,
                fee_drag=fee_drag,
                contribution_timing=contribution_timing,
                seed=seed,
                percentiles=percentiles,
                real_terms=real_terms,
                store_yearly_paths=True,
            )
        )

    return run_multi_asset_monte_carlo(
        current_value=current_value,
        monthly_contribution=monthly_contribution,
        years=years,
        weights=weights,
        expected_returns=mus,
        covariance=cov,
        num_simulations=num_simulations,
        target_amount=target_amount,
        inflation_rate=inflation_rate,
        fee_drags=fees,
        contribution_timing=contribution_timing,
        seed=seed,
        percentiles=percentiles,
        real_terms=real_terms,
        store_yearly_paths=True,
    )


def _selection_components(
    selection: PortfolioSelection,
) -> list[tuple[FundProfile | None, float]]:
    return [
        (selection.eu_stocks, selection.eu_stocks_weight),
        (selection.developed_world, selection.developed_world_weight),
        (selection.emerging_markets, selection.emerging_markets_weight),
        (selection.bonds, selection.bonds_weight),
    ]


def _derive_expected_return_from_selection(selection: PortfolioSelection) -> float | None:
    """Derive weighted expected return from selected funds' 3Y returns."""
    weighted_sum = 0.0
    used_weight = 0.0
    for fund, weight in _selection_components(selection):
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
