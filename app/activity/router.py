from fastapi import APIRouter, Depends, status

from app.activity.domain import ProductViews, ViewIn
from app.container import Container, get_container

router = APIRouter(tags=["activity"])

# Decisión: ver un producto NO es un efecto secundario de `GET /products/{id}`.
# La vista se registra de forma explícita con `POST /products/{id}/views`
# (así los escenarios 01-03 de caché no se mezclan con los de actividad).


@router.post("/products/{product_id}/views", status_code=status.HTTP_202_ACCEPTED)
def register_view(product_id: str, body: ViewIn, c: Container = Depends(get_container)):
    c.activity.register_view(body.customer_id, product_id)
    return {"status": "registered"}


@router.get("/products/{product_id}/views")
def view_count(product_id: str, c: Container = Depends(get_container)):
    return {"product_id": product_id, "views": c.activity.view_count(product_id)}


@router.get("/activity/top", response_model=list[ProductViews])
def top_products(limit: int = 10, c: Container = Depends(get_container)):
    return c.activity.top(limit)


@router.get("/customers/{customer_id}/recent")
def recent_products(customer_id: str, limit: int = 10, c: Container = Depends(get_container)):
    # `limit` en la respuesta = largo máximo configurado del historial (RECENT_VIEWS_LIMIT).
    return {"customer_id": customer_id, "product_ids": c.activity.recent(customer_id, limit), "limit": c.activity.recent_limit}
