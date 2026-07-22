"""Fund comparison card component — displays a single ETF with comparison metrics.

Renders fund name, ticker, exchange badge, TER (with color coding),
AUM, returns (1Y/3Y/5Y), replication method, distribution policy,
and a select button for the portfolio builder.
"""

from __future__ import annotations

import math

import streamlit as st

from app.models.fund_profile import FundProfile


def _ter_color(ter: float) -> str:
    """Return a color indicator based on TER.

    Bogleheads principle: lower costs are better.
    - Green: TER < 0.20%
    - Yellow: 0.20% <= TER < 0.50%
    - Red: TER >= 0.50%

    Args:
        ter: Total Expense Ratio as a percentage.

    Returns:
        Color string ("green", "orange", or "red").
    """
    if ter < 0.20:
        return "green"
    elif ter < 0.50:
        return "orange"
    return "red"


def _format_aum(aum: float) -> str:
    """Format AUM into a human-readable string.

    Args:
        aum: Assets Under Management in EUR (raw number).

    Returns:
        Formatted string (e.g., "EUR 12.5B", "EUR 850.0M").
    """
    if aum >= 1_000_000_000:
        return f"EUR {aum / 1_000_000_000:.1f}B"
    elif aum >= 1_000_000:
        return f"EUR {aum / 1_000_000:.1f}M"
    elif aum > 0:
        return f"EUR {aum:,.0f}"
    return "N/A"


def _format_return(value: float | None) -> str:
    """Format a return value with sign and color indicator.

    Treats NaN (which yfinance sometimes returns instead of None) as
    unavailable so it renders as "N/A" rather than "+nan%".

    Args:
        value: Return as a percentage, or None.

    Returns:
        Formatted string (e.g., "+8.20%", "N/A").
    """
    if value is None:
        return "N/A"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if not math.isfinite(numeric):
        return "N/A"
    return f"{numeric:+.2f}%"


def render_fund_comparison_card(
    profile: FundProfile,
    is_selected: bool = False,
    is_best_in_class: bool = False,
    on_select: callable | None = None,
    key_prefix: str = "",
) -> None:
    """Render a single fund as a comparison card.

    Args:
        profile: The FundProfile to display.
        is_selected: Whether this fund is currently selected in the portfolio.
        is_best_in_class: Whether this fund is the best (lowest TER) in its category.
        on_select: Optional callback for the select button.
        key_prefix: Prefix for Streamlit element keys to ensure uniqueness
            across categories (e.g., the category value).
    """
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

        with col1:
            header = f"### {profile.name}"
            if is_selected:
                header += " [SELECTED]"
            if is_best_in_class:
                header += " [BEST]"
            if not profile.is_available:
                header += " [UNAVAILABLE]"
            st.markdown(header)
            badges = [
                f"`{profile.ticker}`",
                profile.fund_family,
                profile.replication,
                profile.distribution,
            ]
            st.caption(" | ".join(badges))

        with col2:
            st.metric(
                "TER (Annual Cost)",
                f"{profile.ter:.2f}%" if profile.is_available else "N/A",
                help="Total Expense Ratio - lower is better (Bogleheads: costs matter)",
            )
            if profile.is_available:
                color = _ter_color(profile.ter)
                if color == "green":
                    st.caption("Low cost")
                elif color == "orange":
                    st.caption("Moderate cost")
                else:
                    st.caption("High cost")

        with col3:
            st.metric(
                "Fund Size (AUM)",
                _format_aum(profile.aum) if profile.is_available else "N/A",
                help="Assets Under Management - larger funds are more stable",
            )

        with col4:
            ret_3y = _format_return(profile.return_3y)
            st.metric(
                "3Y Return",
                ret_3y,
                help="3-year annualized return - past performance does not guarantee future results",
            )

        # Secondary row: 1Y and 5Y returns
        if profile.is_available:
            ret_cols = st.columns(3)
            with ret_cols[0]:
                st.metric("1Y Return", _format_return(profile.return_1y))
            with ret_cols[1]:
                st.metric("5Y Return", _format_return(profile.return_5y))
            with ret_cols[2]:
                price_str = f"{profile.current_price:,.2f} {profile.currency}"
                st.metric("Current Price", price_str)

        # Select button — key includes key_prefix to avoid duplicates
        if on_select and profile.is_available:
            button_label = "Selected" if is_selected else "Select for Portfolio"
            button_key = f"select_{key_prefix}_{profile.ticker}"
            if st.button(
                button_label,
                key=button_key,
                disabled=is_selected,
                help=f"Select {profile.ticker} for this portfolio slot",
            ):
                on_select(profile)
