from app.catalog.ports import ProductRepository
from app.customers.ports import CustomerRepository
from app.orders.domain import (
    Order,
    OrderItemRequest,
    OrderSyncStatus,
    ReconcileReport,
    SyncStatus,
)
from app.orders.ports import OrderRepository, PurchaseRelations
from app.shared.errors import NotFoundError


class OrderService:
    """Compra: MongoDB (fuente de verdad) primero, relaciones derivadas después. Sin transacción distribuida."""

    def __init__(
        self,
        orders: OrderRepository,
        products: ProductRepository,
        customers: CustomerRepository,
        relations: PurchaseRelations,
    ):
        self._orders = orders
        self._products = products
        self._customers = customers
        self._relations = relations

    # ---- PROVISTO -------------------------------------------------------

    def get(self, order_id: str) -> Order:
        order = self._orders.get(order_id)
        if order is None:
            raise NotFoundError(f"Orden '{order_id}' no encontrada")
        return order

    def list_by_customer(self, customer_id: str) -> list[Order]:
        return self._orders.list_by_customer(customer_id)

    def sync_status(self) -> SyncStatus:
        """Escenario 07: cuántas órdenes hay en cada estado y cuáles están sin sincronizar."""
        by_status = {s: self._orders.list_by_sync_status(s) for s in OrderSyncStatus}
        return SyncStatus(
            counts={s.value: len(orders) for s, orders in by_status.items()},
            unsynced=by_status[OrderSyncStatus.PENDING] + by_status[OrderSyncStatus.FAILED],
        )

    def _project_to_relations(self, order: Order) -> None:
        """Refleja UNA orden en las relaciones de compra (upserts + compra). Lanza excepción si el almacén derivado falla.

        Es idempotente porque el puerto `PurchaseRelations` lo es. Usenlo tanto en
        `place_order` como en `reconcile`.
        """
        customer = self._customers.get_by_id(order.customer_id)
        if customer is None:
            raise NotFoundError(f"Cliente '{order.customer_id}' no encontrado")
        self._relations.upsert_customer(customer)
        for item in order.items:
            product = self._products.get_by_id(item.product_id)
            if product is not None:
                self._relations.upsert_product(product)
        self._relations.record_purchase(order)

    # ---- TODO(alumnos) ---------------------------------------------------

    def place_order(self, customer_id: str, items: list[OrderItemRequest]) -> Order:
        """Escenarios 05 y 07: registrar una compra sin perderla nunca.

        Pasos esperados:
          1. Validar que el cliente exista (`NotFoundError`) y que cada producto exista y
             esté activo (`NotFoundError`).
          2. Verificar stock suficiente para cada ítem (`ConflictError` si no alcanza).
          3. Armar la orden: id nuevo (`new_id("o")`), `OrderItem` con el PRECIO ACTUAL del
             producto como `unit_price` (snapshot), `total` con `compute_total`, estado `PENDING`.
          4. Persistir la orden en MongoDB. A partir de acá la orden EXISTE, pase lo que pase.
          5. Intentar reflejarla en las relaciones de compra con `self._project_to_relations(order)`.
               - Si sale bien: marcar `SYNCED`.
               - Si falla (cualquier excepción): marcar `FAILED` guardando el mensaje de error.
                 NO relanzar el error: la compra se registró, las relaciones quedaron atrasadas.
          6. Devolver la orden con su estado final.

        Pregunta para pensar: ¿por qué no revertimos la orden en Mongo si el almacén de relaciones falla?
        """
        raise NotImplementedError("TODO(alumnos): flujo de compra (escenarios 05 y 07)")

    def reconcile(self) -> ReconcileReport:
        """Escenario 07: recuperar las órdenes que no llegaron a las relaciones de compra.

        Pasos esperados:
          1. Buscar las órdenes `PENDING` y `FAILED`.
          2. Para cada una, reintentar `self._project_to_relations(order)`.
               - Éxito: marcar `SYNCED` (y limpiar el error).
               - Falla: dejarla `FAILED` con el nuevo mensaje; seguir con las demás.
          3. Devolver un `ReconcileReport` con los totales.

        Tiene que ser seguro ejecutarlo varias veces seguidas (idempotencia).
        """
        raise NotImplementedError("TODO(alumnos): reconciliación Mongo -> relaciones de compra (escenario 07)")
