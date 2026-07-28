"""Goal planner view — define investment goals, map holdings, view probability of success.

Provides full CRUD for goals and goal-holding mappings, plus Monte Carlo
projections visualized with progress bars and percentile metrics.
"""

from __future__ import annotations

from datetime import date, datetime

import streamlit as st

from app.database import get_session
from app.providers.yfinance_provider import YFinanceProvider
from app.repositories.goal_repository import GoalRepository
from app.repositories.holding_repository import HoldingRepository
from app.services.goal_service import GoalService
from app.ui.components.goal_card import render_goal_card
from app.ui.components.state_indicators import (
    empty_state,
    error_message,
    render_info_popover,
    success_toast,
)
from app.utils.currency import format_money

_HOW_IT_WORKS_MARKDOWN = """
#### 🎲 What is a Monte Carlo simulation?
Think of it like a weather forecast for your money. We can't know exactly what the
market will do, so instead of guessing once, we simulate **1,000 different possible
futures** for your investments — some where the market does great, some where it
stumbles, and everything in between.

Your **Probability of Success** is simply: *out of those 1,000 imagined futures, how
many actually reached your goal?* If 720 out of 1,000 hit the target, that's a 72%
probability of success — just like "70% chance of rain" tells you how often it rained
in similar conditions.

---
#### 📈 A worked example
Say you have €10,000 today, add €200 every month, and want €50,000 in 10 years. We run
1,000 simulated versions of those 10 years, each with random ups and downs averaging
your expected return. If 650 of those 1,000 simulated futures end above €50,000, your
probability of success is **65%**.

---
#### 📖 Glossary
- **Probability of Success** — % of simulated futures that reached your target.
- **Median (typical outcome)** — the middle result: half of futures did better, half worse.
- **P10 (worst case)** — a pessimistic outcome; only 10% of futures were worse than this.
- **P90 (best case)** — an optimistic outcome; only 10% of futures were better than this.
- **Expected annual return** — the average yearly growth rate we assume (e.g. 7%).
- **Volatility** — how much returns bounce around year to year; higher = bumpier ride.
- **Shortfall / Surplus** — the gap between your target and the median projected outcome.
"""

_MONTE_CARLO_FORMULA = """
#### 🧮 The Monte Carlo Formula — Dumbed Down

Think of Monte Carlo like **rolling a loaded die 1,000 times** to see all the ways
your money could grow. Here's the recipe, step by step:

---

**Step 1 — Start with what you have today**
- You have **€X** today *(Current Value)*
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

**Step 4 — Count how many futures hit your target**

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
"""


def _render_add_goal_form(goal_repo: GoalRepository) -> None:
    """Render the form for adding a new goal."""
    st.subheader("➕ Define a New Goal")
    with st.form("add_goal_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input(
                "Goal Name", placeholder="e.g., Retire at 60, House in 7 years", key="goal_name"
            )
        with col2:
            target_amount = st.number_input(
                "Target Amount (EUR)", min_value=0.0, step=1000.0, key="goal_target"
            )

        col3, col4 = st.columns(2)
        with col3:
            target_date = st.date_input("Target Date", key="goal_date", value=date(2035, 1, 1))
        with col4:
            monthly_contribution = st.number_input(
                "Monthly Contribution (EUR)", min_value=0.0, step=50.0, key="goal_monthly"
            )

        submitted = st.form_submit_button("Create Goal")
        if submitted:
            if not name.strip():
                error_message(title="Missing name", message="Please enter a goal name.")
            elif target_amount <= 0:
                error_message(title="Invalid target", message="Target amount must be greater than zero.")
            else:
                goal_repo.add(
                    name=name.strip(),
                    target_amount=target_amount,
                    target_date=datetime.combine(target_date, datetime.min.time()),
                    monthly_contribution=monthly_contribution,
                )
                success_toast(f"✅ Created goal: {name.strip()}")
                st.rerun()


