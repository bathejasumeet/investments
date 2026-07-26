"""Repository for persisting saved four-fund portfolio plans."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.four_fund_plan import FourFundPlan


class FourFundPlanRepository:
    """CRUD access for FourFundPlan entities."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_all(self) -> list[FourFundPlan]:
        """Return all saved plans, newest first."""
        return (
            self._session.query(FourFundPlan)
            .order_by(FourFundPlan.updated_at.desc())
            .all()
        )

    def get_by_name(self, name: str) -> FourFundPlan | None:
        """Return a saved plan by exact name."""
        return (
            self._session.query(FourFundPlan)
            .filter(FourFundPlan.name == name)
            .first()
        )

    def save(
        self,
        *,
        name: str,
        eu_ticker: str,
        developed_ticker: str,
        emerging_ticker: str,
        bonds_ticker: str,
        eu_weight: float,
        developed_weight: float,
        emerging_weight: float,
        bonds_weight: float,
    ) -> FourFundPlan:
        """Create or update a saved plan by name."""
        existing = self.get_by_name(name)
        if existing is None:
            plan = FourFundPlan(
                name=name,
                eu_ticker=eu_ticker,
                developed_ticker=developed_ticker,
                emerging_ticker=emerging_ticker,
                bonds_ticker=bonds_ticker,
                eu_weight=eu_weight,
                developed_weight=developed_weight,
                emerging_weight=emerging_weight,
                bonds_weight=bonds_weight,
            )
            self._session.add(plan)
            self._session.commit()
            self._session.refresh(plan)
            return plan

        existing.eu_ticker = eu_ticker
        existing.developed_ticker = developed_ticker
        existing.emerging_ticker = emerging_ticker
        existing.bonds_ticker = bonds_ticker
        existing.eu_weight = eu_weight
        existing.developed_weight = developed_weight
        existing.emerging_weight = emerging_weight
        existing.bonds_weight = bonds_weight
        existing.updated_at = datetime.utcnow()
        self._session.commit()
        self._session.refresh(existing)
        return existing

    def delete(self, plan_id: int) -> bool:
        """Delete a saved plan by ID."""
        plan = self._session.get(FourFundPlan, plan_id)
        if plan is None:
            return False
        self._session.delete(plan)
        self._session.commit()
        return True
