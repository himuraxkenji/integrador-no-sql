"""Fixtures de los tests unitarios: servicios cableados con los fakes (sin Docker)."""

from types import SimpleNamespace

import pytest

from app.admin.faults import FaultState, FaultyPurchaseRelations
from app.catalog.domain import Product
from app.catalog.service import CatalogService
from app.customers.domain import Customer
from app.fakes import (
    FakeCustomerRepository,
    FakeRelations,
    FakeOrderRepository,
    FakeProductCache,
    FakeProductRepository,
)
from app.orders.service import OrderService
from app.recommendations.service import RecommendationService

TTL = 30


@pytest.fixture(autouse=True)
def _no_miss_delay(monkeypatch):
    """Los tests no esperan: aunque el entorno o un `.env` definan CACHE_MISS_DELAY_SECONDS, acá vale 0."""
    monkeypatch.setenv("CACHE_MISS_DELAY_SECONDS", "0")


@pytest.fixture
def world():
    """Un 'mundo' mínimo: 3 productos, 3 clientes y todos los servicios."""
    products, cache = FakeProductRepository(), FakeProductCache()
    customers, orders = FakeCustomerRepository(), FakeOrderRepository()
    relations, faults = FakeRelations(), FaultState()

    products.create(Product(id="nb", name="Notebook", category="notebooks", price=1000, stock=5))
    products.create(Product(id="ms", name="Mouse", category="mice", price=20, stock=10))
    products.create(Product(id="kb", name="Teclado", category="keyboards", price=80, stock=1))
    for cid in ("ana", "luis", "nuevo"):
        customers.create(Customer(id=cid, name=cid.title(), email=f"{cid}@x.com", interests=["keyboards"]))
        relations.upsert_customer(customers.get_by_id(cid))
    for pid in ("nb", "ms", "kb"):
        relations.upsert_product(products.get_by_id(pid))

    return SimpleNamespace(
        products=products,
        cache=cache,
        orders_repo=orders,
        relations=relations,
        faults=faults,
        catalog=CatalogService(products, cache, TTL),
        orders=OrderService(orders, products, customers, FaultyPurchaseRelations(relations, faults)),
        recommendations=RecommendationService(relations, products),
    )