def _render_edit_goal_form(goal_repo: GoalRepository, goal_id: int) -> None:
    """Render inline edit form for a goal."""
    goal = goal_repo.get_by_id(goal_id)
    if goal is None:
        return

    with st.form(f"edit_goal_form_{goal_id}"):
        col1, col2 = st.columns(2)
        with col1:
            edit_name = st.text_input("Goal Name", value=goal.name, key=f"edit_name_{goal_id}")
        with col2:
            edit_target = st.number_input(
                "Target Amount (EUR)",
                value=float(goal.target_amount),
                min_value=0.0,
                step=1000.0,
                key=f"edit_target_{goal_id}",
            )

        col3, col4 = st.columns(2)
        with col3:
            edit_date = st.date_input(
                "Target Date",
                value=goal.target_date.date(),
                key=f"edit_date_{goal_id}",
            )
        with col4:
            edit_monthly = st.number_input(
                "Monthly Contribution (EUR)",
                value=float(goal.monthly_contribution),
                min_value=0.0,
                step=50.0,
                key=f"edit_monthly_{goal_id}",
            )

        col_save, col_cancel = st.columns(2)
        with col_save:
            if st.form_submit_button("Save Changes"):
                goal_repo.update(
                    goal_id,
                    name=edit_name,
                    target_amount=edit_target,
                    target_date=datetime.combine(edit_date, datetime.min.time()),
                    monthly_contribution=edit_monthly,
                )
                success_toast(f"✅ Updated goal: {edit_name}")
                st.session_state[f"editing_goal_{goal_id}"] = False
                st.rerun()
        with col_cancel:
            if st.form_submit_button("Cancel"):
                st.session_state[f"editing_goal_{goal_id}"] = False
                st.rerun()


def _render_mapping_section(
    goal_repo: GoalRepository,
    holding_repo: HoldingRepository,
    goal_id: int,
) -> None:
    """Render the holding mapping section for a goal."""
    st.markdown("**📊 Mapped Holdings**")
    mappings = goal_repo.get_mappings_for_goal(goal_id)
    holdings = holding_repo.get_all()
    holding_map = {h.id: h for h in holdings}

    if mappings:
        for mapping in mappings:
            holding = holding_map.get(mapping.holding_id)
            if holding is None:
                continue
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.text(f"{holding.ticker} — {holding.quantity:.2f} shares")
            with col2:
                st.text(f"Allocation: {mapping.allocation_pct:.0f}%")
            with col3:
                if st.button("Unmap", key=f"unmap_{mapping.id}"):
                    goal_repo.delete_mapping(mapping.id)
                    success_toast(f"🗑️ Unmapped {holding.ticker}")
                    st.rerun()
    else:
        st.info("No holdings mapped to this goal yet.")

    # Add mapping form
    available_holdings = [h for h in holdings if h.id not in {m.holding_id for m in mappings}]
    if available_holdings:
        st.markdown("**Map a holding to this goal:**")
        col_h, col_pct, col_btn = st.columns([3, 2, 1])
        with col_h:
            selected_ticker = st.selectbox(
                "Select Holding",
                options=[h.ticker for h in available_holdings],
                key=f"map_holding_{goal_id}",
                label_visibility="collapsed",
            )
        with col_pct:
            alloc_pct = st.number_input(
                "Allocation %",
                min_value=0.0,
                max_value=100.0,
                value=100.0,
                step=10.0,
                key=f"map_pct_{goal_id}",
                label_visibility="collapsed",
            )
        with col_btn:
            if st.button("Map", key=f"map_btn_{goal_id}"):
                selected_holding = next(
                    (h for h in available_holdings if h.ticker == selected_ticker), None
                )
                if selected_holding:
                    goal_repo.add_mapping(goal_id, selected_holding.id, alloc_pct)
                    success_toast(f"✅ Mapped {selected_ticker} to goal")
                    st.rerun()
    elif not holdings:
        st.caption("💡 Add holdings first on the **💼 Holdings** page.")


