"""Carga el dataset de `datasets/` a través de los PUERTOS. PROVISTO.

Lo usan `python -m scripts.seed` (motores reales) y el modo `ADAPTERS=fake` (memoria).
Como pasa por los puertos, el seed funciona con los motores reales recién cuando
ustedes implementaron los adaptadores.
"""

import json
from pathlib import Path

from app.catalog.domain import Product
from app.catalog.ports import ProductRepository
from app.customers.domain import Customer
from app.customers.ports import CustomerRepository
from app.orders.domain import OrderSyncStatus, Order
from app.orders.ports import OrderRepository, PurchaseRelations

DATASETS_DIR = Path(__file__).resolve().parent.parent / "datasets"


def _load(name: str, datasets_dir: Path) -> list[dict]:
    return json.loads((datasets_dir / name).read_text(encoding="utf-8"))


def load_dataset(
    products: ProductRepository,
    customers: CustomerRepository,
    orders: OrderRepository,
    relations: PurchaseRelations,
    datasets_dir: Path = DATASETS_DIR,
) -> None:
    for raw in _load("products.json", datasets_dir):
        product = Product.model_validate(raw)
        products.create(product)
        relations.upsert_product(product)

    for raw in _load("customers.json", datasets_dir):
        customer = Customer.model_validate(raw)
        customers.create(customer)
        relations.upsert_customer(customer)

    for raw in _load("orders.json", datasets_dir):
        order = Order.model_validate(raw)  # arranca en `pending`
        orders.create(order)
        relations.record_purchase(order)
        orders.set_sync_status(order.id, OrderSyncStatus.SYNCED)
