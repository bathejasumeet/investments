"""Unit tests for the YFinanceProvider implementation.

Covers the parallel bulk price fetch (with progress reporting) and the
in-memory FX rate cache that prevents redundant HTTP lookups.
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pandas as pd
import pytest

from app.models.investment_option import ExchangeRate
from app.providers.base import PriceQuote
from app.providers import yfinance_provider
from app.providers.yfinance_provider import YFinanceProvider


def _quote(ticker: str, price: float = 100.0, currency: str = "EUR") -> PriceQuote:
    return PriceQuote(ticker=ticker, price=price, currency=currency, timestamp=datetime.utcnow())


@pytest.mark.unit
class TestGetCurrentPricesParallel:
    """Tests for concurrent bulk price fetching."""

    def test_returns_quotes_for_resolved_tickers(self) -> None:
        """For successful tickers a PriceQuote is included; failures omitted."""
        provider = YFinanceProvider()
        quotes = {
            "SAP.DE": _quote("SAP.DE", 180.0, "EUR"),
            "ASML.AS": _quote("ASML.AS", 650.0, "EUR"),
        }
        provider.get_current_price = lambda ticker: quotes.get(ticker)  # type: ignore[method-assign]

        result = provider.get_current_prices(["SAP.DE", "ASML.AS", "INVALID.X"])

        assert set(result.keys()) == {"SAP.DE", "ASML.AS"}
        assert result["SAP.DE"].price == 180.0

    def test_empty_ticker_list_returns_empty_dict(self) -> None:
        """An empty request must not start a thread pool."""
        provider = YFinanceProvider()
        assert provider.get_current_prices([]) == {}

    def test_progress_callback_reports_monotonic_completion(self) -> None:
        """Callback receives (completed, total) with completed going 1..N."""
        provider = YFinanceProvider()
        provider.get_current_price = lambda ticker: _quote(ticker)  # type: ignore[method-assign]

        events: list[tuple[int, int]] = []
        provider.get_current_prices(
            ["A", "B", "C"],
            progress_callback=lambda done, total: events.append((done, total)),
        )

        # Completion order from the pool is arbitrary, but the running counter
        # is incremented serially in the main thread, so counts are monotonic.
        assert [done for done, _ in events] == [1, 2, 3]
        assert all(total == 3 for _, total in events)

    def test_progress_callback_optional(self) -> None:
        """Omitting the callback must not raise."""
        provider = YFinanceProvider()
        provider.get_current_price = lambda ticker: _quote(ticker)  # type: ignore[method-assign]

        result = provider.get_current_prices(["A", "B"])  # no callback

        assert len(result) == 2

    def test_individual_ticker_failure_does_not_abort_batch(self) -> None:
        """A raising get_current_price must be swallowed, others still returned."""
        provider = YFinanceProvider()

        def flaky(ticker: str) -> PriceQuote | None:
            if ticker == "BOOM":
                raise RuntimeError("network error")
            return _quote(ticker)

        provider.get_current_price = flaky  # type: ignore[method-assign]

        result = provider.get_current_prices(["OK1", "BOOM", "OK2"])

        assert "BOOM" not in result
        assert {"OK1", "OK2"} <= set(result.keys())


@pytest.mark.unit
class TestExchangeRateCache:
    """Tests for the per-instance FX rate cache."""

    def test_same_currency_returns_identity_rate(self) -> None:
        provider = YFinanceProvider()
        rate = provider.get_exchange_rate("EUR", "eur")

        assert rate is not None
        assert rate.rate == 1.0
        assert rate.source_currency == "EUR"
        assert rate.target_currency == "EUR"

    def test_cache_prevents_repeated_network_lookups(self, monkeypatch) -> None:
        provider = YFinanceProvider()
        calls = 0

        def fake_fetch(src: str, target: str) -> ExchangeRate | None:
            nonlocal calls
            calls += 1
            return ExchangeRate(src, target, 0.85, datetime.utcnow())

        monkeypatch.setattr(provider, "_fetch_exchange_rate", fake_fetch)

        first = provider.get_exchange_rate("GBP", "EUR")
        second = provider.get_exchange_rate("GBP", "EUR")

        assert calls == 1
        assert first is not None and second is not None
        assert second.rate == first.rate

    def test_clear_fx_cache_forces_refetch(self, monkeypatch) -> None:
        provider = YFinanceProvider()
        calls = 0

        def fake_fetch(src: str, target: str) -> ExchangeRate | None:
            nonlocal calls
            calls += 1
            return ExchangeRate(src, target, 0.85, datetime.utcnow())

        monkeypatch.setattr(provider, "_fetch_exchange_rate", fake_fetch)

        provider.get_exchange_rate("GBP", "EUR")
        provider.clear_fx_cache()
        provider.get_exchange_rate("GBP", "EUR")

        assert calls == 2

    def test_negative_lookup_is_cached(self, monkeypatch) -> None:
        """A None result must also be cached to avoid retry storms."""
        provider = YFinanceProvider()
        calls = 0

        def fake_fetch(src: str, target: str) -> ExchangeRate | None:
            nonlocal calls
            calls += 1
            return None

        monkeypatch.setattr(provider, "_fetch_exchange_rate", fake_fetch)

        first = provider.get_exchange_rate("SEK", "EUR")
        second = provider.get_exchange_rate("SEK", "EUR")

        assert first is None and second is None
        assert calls == 1

    def test_different_pairs_fetched_separately(self, monkeypatch) -> None:
        provider = YFinanceProvider()
        calls: list[tuple[str, str]] = []
        monkeypatch.setattr(
            provider,
            "_fetch_exchange_rate",
            lambda s, t: (calls.append((s, t)), ExchangeRate(s, t, 0.9, datetime.utcnow()))[1],
        )

        provider.get_exchange_rate("GBP", "EUR")
        provider.get_exchange_rate("CHF", "EUR")

        assert calls == [("GBP", "EUR"), ("CHF", "EUR")]


@pytest.mark.unit
class TestGetFundInfoAumFallback:
    """Tests for AUM extraction in get_fund_info."""

    def test_uses_total_net_assets_when_total_assets_missing(self, monkeypatch) -> None:
        """Should estimate AUM from fund operations when totalAssets is None."""
        provider = YFinanceProvider()

        fund_ops = pd.DataFrame(
            {"EUNL.DE": [10_000.0]},
            index=["Total Net Assets"],
        )

        class StubFundsData:
            def __init__(self, operations) -> None:
                self.fund_operations = operations

        class StubTicker:
            def __init__(self, symbol: str) -> None:
                self.symbol = symbol
                self.info = {
                    "regularMarketPrice": 100.0,
                    "currency": "EUR",
                    "totalAssets": None,
                    "navPrice": 100.0,
                }
                self.funds_data = StubFundsData(fund_ops)

        monkeypatch.setattr(yfinance_provider.yf, "Ticker", StubTicker)

        profile = provider.get_fund_info("EUNL.DE")

        assert profile is not None
        assert profile.aum == 1_000_000_000.0

    def test_prefers_total_assets_when_present(self, monkeypatch) -> None:
        """Should use totalAssets directly when Yahoo provides it."""
        provider = YFinanceProvider()

        class StubFundsData:
            def __init__(self) -> None:
                self.fund_operations = pd.DataFrame()

        class StubTicker:
            def __init__(self, symbol: str) -> None:
                self.symbol = symbol
                self.info = {
                    "regularMarketPrice": 100.0,
                    "currency": "EUR",
                    "totalAssets": 7_402_345_984.0,
                    "navPrice": 100.0,
                }
                self.funds_data = StubFundsData()

        monkeypatch.setattr(yfinance_provider.yf, "Ticker", StubTicker)

        profile = provider.get_fund_info("EUNL.DE")

        assert profile is not None
        assert profile.aum == 7_402_345_984.0

    def test_converts_gbp_fields_to_eur_base_currency(self, monkeypatch) -> None:
        """Should convert current_price and AUM to configured base currency."""
        provider = YFinanceProvider()

        class StubFundsData:
            def __init__(self) -> None:
                self.fund_operations = pd.DataFrame()

        class StubTicker:
            def __init__(self, symbol: str) -> None:
                self.symbol = symbol
                self.info = {
                    "regularMarketPrice": 10.0,
                    "currency": "GBP",
                    "totalAssets": 1_000.0,
                    "navPrice": 10.0,
                }
                self.funds_data = StubFundsData()

        monkeypatch.setattr(yfinance_provider.yf, "Ticker", StubTicker)
        monkeypatch.setattr(yfinance_provider, "config", SimpleNamespace(base_currency="EUR"))
        monkeypatch.setattr(
            provider,
            "get_exchange_rate",
            lambda src, target: ExchangeRate(src, target, 1.2, datetime.utcnow()),
        )

        profile = provider.get_fund_info("EUNL.DE")

        assert profile is not None
        assert profile.currency == "EUR"
        assert profile.current_price == 12.0
        assert profile.aum == 1_200.0
