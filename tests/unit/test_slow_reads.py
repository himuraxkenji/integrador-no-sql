"""Retardo de MISS (demo de caché, cátedra): duerme solo en la lectura por id y con 0 no envuelve."""

import pytest
from pydantic import ValidationError

from app.catalog.domain import Product, ProductFilter
from app.catalog.slow_reads import SlowProductReads, with_miss_delay
from app.config import Settings
from app.container import build_container
from app.fakes import FakeProductRepository


@pytest.fixture
def sleeps(monkeypatch):
    """Registra los `time.sleep` sin dormir de verdad."""
    calls: list[float] = []
    monkeypatch.setattr("app.catalog.slow_reads.time.sleep", calls.append)
    return calls


@pytest.fixture
def repo():
    r = FakeProductRepository()
    r.create(Product(id="nb", name="Notebook", category="notebooks", price=1000, stock=5))
    return r


def test_get_by_id_sleeps_and_delegates(repo, sleeps):
    slow = SlowProductReads(repo, 5)
    assert slow.get_by_id("nb").name == "Notebook"
    assert slow.get_by_id("no-existe") is None
    assert sleeps == [5, 5]


def test_other_methods_delegate_without_sleeping(repo, sleeps):
    slow = SlowProductReads(repo, 5)
    slow.create(Product(id="ms", name="Mouse", category="mice", price=20, stock=1))
    assert [p.id for p in slow.get_many(["nb", "ms"])] == ["nb", "ms"]
    assert slow.update("ms", {"price": 25}).price == 25
    assert slow.soft_delete("ms") is True
    assert slow.search(ProductFilter()) != []
    assert sleeps == []


def test_zero_or_negative_delay_does_not_wrap(repo):
    assert with_miss_delay(repo, 0) is repo
    assert isinstance(with_miss_delay(repo, 0.5), SlowProductReads)


def test_settings_default_is_zero_and_rejects_negative(monkeypatch):
    monkeypatch.delenv("CACHE_MISS_DELAY_SECONDS", raising=False)
    assert Settings(_env_file=None).cache_miss_delay_seconds == 0
    monkeypatch.setenv("CACHE_MISS_DELAY_SECONDS", "-1")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_only_catalog_gets_the_delay(sleeps):
    """Con delay configurado, solo el repo del catálogo está envuelto; órdenes y recomendaciones leen directo."""
    c = build_container(Settings(_env_file=None, adapters="fake", cache_miss_delay_seconds=5))
    assert isinstance(c.catalog._repo, SlowProductReads)
    assert not isinstance(c.orders._products, SlowProductReads)
    assert not isinstance(c.recommendations._products, SlowProductReads)
    c.orders._products.get_by_id("nb-001")
    c.recommendations._products.get_many(["nb-001"])
    assert sleeps == []
    c.catalog._repo.get_by_id("nb-001")
    assert sleeps == [5]


def test_zero_delay_container_is_not_wrapped():
    c = build_container(Settings(_env_file=None, adapters="fake", cache_miss_delay_seconds=0))
    assert not isinstance(c.catalog._repo, SlowProductReads)
