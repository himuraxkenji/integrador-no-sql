from fastapi import APIRouter, Depends

from app.container import Container, get_container
from app.customers.domain import Customer

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[Customer])
def list_customers(c: Container = Depends(get_container)):
    return c.customers.list()


@router.get("/{customer_id}", response_model=Customer)
def get_customer(customer_id: str, c: Container = Depends(get_container)):
    return c.customers.get(customer_id)
