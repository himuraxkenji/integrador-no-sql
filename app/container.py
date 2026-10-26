"""Cableado de dependencias. PROVISTO: acá se elige real vs fake según `ADAPTERS`."""

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Request

from app.activity.adapters.activity_store import ActivityStoreAdapter
from app.activity.service import ActivityService
from app.admin.faults import FaultState, FaultyPurchaseRelations
from app.catalog.adapters.mongo_product_repository import MongoProductRepository
from app.catalog.adapters.product_cache import ProductCacheAdapter
from app.catalog.service import CatalogService
from app.catalog.slow_reads import with_miss_delay
from app.config import Settings
from app.customers.adapters.mongo_customer_repository import MongoCustomerRepository
from app.customers.service import CustomerService
from app.fakes import (
    FakeActivityStore,
    FakeCustomerRepository,
    FakeRelations,
    FakeOrderRepository,
    FakeProductCache,
    FakeProductRepository,
)
from app.infrastructure.connections import Connections
from app.orders.adapters.mongo_order_repository import MongoOrderRepository
from app.orders.adapters.purchase_relations import PurchaseRelationsAdapter
from app.orders.service import OrderService
from app.recommendations.adapters.recommendation_finder import RecommendationFinderAdapter
from app.recommendations.service import RecommendationService
from app.seeding import load_dataset


@dataclass
class Container:
    catalog: CatalogService
    customers: CustomerService
    activity: ActivityService
    orders: OrderService
    recommendations: RecommendationService
    faults: FaultState
    health: Callable[[], dict[str, str]]
    close: Callable[[], None]


def build_container(settings: Settings) -> Container:
    faults = FaultState()

    if settings.adapters == "fake":
        products, cache = FakeProductRepository(), FakeProductCache()
        activity_store = FakeActivityStore(settings.recent_views_limit)
        customers, orders = FakeCustomerRepository(), FakeOrderRepository()
        relations = FakeRelations()
        load_dataset(products, customers, orders, relations)  # el modo fake arranca con datos
        purchase_relations, finder = FaultyPurchaseRelations(relations, faults), relations
        health = lambda: {"mongo": "fake", "redis": "fake", "neo4j": "fake"}  # noqa: E731
        close = lambda: None  # noqa: E731
    else:
        conns = Connections.open(settings)
        products, cache = MongoProductRepository(conns.mongo), ProductCacheAdapter(conns)
        activity_store = ActivityStoreAdapter(conns, settings.recent_views_limit)
        customers, orders = MongoCustomerRepository(conns.mongo), MongoOrderRepository(conns.mongo)
        purchase_relations = FaultyPurchaseRelations(PurchaseRelationsAdapter(conns), faults)
        finder = RecommendationFinderAdapter(conns)
        health, close = conns.ping, conns.close

    return Container(
        # Solo el catálogo ve la fuente "lenta" (demo de caché); órdenes y recomendaciones leen `products` directo.
        catalog=CatalogService(
            with_miss_delay(products, settings.cache_miss_delay_seconds), cache, settings.cache_ttl_seconds
        ),
        customers=CustomerService(customers),
        activity=ActivityService(activity_store, settings.recent_views_limit),
        orders=OrderService(orders, products, customers, purchase_relations),
        recommendations=RecommendationService(finder, products),
        faults=faults,
        health=health,
        close=close,
    )


def get_container(request: Request) -> Container:
    """Dependencia de FastAPI: devuelve el contenedor creado en el arranque."""
    return request.app.state.container
