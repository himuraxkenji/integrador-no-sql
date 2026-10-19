from typing import Protocol

from app.customers.domain import Customer
from app.catalog.domain import Product
from app.orders.domain import OrderSyncStatus, Order


class OrderRepository(Protocol):
    """Órdenes en MongoDB (fuente de verdad)."""

    def create(self, order: Order) -> Order:
        """Inserta la orden tal como viene (incluye `sync_status`). Escenario 05."""
        ...

    def get(self, order_id: str) -> Order | None:
        """Devuelve la orden o `None`."""
        ...

    def list_by_customer(self, customer_id: str) -> list[Order]:
        """Órdenes del cliente, la más reciente primero."""
        ...

    def list_by_sync_status(self, status: OrderSyncStatus) -> list[Order]:
        """Órdenes con ese estado de sincronización. Escenario 07 (detección)."""
        ...

    def set_sync_status(self, order_id: str, status: OrderSyncStatus, error: str | None = None) -> None:
        """Actualiza `sync_status` y `sync_error` de la orden. Escenarios 05 y 07."""
        ...


class PurchaseRelations(Protocol):
    """Relaciones de compra (proyección derivada de MongoDB; motor a elección del equipo).

    TODAS las operaciones deben ser IDEMPOTENTES: ejecutarlas dos veces
    deja las relaciones igual que ejecutarlas una. La reconciliación depende de eso.
    """

    def upsert_customer(self, customer: Customer) -> None:
        """Asegura el cliente y su interés en cada categoría de `customer.interests`."""
        ...

    def upsert_product(self, product: Product) -> None:
        """Asegura el producto y su pertenencia a su categoría."""
        ...

    def record_purchase(self, order: Order) -> None:
        """Registra la relación "cliente compró producto" por cada ítem de la orden. Escenarios 05 y 07.

        Si la orden ya había sido registrada, no debe duplicar relaciones.
        Puede asumir que el cliente y los productos ya fueron creados con los upsert.
        """
        ...
