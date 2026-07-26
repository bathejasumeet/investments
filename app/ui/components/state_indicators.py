"""Reusable UI state indicator components for Streamlit.

Provides loading, empty, error, and success state components
to ensure consistent UX across all views (Constitution Principle III).
"""

from __future__ import annotations

import streamlit as st


def loading_spinner(message: str = "Loading...") -> None:
    """Display a loading spinner with a message."""
    with st.spinner(message):
        st.info(message)


def empty_state(
    title: str = "Nothing here yet",
    message: str = "",
    action_label: str = "",
) -> None:
    """Display an empty state with guidance."""
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
    """Display an error message with a recovery path."""
    st.error(f"**{title}**")
    if message:
        st.markdown(message)
    if recovery_hint:
        st.info(f"💡 {recovery_hint}")


def success_toast(message: str) -> None:
    """Display a success notification."""
    st.success(message)


def stale_data_warning(last_updated: str) -> None:
    """Display a warning about stale market data."""
    st.warning(
        f"⚠️ **Market data may be stale.** "
        f"Last updated: {last_updated}. "
        f"Some information may not reflect current market conditions."
    )


def data_freshness_indicator(is_stale: bool, last_updated: str) -> None:
    """Display a data freshness indicator."""
    if is_stale:
        stale_data_warning(last_updated)
    else:
        st.caption(f"✅ Data up to date — Last refresh: {last_updated}")


def render_info_popover(label: str, body: str, *, icon: str = "ℹ️") -> None:
    """Display a plain-language explanation in a popover (or expander fallback).

    Args:
        label: Short button/section label (without icon).
        body: Markdown content to display when expanded.
        icon: Icon prefix shown before the label.
    """
    title = f"{icon} {label}"
    if hasattr(st, "popover"):
        with st.popover(title):
            st.markdown(body)
    else:
        with st.expander(title):
            st.markdown(body)
