"""Unit tests for ChartService — TDD tests written FIRST."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.services.chart_service import ChartService


@pytest.mark.unit
class TestChartDataPreparation:
    """Tests for chart data preparation."""

    def test_price_history_converted_to_plotly_format(self, mock_provider):
        """Price history MUST be converted to Plotly-compatible format."""
        service = ChartService(provider=mock_provider)
        chart_data = service.prepare_chart_data("AAPL", "1M")
        assert chart_data is not None
        assert "dates" in chart_data
        assert "closes" in chart_data
        assert "opens" in chart_data
        assert "highs" in chart_data
        assert "lows" in chart_data
        assert "volumes" in chart_data
        assert len(chart_data["dates"]) > 0

    def test_empty_history_returns_none(self, mock_provider):
        """Empty price history MUST return None."""
        mock_provider.get_price_history.return_value = None
        service = ChartService(provider=mock_provider)
        chart_data = service.prepare_chart_data("INVALID", "1M")
        assert chart_data is None


@pytest.mark.unit
class TestTimeRangeFiltering:
    """Tests for time range filtering."""

    @pytest.mark.parametrize("period", ["1D", "1W", "1M", "3M", "1Y"])
    def test_all_time_ranges_return_data(self, mock_provider, period):
        """All supported time ranges MUST return data when available."""
        service = ChartService(provider=mock_provider)
        chart_data = service.prepare_chart_data("AAPL", period)
        assert chart_data is not None

    def test_invalid_period_defaults_to_1m(self, mock_provider):
        """Invalid period MUST default to 1M."""
        service = ChartService(provider=mock_provider)
        chart_data = service.prepare_chart_data("AAPL", "INVALID")
        assert chart_data is not None
        mock_provider.get_price_history.assert_called_with("AAPL", "1M")


@pytest.mark.unit
class TestInsufficientDataHandling:
    """Tests for insufficient data handling."""

    def test_partial_data_renders_without_extrapolation(self, mock_provider):
        """Partial data MUST render without extrapolation."""
        from app.providers.base import PriceHistory

        mock_provider.get_price_history.return_value = PriceHistory(
            ticker="AAPL",
            dates=[datetime(2024, 6, 1)],
            opens=[170.0],
            highs=[175.0],
            lows=[168.0],
            closes=[172.0],
            volumes=[50000000],
        )
        service = ChartService(provider=mock_provider)
        chart_data = service.prepare_chart_data("AAPL", "1M")
        assert chart_data is not None
        assert len(chart_data["dates"]) == 1