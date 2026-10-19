from fastapi import APIRouter, Depends

from app.admin.faults import FaultState
from app.container import Container, get_container
from app.orders.domain import ReconcileReport, SyncStatus

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/faults", response_model=FaultState)
def get_faults(c: Container = Depends(get_container)):
    return c.faults


@router.post("/faults", response_model=FaultState)
def set_faults(body: FaultState, c: Container = Depends(get_container)):
    """Ej.: `{"relations_down": true}` hace que toda escritura de relaciones de compra falle (escenario 07)."""
    c.faults.relations_down = body.relations_down
    return c.faults


@router.get("/sync-status", response_model=SyncStatus)
def sync_status(c: Container = Depends(get_container)):
    """Detección: cantidad de órdenes por estado y lista de las que no llegaron a las relaciones de compra."""
    return c.orders.sync_status()


@router.post("/reconcile", response_model=ReconcileReport)
def reconcile(c: Container = Depends(get_container)):
    """Recuperación: reintenta las relaciones de compra para las órdenes pending/failed."""
    return c.orders.reconcile()