def _render_assumptions_section() -> tuple[float, float, int]:
    """Render market assumptions controls and return values."""
    with st.expander("⚙️ Monte Carlo Assumptions", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            expected_return = st.slider(
                "Expected Annual Return (%)",
                min_value=0.0,
                max_value=15.0,
                value=7.0,
                step=0.5,
                help=(
                    "How much your investments are assumed to grow each year, on "
                    "average (7% is a common long-term stock-market assumption)."
                ),
            )
        with col2:
            volatility = st.slider(
                "Annual Volatility (%)",
                min_value=5.0,
                max_value=40.0,
                value=15.0,
                step=1.0,
                help=(
                    "How much returns swing year to year — higher means a bumpier "
                    "ride, even if the long-term average stays the same."
                ),
            )
        with col3:
            num_sims = st.select_slider(
                "Simulations",
                options=[100, 500, 1000, 5000],
                value=1000,
                help=(
                    "Number of possible futures we simulate. More = a smoother, "
                    "more reliable probability estimate, but slower to compute."
                ),
            )
        return expected_return / 100.0, volatility / 100.0, num_sims


def render_goal_planner() -> None:
    """Render the goal-based investing planner view."""
    st.title("🎯 Goal-Based Investing Planner")
    st.markdown(
        "Define your life goals, map your holdings to each goal, "
        "and see your **probability of success** based on Monte Carlo simulation."
    )
    render_info_popover("How does this work?", _HOW_IT_WORKS_MARKDOWN)
    render_info_popover(
        "Monte Carlo formula explained (dumbed down)",
        _MONTE_CARLO_FORMULA,
        icon="🧮",
    )

    session = get_session()
    goal_repo = GoalRepository(session)
    holding_repo = HoldingRepository(session)
    provider = YFinanceProvider()
    goal_service = GoalService(goal_repo, holding_repo, provider, session)

    # Add goal form
    _render_add_goal_form(goal_repo)

    st.markdown("---")

    # Get all goals
    goals = goal_repo.get_all()

    if not goals:
        empty_state(
            title="No goals defined yet",
            message="Use the form above to define your first investment goal. "
            "Examples: *Retire at 60*, *House down payment in 7 years*, *College tuition fund*.",
        )
        session.close()
        return

    # Market assumptions
    expected_return, volatility, num_sims = _render_assumptions_section()

    st.markdown("---")

    # Refresh button
    if st.button("🔄 Recalculate Projections"):
        st.rerun()

    # Project all goals
    holdings = holding_repo.get_all()
    with st.spinner(f"Running {num_sims} Monte Carlo simulations per goal..."):
        projections = goal_service.project_all_goals(
            holdings=holdings,
            expected_return=expected_return,
            volatility=volatility,
            num_simulations=num_sims,
        )

    # Render each goal card
    for goal, projection in zip(goals, projections, strict=False):
        render_goal_card(projection)

        # Edit / Delete buttons
        col_edit, col_delete, col_map = st.columns([1, 1, 2])
        with col_edit:
            if st.button("✏️ Edit", key=f"edit_btn_{goal.id}"):
                st.session_state[f"editing_goal_{goal.id}"] = True
                st.rerun()
        with col_delete:
            if st.button("🗑️ Delete", key=f"del_btn_{goal.id}"):
                st.session_state[f"deleting_goal_{goal.id}"] = True
                st.rerun()

        # Edit form
        if st.session_state.get(f"editing_goal_{goal.id}"):
            _render_edit_goal_form(goal_repo, goal.id)

        # Delete confirmation
        if st.session_state.get(f"deleting_goal_{goal.id}"):
            st.warning(f"Are you sure you want to delete '{goal.name}'? This will remove all holding mappings.")
            col_confirm, col_cancel = st.columns(2)
            with col_confirm:
                if st.button("Yes, Delete", key=f"confirm_del_{goal.id}"):
                    goal_repo.delete(goal.id)
                    success_toast(f"🗑️ Deleted goal: {goal.name}")
                    st.session_state[f"deleting_goal_{goal.id}"] = False
                    st.rerun()
            with col_cancel:
                if st.button("Cancel", key=f"cancel_del_{goal.id}"):
                    st.session_state[f"deleting_goal_{goal.id}"] = False
                    st.rerun()

        # Mapping section
        with st.expander("Manage Holding Mappings", expanded=False):
            _render_mapping_section(goal_repo, holding_repo, goal.id)

        st.markdown("---")

    # Summary
    if projections:
        st.subheader("📋 Goal Summary")
        total_target = sum(p.target_amount for p in projections)
        total_current = sum(p.current_value for p in projections)
        avg_prob = sum(p.probability_of_success for p in projections) / len(projections)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Target", format_money(total_target, projections[0].currency))
        with col2:
            st.metric("Total Current Value", format_money(total_current, projections[0].currency))
        with col3:
            st.metric("Avg Probability of Success", f"{avg_prob * 100:.0f}%")

    session.close()
