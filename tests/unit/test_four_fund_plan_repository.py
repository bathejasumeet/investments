"""Unit tests for FourFundPlanRepository."""

from __future__ import annotations

import pytest

from app.repositories.four_fund_plan_repository import FourFundPlanRepository


@pytest.mark.unit
class TestFourFundPlanRepository:
    """CRUD behavior for saved four-fund plans."""

    def test_save_creates_new_plan(self, db_session) -> None:
        repo = FourFundPlanRepository(db_session)

        plan = repo.save(
            name="My Plan",
            eu_ticker="EUNL.DE",
            developed_ticker="IWDA.AS",
            emerging_ticker="EMIM.L",
            bonds_ticker="AGGH.L",
            eu_weight=30.0,
            developed_weight=30.0,
            emerging_weight=10.0,
            bonds_weight=30.0,
        )

        assert plan.id is not None
        assert plan.name == "My Plan"
        assert plan.eu_ticker == "EUNL.DE"

    def test_save_updates_existing_plan_by_name(self, db_session) -> None:
        repo = FourFundPlanRepository(db_session)

        first = repo.save(
            name="My Plan",
            eu_ticker="EUNL.DE",
            developed_ticker="IWDA.AS",
            emerging_ticker="EMIM.L",
            bonds_ticker="AGGH.L",
            eu_weight=30.0,
            developed_weight=30.0,
            emerging_weight=10.0,
            bonds_weight=30.0,
        )
        updated = repo.save(
            name="My Plan",
            eu_ticker="VEUR.AS",
            developed_ticker="SWDA.L",
            emerging_ticker="VFEM.L",
            bonds_ticker="VAGF.DE",
            eu_weight=20.0,
            developed_weight=50.0,
            emerging_weight=10.0,
            bonds_weight=20.0,
        )

        assert updated.id == first.id
        assert updated.eu_ticker == "VEUR.AS"
        assert updated.developed_weight == 50.0
        assert len(repo.get_all()) == 1

    def test_get_by_name_returns_none_for_missing(self, db_session) -> None:
        repo = FourFundPlanRepository(db_session)

        assert repo.get_by_name("Does Not Exist") is None

    def test_delete_removes_plan(self, db_session) -> None:
        repo = FourFundPlanRepository(db_session)
        plan = repo.save(
            name="Delete Me",
            eu_ticker="EUNL.DE",
            developed_ticker="IWDA.AS",
            emerging_ticker="EMIM.L",
            bonds_ticker="AGGH.L",
            eu_weight=30.0,
            developed_weight=30.0,
            emerging_weight=10.0,
            bonds_weight=30.0,
        )

        assert repo.delete(plan.id) is True
        assert repo.get_by_name("Delete Me") is None
        assert repo.delete(plan.id) is False
