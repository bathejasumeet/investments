"""Investment option card component — displays a single European investment option.

Renders option name, ticker, exchange badge, current price, currency,
asset class pill, performance deltas (1Y/3Y/5Y), and benefit score.
"""

from __future__ import annotations

import math
from typing import Optional

import streamlit as st

from app.data.eu_ticker_universes import AssetClass
from app.models.investment_option import (
    BenefitScore,
    InvestmentOption,
    PerformanceDelta,
)
from app.utils.currency import format_money

# Asset class display configuration
_ASSET_CLASS_CONFIG: dict[AssetClass, dict[str, str]] = {
    AssetClass.STOCK: {"label": "Stock", "icon": "📊", "color": "blue"},
    AssetClass.ETF: {"label": "ETF", "icon": "📈", "color": "green"},
    AssetClass.BOND_ETF: {"label": "Bond ETF", "icon": "🏦", "color": "orange"},
}


def _format_pct(value: float) -> str:
    """Format a percentage change, treating NaN as unavailable.

    yfinance history closes can occasionally contain NaN values, which
    propagate into PerformanceDelta.percentage_change and render as
    "+nan%". Normalize to "N/A" for display.

    Args:
        value: Percentage change value.

    Returns:
        Formatted string (e.g., "+8.20%", "N/A").
    """
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if not math.isfinite(numeric):
        return "N/A"
    return f"{numeric:+.2f}%"


def _format_money_delta(value: float, currency: str) -> str:
    """Format money delta with explicit leading sign for st.metric.

    Streamlit infers up/down arrow direction from a leading +/- token.
    """
    sign = "+" if value >= 0 else "-"
    return f"{sign}{format_money(abs(value), currency)}"


def render_investment_option_card(
    option: InvestmentOption,
    deltas: Optional[list[PerformanceDelta]] = None,
    benefit_score: Optional[BenefitScore] = None,
    on_add_to_portfolio: Optional[callable] = None,
) -> None:
    """Render a single investment option as a card.

    Args:
        option: The InvestmentOption to display.
        deltas: Optional list of PerformanceDelta for 1Y/3Y/5Y.
        benefit_score: Optional BenefitScore with breakdown.
        on_add_to_portfolio: Optional callback for add-to-portfolio action.
    """
    config = _ASSET_CLASS_CONFIG.get(option.asset_class, {})
    icon = config.get("icon", "❓")
    class_label = config.get("label", "Unknown")

    with st.container(border=True):
        col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

        with col1:
            header = f"### {icon} {option.name}"
            if option.in_portfolio:
                header += " ✅"
            if option.is_delisted:
                header += " ⚠️ Delisted"
            st.markdown(header)
            st.caption(f"`{option.ticker}` | {option.exchange} | {class_label} | {option.sector}")

        with col2:
            price_str = f"{option.current_price:,.2f} {option.currency}"
            st.metric("Current Price", price_str)

        with col3:
            if deltas:
                delta_1y = next((d for d in deltas if d.period == "1Y"), None)
                if delta_1y:
                    st.metric(
                        "1Y Change",
                        _format_pct(delta_1y.percentage_change),
                        delta=_format_money_delta(
                            delta_1y.absolute_change,
                            option.currency,
                        ),
                    )
                else:
                    st.metric("1Y Change", "N/A")

        with col4:
            if benefit_score:
                st.metric(
                    "Benefit Score",
                    f"{benefit_score.composite_score:.0%}",
                    help=benefit_score.component_breakdown,
                )
            elif option.benefit_score > 0:
                st.metric("Benefit Score", f"{option.benefit_score:.0%}")

        # Display 3Y and 5Y deltas if available
        if deltas:
            delta_cols = st.columns(3)
            delta_3y = next((d for d in deltas if d.period == "3Y"), None)
            delta_5y = next((d for d in deltas if d.period == "5Y"), None)

            with delta_cols[0]:
                if delta_3y:
                    label = "3Y Change" if delta_3y.available else "3Y Change (partial)"
                    st.metric(
                        label,
                        _format_pct(delta_3y.percentage_change),
                    )

            with delta_cols[1]:
                if delta_5y:
                    label = "5Y Change" if delta_5y.available else "5Y Change (partial)"
                    st.metric(
                        label,
                        _format_pct(delta_5y.percentage_change),
                    )

            with delta_cols[2]:
                if not delta_5y or not delta_5y.available:
                    st.caption("ℹ️ Limited historical data available")

        # Add to portfolio button
        if on_add_to_portfolio and not option.in_portfolio and not option.is_delisted:
            if st.button(
                "Add to Portfolio",
                key=f"add_{option.ticker}",
                help=f"Add {option.ticker} to your portfolio",
            ):
                on_add_to_portfolio(option)