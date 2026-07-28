"""Unit tests for recommendations UI loading / session cache."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.recommendation_service import Recommendation
from app.ui import recommendations as recommendations_ui


class _FakeSessionState(dict):
    """Minimal stand-in for st.session_state supporting dict + attr access."""

    def __getattr__(self, name: str):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value) -> None:
        self[name] = value

    def pop(self, key, default=None):
        return super().pop(key, default)


@pytest.fixture
def fake_streamlit(monkeypatch):
    """Patch streamlit symbols used by the recommendations view helpers."""
    state = _FakeSessionState()
    spinner_calls: list[str] = []

    class _Spinner:
        def __init__(self, label: str) -> None:
            spinner_calls.append(label)

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

    fake_st = SimpleNamespace(
        session_state=state,
        spinner=lambda label: _Spinner(label),
    )
    monkeypatch.setattr(recommendations_ui, "st", fake_st)
    return fake_st, spinner_calls


def _sample_rec(ticker: str = "NVDA") -> Recommendation:
    return Recommendation(
        ticker=ticker,
        current_price=100.0,
        trend_direction="up",
        sector="Technology",
        confidence_score=0.8,
        change_percent=5.0,
        currency="EUR",
    )


@pytest.mark.unit
class TestRecommendationCache:
    """Session cache must prevent re-fetch on Streamlit reruns."""

    def test_first_load_fetches_and_caches(self, fake_streamlit) -> None:
        st, spinner_calls = fake_streamlit
        service = MagicMock()
        service.get_recommendations.return_value = [_sample_rec()]
        service.get_last_fetch_time.return_value = datetime(2024, 1, 1, 12, 0, 0)

        recs, last_fetch, error = recommendations_ui._load_recommendations(
            service,
            portfolio_tickers=["AAPL"],
            force_refresh=False,
        )

        assert len(recs) == 1
        assert recs[0].ticker == "NVDA"
        assert last_fetch == datetime(2024, 1, 1, 12, 0, 0)
        assert error is False
        assert service.get_recommendations.call_count == 1
        assert len(spinner_calls) == 1
        assert st.session_state[recommendations_ui._CACHE_RECS_KEY][0].ticker == "NVDA"

    def test_second_load_uses_cache_without_network(self, fake_streamlit) -> None:
        st, spinner_calls = fake_streamlit
        service = MagicMock()
        service.get_recommendations.return_value = [_sample_rec("ONE")]
        service.get_last_fetch_time.return_value = datetime(2024, 1, 1, 12, 0, 0)

        recommendations_ui._load_recommendations(
            service, portfolio_tickers=[], force_refresh=False
        )
        service.get_recommendations.return_value = [_sample_rec("TWO")]

        recs, _, _ = recommendations_ui._load_recommendations(
            service, portfolio_tickers=[], force_refresh=False
        )

        assert service.get_recommendations.call_count == 1
        assert recs[0].ticker == "ONE"
        assert len(spinner_calls) == 1

    def test_force_refresh_bypasses_cache(self, fake_streamlit) -> None:
        _, spinner_calls = fake_streamlit
        service = MagicMock()
        service.get_recommendations.return_value = [_sample_rec("OLD")]
        service.get_last_fetch_time.return_value = datetime(2024, 1, 1, 12, 0, 0)

        recommendations_ui._load_recommendations(
            service, portfolio_tickers=[], force_refresh=False
        )
        service.get_recommendations.return_value = [_sample_rec("NEW")]
        service.get_last_fetch_time.return_value = datetime(2024, 1, 1, 13, 0, 0)

        recs, last_fetch, _ = recommendations_ui._load_recommendations(
            service, portfolio_tickers=[], force_refresh=True
        )

        assert service.get_recommendations.call_count == 2
        assert recs[0].ticker == "NEW"
        assert last_fetch == datetime(2024, 1, 1, 13, 0, 0)
        assert len(spinner_calls) == 2

    def test_clear_cache_removes_keys(self, fake_streamlit) -> None:
        st, _ = fake_streamlit
        st.session_state[recommendations_ui._CACHE_RECS_KEY] = [_sample_rec()]
        st.session_state[recommendations_ui._CACHE_FETCH_KEY] = datetime.utcnow()
        st.session_state[recommendations_ui._CACHE_ERROR_KEY] = False

        recommendations_ui._clear_recommendation_cache()

        assert recommendations_ui._CACHE_RECS_KEY not in st.session_state
        assert recommendations_ui._CACHE_FETCH_KEY not in st.session_state
        assert recommendations_ui._CACHE_ERROR_KEY not in st.session_state

    def test_provider_exception_sets_error_flag(self, fake_streamlit) -> None:
        service = MagicMock()
        service.get_recommendations.side_effect = RuntimeError("network down")
        service.get_last_fetch_time.return_value = None

        recs, _, error = recommendations_ui._load_recommendations(
            service, portfolio_tickers=[], force_refresh=True
        )

        assert recs == []
        assert error is True
