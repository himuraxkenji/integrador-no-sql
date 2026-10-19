from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class OrderSyncStatus(str, Enum):
    """Estado de la sincronización de la orden con las relaciones de compra. Se persiste en MongoDB."""

    PENDING = "pending"  # la orden existe en Mongo, las relaciones de compra todavía no se actualizaron
    SYNCED = "synced"  # las relaciones reflejan la compra
    FAILED = "failed"  # se intentó actualizar las relaciones y falló (hay que reconciliar)


class OrderItemRequest(BaseModel):
    product_id: str
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    customer_id: str
    items: list[OrderItemRequest] = Field(min_length=1)


class OrderItem(BaseModel):
    """Línea de una orden. `unit_price` es el precio AL MOMENTO de la compra (snapshot)."""

    product_id: str
    quantity: int = Field(gt=0)
    unit_price: float


class Order(BaseModel):
    id: str
    customer_id: str
    items: list[OrderItem]
    total: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sync_status: OrderSyncStatus = OrderSyncStatus.PENDING
    sync_error: str | None = None  # último error al sincronizar las relaciones de compra, si lo hubo


def compute_total(items: list[OrderItem]) -> float:
    return round(sum(i.unit_price * i.quantity for i in items), 2)


class SyncStatus(BaseModel):
    """Resumen para `GET /admin/sync-status`."""

    counts: dict[str, int]
    unsynced: list[Order]  # órdenes pending o failed


class ReconcileReport(BaseModel):
    """Resultado de `POST /admin/reconcile`."""

    checked: int  # órdenes pending/failed revisadas
    synced: int  # las que se lograron sincronizar ahora
    still_failed: int  # las que siguen sin sincronizar
    synced_order_ids: list[str] = Field(default_factory=list)
