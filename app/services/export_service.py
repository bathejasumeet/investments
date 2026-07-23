"""CSV export service — export portfolio data to CSV.

Exports holdings and performance history in CSV format.
"""

from __future__ import annotations

import csv
import io
from typing import Any

from app.models.holding import Holding
from app.services.portfolio_service import HoldingSummary


class ExportService:
    """Service for exporting portfolio data to CSV."""

    def export_holdings(
        self, holdings: list[Holding], summaries: list[HoldingSummary]
    ) -> str:
        """Export holdings with current values to CSV string.

        Args:
            holdings: List of Holding instances.
            summaries: List of HoldingSummary with calculated values.

        Returns:
            CSV string with holdings data.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Ticker",
                "Quantity",
                "Purchase Price",
                "Current Price",
                "Current Value",
                "Gain/Loss (EUR)",
                "Gain/Loss (%)",
                "Date Acquired",
            ]
        )

        summary_map = {s.ticker: s for s in summaries}
        for holding in holdings:
            s = summary_map.get(holding.ticker)
            if s:
                writer.writerow(
                    [
                        s.ticker,
                        f"{s.quantity:.2f}",
                        f"{s.purchase_price:.2f}",
                        f"{s.current_price:.2f}",
                        f"{s.current_value:.2f}",
                        f"{s.absolute_gain:.2f}",
                        f"{s.percentage_gain:.2f}",
                        holding.date_acquired.strftime("%Y-%m-%d"),
                    ]
                )
            else:
                writer.writerow(
                    [
                        holding.ticker,
                        f"{holding.quantity:.2f}",
                        f"{holding.purchase_price:.2f}",
                        "N/A",
                        "N/A",
                        "N/A",
                        "N/A",
                        holding.date_acquired.strftime("%Y-%m-%d"),
                    ]
                )

        return output.getvalue()

    def export_to_file(
        self, holdings: list[Holding], summaries: list[HoldingSummary], filepath: str
    ) -> bool:
        """Export holdings to a CSV file.

        Args:
            holdings: List of Holding instances.
            summaries: List of HoldingSummary with calculated values.
            filepath: Path to write the CSV file.

        Returns:
            True if successful, False otherwise.
        """
        try:
            csv_content = self.export_holdings(holdings, summaries)
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                f.write(csv_content)
            return True
        except Exception:
            return False