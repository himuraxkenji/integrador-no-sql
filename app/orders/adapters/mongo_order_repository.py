"""Usen el lenguaje nativo del motor mediante el driver oficial (ver docs/guia-consultas.md). No se admiten ORM/ODM/OGM."""

from pymongo.database import Database

from app.infrastructure.mongo_utils import from_document, to_document
from app.orders.domain import OrderSyncStatus, Order
from app.orders.ports import OrderRepository


class MongoOrderRepository(OrderRepository):
    """Órdenes en MongoDB. Colección sugerida: `orders`.

    Cada orden guarda sus ítems embebidos (con el precio snapshot) y `sync_status`.
    Plomería provista: `to_document(order)` / `from_document(Order, doc)`.
    Ojo: `OrderSyncStatus` es un Enum de `str`; guardenlo como texto (`status.value`).
    """

    def __init__(self, db: Database):
        self._col = db["orders"]

    def create(self, order: Order) -> Order:
        """Escenario 05."""
        raise NotImplementedError("TODO(alumnos): insertar la orden en MongoDB")

    def get(self, order_id: str) -> Order | None:
        raise NotImplementedError("TODO(alumnos): buscar una orden por id")

    def list_by_customer(self, customer_id: str) -> list[Order]:
        """Más reciente primero."""
        raise NotImplementedError("TODO(alumnos): listar órdenes de un cliente, ordenadas")

    def list_by_sync_status(self, status: OrderSyncStatus) -> list[Order]:
        """Escenario 07. Pensar: ¿qué índice acelera esta consulta cuando hay millones de órdenes?"""
        raise NotImplementedError("TODO(alumnos): listar órdenes por estado de sincronización")

    def set_sync_status(self, order_id: str, status: OrderSyncStatus, error: str | None = None) -> None:
        """Escenarios 05 y 07. Actualizar solo los dos campos de sincronización."""
        raise NotImplementedError("TODO(alumnos): actualizar sync_status y sync_error")
