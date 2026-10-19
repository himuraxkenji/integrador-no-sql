from fastapi import APIRouter, Depends, status

from app.container import Container, get_container
from app.orders.domain import Order, OrderCreate

router = APIRouter(tags=["orders"])


@router.post("/orders", response_model=Order, status_code=status.HTTP_201_CREATED)
def create_order(data: OrderCreate, c: Container = Depends(get_container)):
    """201 incluso si `sync_status` vuelve `failed`: la compra quedó registrada en MongoDB."""
    return c.orders.place_order(data.customer_id, data.items)


@router.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: str, c: Container = Depends(get_container)):
    return c.orders.get(order_id)


@router.get("/customers/{customer_id}/orders", response_model=list[Order])
def list_customer_orders(customer_id: str, c: Container = Depends(get_container)):
    return c.orders.list_by_customer(customer_id)
