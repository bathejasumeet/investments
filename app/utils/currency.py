"""Currency conversion and formatting utilities."""

from __future__ import annotations

import math
from typing import Protocol


class ExchangeRateProvider(Protocol):
    """Protocol for providers that can return FX rates."""

    def get_exchange_rate(self, source_currency: str, target_currency: str) -> object | None:
        """Return exchange-rate-like object with a numeric `rate` attribute."""


def normalize_currency(code: str | None) -> str:
    """Normalize currency code to uppercase, defaulting to EUR."""
    if not code:
        return "EUR"
    return code.upper()


def format_money(value: float, currency: str = "EUR") -> str:
    """Format numeric money values with a currency symbol/code."""
    code = normalize_currency(currency)
    symbols = {
        "EUR": "€",
        "USD": "$",
        "GBP": "£",
        "CHF": "CHF ",
        "SEK": "SEK ",
    }
    prefix = symbols.get(code, f"{code} ")
    return f"{prefix}{value:,.2f}"


def convert_amount(
    amount: float,
    source_currency: str,
    target_currency: str,
    provider: ExchangeRateProvider,
) -> float:
    """Convert an amount to target currency using provider FX rates.

    Returns the original amount when conversion data is unavailable.
    """
    src = normalize_currency(source_currency)
    target = normalize_currency(target_currency)

    if src == target:
        return amount

    try:
        fx = provider.get_exchange_rate(src, target)
    except Exception:
        return amount

    if fx is None:
        return amount

    rate = getattr(fx, "rate", None)
    try:
        numeric_rate = float(rate)
    except (TypeError, ValueError):
        return amount

    if not math.isfinite(numeric_rate) or numeric_rate <= 0:
        return amount

    return amount * numeric_rate
