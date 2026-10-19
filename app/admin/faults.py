"""Inyección de fallas para el escenario 07. PROVISTO: no hace falta tocarlo."""

from pydantic import BaseModel

from app.catalog.domain import Product
from app.customers.domain import Customer
from app.orders.domain import Order
from app.orders.ports import PurchaseRelations
from app.shared.errors import RelationsUnavailableError


class FaultState(BaseModel):
    """Banderas de falla activas. Se modifican con `POST /admin/faults`."""

    relations_down: bool = False


class FaultyPurchaseRelations(PurchaseRelations):
    """Decorador de `PurchaseRelations`: si `relations_down` está activo, toda operación falla.

    Simula que el almacén de relaciones de compra se cae sin tener que apagar el contenedor.
    """

    def __init__(self, inner: PurchaseRelations, faults: FaultState):
        self._inner = inner
        self._faults = faults

    def _check(self) -> None:
        if self._faults.relations_down:
            raise RelationsUnavailableError("Relaciones de compra no disponibles (falla inyectada con /admin/faults)")

    def upsert_customer(self, customer: Customer) -> None:
        self._check()
        self._inner.upsert_customer(customer)

    def upsert_product(self, product: Product) -> None:
        self._check()
        self._inner.upsert_product(product)

    def record_purchase(self, order: Order) -> None:
        self._check()
        self._inner.record_purchase(order)
