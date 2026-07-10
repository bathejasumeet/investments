"""Holdings management view — add, edit, and remove portfolio holdings.

Provides forms for adding new holdings with ticker validation,
editing existing holdings, and deleting with confirmation.
"""

from __future__ import annotations

import streamlit as st

from app.database import get_session
from app.providers.yfinance_provider import YFinanceProvider
from app.repositories.holding_repository import HoldingRepository
from app.repositories.price_repository import PriceRepository
from app.services.market_data_service import MarketDataService
from app.ui.components.state_indicators import (
    empty_state,
    error_message,
    success_toast,
)


def render_holdings() -> None:
    """Render the holdings management view."""
    st.title("💼 Holdings Management")

    session = get_session()
    holding_repo = HoldingRepository(session)
    price_repo = PriceRepository(session)
    provider = YFinanceProvider()
    market_data_service = MarketDataService(provider, price_repo)

    # --- Add New Holding Form ---
    st.subheader("Add New Holding")
    with st.form("add_holding_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            new_ticker = st.text_input(
                "Ticker Symbol",
                placeholder="e.g., AAPL",
                key="new_ticker",
            )

        with col2:
            new_quantity = st.number_input(
                "Quantity (shares)",
                min_value=0.0,
                step=0.01,
                key="new_quantity",
            )

        with col3:
            new_price = st.number_input(
                "Purchase Price ($)",
                min_value=0.0,
                step=0.01,
                key="new_price",
            )

        submitted = st.form_submit_button("Add Holding")

        if submitted:
            if not new_ticker.strip():
                error_message(
                    title="Missing ticker",
                    message="Please enter a valid ticker symbol.",
                )
            elif new_quantity <= 0:
                error_message(
                    title="Invalid quantity",
                    message="Quantity must be greater than zero.",
                )
            elif new_price <= 0:
                error_message(
                    title="Invalid price",
                    message="Purchase price must be greater than zero.",
                )
            else:
                # Check for duplicate
                existing = holding_repo.get_by_ticker(new_ticker)
                if existing:
                    error_message(
                        title="Duplicate holding",
                        message=(
                            f"You already hold {existing.ticker}. "
                            "Edit the existing holding instead."
                        ),
                    )
                else:
                    # Validate ticker
                    with st.spinner("Validating ticker symbol..."):
                        is_valid = market_data_service.validate_ticker(
                            new_ticker.strip()
                        )
                    if not is_valid:
                        error_message(
                            title="Invalid ticker",
                            message=(
                                f"'{new_ticker}' is not a valid ticker "
                                "symbol on the exchange."
                            ),
                        )
                    else:
                        holding_repo.add(
                            ticker=new_ticker,
                            quantity=new_quantity,
                            purchase_price=new_price,
                        )
                        success_toast(
                            f"✅ Added {new_quantity:.2f} shares of "
                            f"{new_ticker.upper()} at ${new_price:.2f}"
                        )
                        st.rerun()

    st.markdown("---")

    # --- List Existing Holdings ---
    st.subheader("Your Holdings")
    holdings = holding_repo.get_all()

    if not holdings:
        empty_state(
            title="No holdings yet",
            message="Use the form above to add your first investment holding.",
        )
        session.close()
        return

    for holding in holdings:
        with st.container(border=True):
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])

            with col1:
                st.markdown(f"### {holding.ticker}")

            with col2:
                st.metric("Quantity", f"{holding.quantity:.2f}")

            with col3:
                st.metric("Purchase Price", f"${holding.purchase_price:.2f}")

            with col4:
                if st.button("Edit", key=f"edit_{holding.id}"):
                    st.session_state[f"editing_{holding.id}"] = True
                    st.rerun()

            with col5:
                if st.button("Delete", key=f"delete_{holding.id}"):
                    st.session_state[f"deleting_{holding.id}"] = True
                    st.rerun()

            # Edit form
            if st.session_state.get(f"editing_{holding.id}"):
                with st.form(f"edit_form_{holding.id}"):
                    edit_qty = st.number_input(
                        "Quantity",
                        value=float(holding.quantity),
                        min_value=0.0,
                        step=0.01,
                        key=f"edit_qty_{holding.id}",
                    )
                    edit_price = st.number_input(
                        "Purchase Price",
                        value=float(holding.purchase_price),
                        min_value=0.0,
                        step=0.01,
                        key=f"edit_price_{holding.id}",
                    )
                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.form_submit_button("Save"):
                            holding_repo.update(
                                holding.id,
                                quantity=edit_qty,
                                purchase_price=edit_price,
                            )
                            success_toast(f"✅ Updated {holding.ticker}")
                            st.session_state[f"editing_{holding.id}"] = False
                            st.rerun()
                    with col_cancel:
                        if st.form_submit_button("Cancel"):
                            st.session_state[f"editing_{holding.id}"] = False
                            st.rerun()

            # Delete confirmation
            if st.session_state.get(f"deleting_{holding.id}"):
                st.warning(f"Are you sure you want to delete {holding.ticker}?")
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("Yes, Delete", key=f"confirm_{holding.id}"):
                        holding_repo.delete(holding.id)
                        success_toast(f"🗑️ Deleted {holding.ticker}")
                        st.session_state[f"deleting_{holding.id}"] = False
                        st.rerun()
                with col_cancel:
                    if st.button("Cancel", key=f"cancel_del_{holding.id}"):
                        st.session_state[f"deleting_{holding.id}"] = False
                        st.rerun()

    session.close()