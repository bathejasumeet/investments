"""Unit tests for ExportService — TDD tests written FIRST."""

from __future__ import annotations

import csv
import io

import pytest

from app.services.export_service import ExportService
from app.services.portfolio_service import HoldingSummary


@pytest.mark.unit
class TestExportService:
    """Tests for CSV export functionality."""

    def test_csv_format_has_correct_headers(self):
        """CSV export MUST have correct column headers."""
        service = ExportService()
        csv_content = service.export_holdings([], [])
        reader = csv.reader(io.StringIO(csv_content))
        headers = next(reader)
        assert "Ticker" in headers
        assert "Quantity" in headers
        assert "Purchase Price" in headers
        assert "Current Price" in headers
        assert "Current Value" in headers
        assert "Gain/Loss (EUR)" in headers

    def test_complete_export_with_holdings(self, sample_holdings):
        """Complete export MUST include all holdings with data."""
        service = ExportService()
        summaries = [
            HoldingSummary(
                ticker="AAPL", quantity=10.0, purchase_price=150.0,
                current_price=175.0, current_value=1750.0,
                absolute_gain=250.0, percentage_gain=16.67,
            ),
            HoldingSummary(
                ticker="MSFT", quantity=5.0, purchase_price=300.0,
                current_price=380.0, current_value=1900.0,
                absolute_gain=400.0, percentage_gain=33.33,
            ),
            HoldingSummary(
                ticker="GOOGL", quantity=8.0, purchase_price=140.0,
                current_price=145.0, current_value=1160.0,
                absolute_gain=40.0, percentage_gain=3.57,
            ),
        ]
        csv_content = service.export_holdings(sample_holdings, summaries)
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)
        assert len(rows) == 4  # header + 3 holdings
        assert rows[1][0] == "AAPL"
        assert rows[2][0] == "MSFT"
        assert rows[3][0] == "GOOGL"

    def test_empty_portfolio_export(self):
        """Empty portfolio export MUST contain only headers."""
        service = ExportService()
        csv_content = service.export_holdings([], [])
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)
        assert len(rows) == 1  # only header row