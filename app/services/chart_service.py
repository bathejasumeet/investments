"""Chart service — prepares price history data for Plotly charts.

Fetches price history, filters by time range, and formats
data for Plotly candlestick/line chart rendering.
"""

from __future__ import annotations

from typing import Any, Optional

from app.providers.base import MarketDataProvider, PriceHistory

# Valid time periods
_VALID_PERIODS = {"1D", "1W", "1M", "3M", "1Y"}


class ChartService:
    """Service for preparing chart data from market data."""

    def __init__(self, provider: MarketDataProvider) -> None:
        self._provider = provider

    def prepare_chart_data(
        self, ticker: str, period: str = "1M"
    ) -> Optional[dict[str, Any]]:
        """Prepare price history data for Plotly chart rendering.

        Args:
            ticker: Stock ticker symbol.
            period: Time range — one of 1D, 1W, 1M, 3M, 1Y.

        Returns:
            Dictionary with dates, opens, highs, lows, closes, volumes
            ready for Plotly, or None if no data available.
        """
        # Validate period, default to 1M
        if period not in _VALID_PERIODS:
            period = "1M"

        history = self._provider.get_price_history(ticker, period)
        if history is None or not history.dates:
            return None

        return {
            "ticker": history.ticker,
            "dates": [d.strftime("%Y-%m-%d") for d in history.dates],
            "opens": history.opens,
            "highs": history.highs,
            "lows": history.lows,
            "closes": history.closes,
            "volumes": history.volumes,
        }

    def create_candlestick_chart(
        self, chart_data: dict[str, Any]
    ) -> Any:
        """Create a Plotly candlestick chart from prepared data.

        Args:
            chart_data: Dictionary from prepare_chart_data.

        Returns:
            Plotly Figure object.
        """
        import plotly.graph_objects as go

        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=chart_data["dates"],
                    open=chart_data["opens"],
                    high=chart_data["highs"],
                    low=chart_data["lows"],
                    close=chart_data["closes"],
                    name=chart_data["ticker"],
                )
            ]
        )
        fig.update_layout(
            title=f"{chart_data['ticker']} Price History",
            yaxis_title="Price ($)",
            xaxis_title="Date",
            template="plotly_dark",
            height=500,
        )
        return fig

    def create_line_chart(
        self, chart_data: dict[str, Any]
    ) -> Any:
        """Create a Plotly line chart from prepared data.

        Args:
            chart_data: Dictionary from prepare_chart_data.

        Returns:
            Plotly Figure object.
        """
        import plotly.graph_objects as go

        fig = go.Figure(
            data=[
                go.Scatter(
                    x=chart_data["dates"],
                    y=chart_data["closes"],
                    mode="lines",
                    name=chart_data["ticker"],
                    line=dict(color="#00d4aa", width=2),
                )
            ]
        )
        fig.update_layout(
            title=f"{chart_data['ticker']} Price History",
            yaxis_title="Price ($)",
            xaxis_title="Date",
            template="plotly_dark",
            height=500,
            hovermode="x unified",
        )
        return fig