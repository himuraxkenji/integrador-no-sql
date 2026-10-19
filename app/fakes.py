"""Implementaciones EN MEMORIA de todos los puertos. PROVISTO.

Sirven para dos cosas:
  1. Levantar la API sin Docker (`ADAPTERS=fake`).
  2. Probar los flujos de servicio en tests unitarios.

Son simples a propósito (dicts y listas): NO muestran cómo se consulta cada motor.
"""

from collections import Counter

from app.activity.domain import ProductViews
from app.activity.ports import ActivityStore
from app.catalog.domain import Product, ProductFilter
from app.catalog.ports import ProductCache, ProductRepository
from app.customers.domain import Customer
from app.customers.ports import CustomerRepository
from app.orders.domain import OrderSyncStatus, Order
from app.orders.ports import OrderRepository, PurchaseRelations
from app.recommendations.domain import Candidate
from app.recommendations.ports import RecommendationFinder


class FakeProductRepository(ProductRepository):
    def __init__(self):
        self._items: dict[str, Product] = {}

    def create(self, product):
        self._items[product.id] = product.model_copy(deep=True)
        return product

    def get_by_id(self, product_id):
        item = self._items.get(product_id)
        return item.model_copy(deep=True) if item else None

    def get_many(self, product_ids):
        return [self._items[i].model_copy(deep=True) for i in product_ids if i in self._items]

    def update(self, product_id, changes):
        item = self._items.get(product_id)
        if item is None:
            return None
        self._items[product_id] = item.model_copy(update=changes)
        return self.get_by_id(product_id)

    def soft_delete(self, product_id):
        item = self._items.get(product_id)
        if item is None:
            return False
        item.active = False
        return True

    def search(self, criteria: ProductFilter):
        def matches(p: Product) -> bool:
            return (
                p.active
                and (criteria.category is None or p.category == criteria.category)
                and (criteria.min_price is None or p.price >= criteria.min_price)
                and (criteria.max_price is None or p.price <= criteria.max_price)
                and (criteria.available is None or (p.stock > 0) == criteria.available)
                and all(p.attributes.get(k) == v for k, v in criteria.attributes.items())
            )

        found = [p.model_copy(deep=True) for p in self._items.values() if matches(p)]
        return found[criteria.skip : criteria.skip + criteria.limit]


class FakeProductCache(ProductCache):
    """Guarda JSON (como un almacén clave-valor) y recuerda el TTL pedido. Los TTL no expiran solos."""

    def __init__(self):
        self._data: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def get(self, product_id):
        raw = self._data.get(product_id)
        return Product.model_validate_json(raw) if raw else None

    def set(self, product, ttl_seconds):
        self._data[product.id] = product.model_dump_json()
        self.ttls[product.id] = ttl_seconds

    def invalidate(self, product_id):
        self._data.pop(product_id, None)
        self.ttls.pop(product_id, None)

    def contains(self, product_id: str) -> bool:
        return product_id in self._data


class FakeActivityStore(ActivityStore):
    def __init__(self, recent_limit: int = 10):
        self._limit = recent_limit
        self._views: Counter[str] = Counter()
        self._recent: dict[str, list[str]] = {}

    def register_view(self, customer_id, product_id):
        self._views[product_id] += 1
        history = [p for p in self._recent.get(customer_id, []) if p != product_id]
        self._recent[customer_id] = ([product_id] + history)[: self._limit]

    def get_view_count(self, product_id):
        return self._views[product_id]

    def recent_products(self, customer_id, limit):
        return self._recent.get(customer_id, [])[:limit]

    def top_products(self, limit):
        ranked = sorted(self._views.items(), key=lambda kv: (-kv[1], kv[0]))
        return [ProductViews(product_id=p, views=v) for p, v in ranked[:limit]]


class FakeCustomerRepository(CustomerRepository):
    def __init__(self):
        self._items: dict[str, Customer] = {}

    def create(self, customer):
        self._items[customer.id] = customer
        return customer

    def get_by_id(self, customer_id):
        return self._items.get(customer_id)

    def list(self):
        return list(self._items.values())


class FakeOrderRepository(OrderRepository):
    def __init__(self):
        self._items: dict[str, Order] = {}

    def create(self, order):
        self._items[order.id] = order.model_copy(deep=True)
        return order

    def get(self, order_id):
        item = self._items.get(order_id)
        return item.model_copy(deep=True) if item else None

    def list_by_customer(self, customer_id):
        mine = [o for o in self._items.values() if o.customer_id == customer_id]
        return [o.model_copy(deep=True) for o in sorted(mine, key=lambda o: o.created_at, reverse=True)]

    def list_by_sync_status(self, status):
        return [o.model_copy(deep=True) for o in self._items.values() if o.sync_status == status]

    def set_sync_status(self, order_id, status: OrderSyncStatus, error=None):
        order = self._items[order_id]
        order.sync_status = status
        order.sync_error = error


class FakeRelations(PurchaseRelations, RecommendationFinder):
    """Un único almacén de relaciones en memoria que implementa escritura Y recomendaciones."""

    def __init__(self):
        self.interests: dict[str, set[str]] = {}
        self.product_category: dict[str, str] = {}
        self.purchases: dict[str, set[str]] = {}

    def upsert_customer(self, customer):
        self.interests[customer.id] = set(customer.interests)
        self.purchases.setdefault(customer.id, set())

    def upsert_product(self, product):
        self.product_category[product.id] = product.category

    def record_purchase(self, order):
        self.purchases.setdefault(order.customer_id, set()).update(i.product_id for i in order.items)

    def candidates(self, customer_id, limit):
        bought = self.purchases.get(customer_id, set())
        scores: Counter[str] = Counter()
        for other, theirs in self.purchases.items():
            if other != customer_id and theirs & bought:
                for pid in theirs - bought:
                    scores[pid] += 1
        found = [Candidate(product_id=p, score=float(n), reason="also_bought") for p, n in scores.items()]
        wanted = self.interests.get(customer_id, set())
        for pid, category in self.product_category.items():
            if category in wanted and pid not in bought and pid not in scores:
                found.append(Candidate(product_id=pid, score=0.5, reason="category_interest"))
        found.sort(key=lambda c: (-c.score, c.product_id))
        return found[:limit]
