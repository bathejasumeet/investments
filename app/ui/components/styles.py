"""Minimal, safe UI styles and helpers for Streamlit.

Only adds styling that Streamlit's theme doesn't already provide well
(card backgrounds, borders, spacing). Does NOT override text colors so
Streamlit's theme handles all contrast — keeping text readable.
"""

from __future__ import annotations

import contextlib
from collections.abc import Generator

import streamlit as st

# Color tokens for custom HTML components only (badges, progress bars)
SUCCESS = "#047857"
DANGER = "#b91c1c"
WARNING = "#b45309"
INFO = "#0369a1"
PRIMARY = "#1d4ed8"
BORDER = "#cbd5e1"

_GLOBAL_CSS = f"""
<style>
  /* Metrics as white cards with borders */
  [data-testid="stMetric"] {{
    background-color: #ffffff;
    border: 1px solid {BORDER};
    border-radius: 0.75rem;
    padding: 0.85rem 1rem;
  }}

  /* Bordered containers — clean cards */
  [data-testid="stVerticalBlockBorderWrapper"] {{
    border-radius: 0.75rem;
  }}

  /* Chart containers with border */
  .stPlotlyChart {{
    border-radius: 0.75rem;
    overflow: hidden;
  }}

  /* Dataframe borders */
  .stDataFrame {{
    border-radius: 0.75rem;
    overflow: hidden;
  }}

  /* ---- Custom HTML components (scoped classes only) ---- */
  .ux-badge {{
    display: inline-block;
    padding: 0.18rem 0.5rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 800;
    line-height: 1.4;
  }}
  .ux-badge-success {{ background-color: #d1fae5; color: #065f46; }}
  .ux-badge-danger  {{ background-color: #fee2e2; color: #991b1b; }}
  .ux-badge-warning {{ background-color: #fef3c7; color: #92400e; }}
  .ux-badge-info    {{ background-color: #e0f2fe; color: #075985; }}
  .ux-badge-neutral {{ background-color: #e2e8f0; color: #1e293b; }}

  .ux-progress-track {{
    width: 100%;
    height: 0.65rem;
    background-color: #e2e8f0;
    border-radius: 999px;
    overflow: hidden;
  }}
  .ux-progress-fill {{
    height: 100%;
    border-radius: 999px;
  }}

  .ux-section-header {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 1.35rem 0 0.65rem 0;
    padding-bottom: 0.45rem;
    border-bottom: 2px solid {BORDER};
  }}
  .ux-section-header-icon {{ font-size: 1.2rem; }}
  .ux-section-header-text {{
    font-size: 1.15rem;
    font-weight: 800;
  }}
</style>
"""


def inject_custom_styles() -> None:
    """Inject global custom CSS into the Streamlit app."""
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


def badge(label: str, tone: str = "neutral") -> str:
    """Return an HTML badge string."""
    safe = label.replace("<", "&lt;").replace(">", "&gt;")
    return f'<span class="ux-badge ux-badge-{tone}">{safe}</span>'


def progress_bar_html(value: float, color: str = PRIMARY) -> str:
    """Return a custom rounded progress bar as HTML."""
    pct = max(0.0, min(1.0, value)) * 100
    return (
        f'<div class="ux-progress-track">'
        f'<div class="ux-progress-fill" style="width:{pct:.1f}%;background-color:{color};"></div>'
        f"</div>"
    )


def section_header(title: str, icon: str = "") -> None:
    """Render a styled section header with optional emoji icon."""
    icon_html = f'<span class="ux-section-header-icon">{icon}</span>' if icon else ""
    html = (
        f'<div class="ux-section-header">'
        f"{icon_html}"
        f'<span class="ux-section-header-text">{title}</span>'
        f"</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


@contextlib.contextmanager
def card_container(*, key: str | None = None) -> Generator[None, None, None]:
    """Context manager that wraps content in a bordered Streamlit container."""
    with st.container(border=True):
        yield


def styled_divider() -> None:
    """Render a subtle horizontal divider."""
    st.markdown("---")
