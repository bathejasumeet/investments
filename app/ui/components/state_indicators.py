"""Reusable UI state indicator components for Streamlit.

Provides loading, empty, error, and success state components
to ensure consistent UX across all views (Constitution Principle III).
"""

from __future__ import annotations

import streamlit as st


def loading_spinner(message: str = "Loading...") -> None:
    """Display a loading spinner with a message.

    Args:
        message: Message to display alongside the spinner.
    """
    with st.spinner(message):
        st.info(message)


def empty_state(
    title: str = "Nothing here yet",
    message: str = "",
    action_label: str = "",
) -> None:
    """Display an empty state with guidance.

    Args:
        title: Headline for the empty state.
        message: Descriptive message explaining what to do.
        action_label: Optional label for a call-to-action button.
    """
    st.markdown(f"### 📭 {title}")
    if message:
        st.markdown(message)
    if action_label:
        st.button(action_label, key=f"empty_action_{title}")


def error_message(
    title: str = "Something went wrong",
    message: str = "",
    recovery_hint: str = "",
) -> None:
    """Display an error message with a recovery path.

    Args:
        title: Error headline.
        message: Detailed error description.
        recovery_hint: Suggested action to recover from the error.
    """
    st.error(f"**{title}**")
    if message:
        st.markdown(message)
    if recovery_hint:
        st.info(f"💡 {recovery_hint}")


def success_toast(message: str) -> None:
    """Display a success notification.

    Args:
        message: Success message to display.
    """
    st.success(message)


def stale_data_warning(last_updated: str) -> None:
    """Display a warning about stale market data.

    Args:
        last_updated: Human-readable timestamp of last data update.
    """
    st.warning(
        f"⚠️ **Market data may be stale.** "
        f"Last updated: {last_updated}. "
        f"Some information may not reflect current market conditions."
    )


def data_freshness_indicator(is_stale: bool, last_updated: str) -> None:
    """Display a data freshness indicator.

    Args:
        is_stale: Whether the data is considered stale (> 1 hour old).
        last_updated: Human-readable timestamp of last update.
    """
    if is_stale:
        stale_data_warning(last_updated)
    else:
        st.caption(f"✅ Data up to date — Last refresh: {last_updated}")