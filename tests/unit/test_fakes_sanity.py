"""Sanidad de las piezas PROVISTAS (fakes, fallas, seed en memoria). Estos tests deben pasar desde el día 1."""

import pytest

from app.activity.service import ActivityService
from app.admin.faults import FaultState, FaultyPurchaseRelations
from app.config import Settings
from app.container import build_container
from app.fakes import FakeActivityStore, FakeRelations
from app.shared.errors import RelationsUnavailableError


def test_activity_fake_counts_recent_and_top():
    service = ActivityService(FakeActivityStore(recent_limit=2))
    for product in ("a", "b", "a", "c"):
        service.register_view("u1", product)
    assert service.view_count("a") == 2
    assert service.recent("u1", 10) == ["c", "a"]  # acotado a 2, más reciente primero
    assert service.top(1)[0].product_id == "a"


def test_faulty_relations_raises_only_when_flag_is_on():
    faults = FaultState()
    relations = FaultyPurchaseRelations(FakeRelations(), faults)
    faults.relations_down = True
    with pytest.raises(RelationsUnavailableError):
        relations.upsert_product(None)  # type: ignore[arg-type]  # falla antes de usar el argumento


def test_fake_container_boots_with_dataset():
    container = build_container(Settings(adapters="fake"))
    assert len(container.customers.list()) == 8
    assert container.health()["mongo"] == "fake"
