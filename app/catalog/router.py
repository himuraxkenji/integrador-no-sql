from typing import Any

from fastapi import APIRouter, Depends, Request, Response, status

from app.catalog.domain import Product, ProductCreate, ProductFilter, ProductUpdate
from app.container import Container, get_container

router = APIRouter(prefix="/products", tags=["catalog"])


def _parse_value(raw: str) -> Any:
    """Los query params llegan como texto; los atributos en Mongo pueden ser números/bools."""
    if raw.lower() in ("true", "false"):
        return raw.lower() == "true"
    for cast in (int, float):
        try:
            return cast(raw)
        except ValueError:
            pass
    return raw


@router.post("", response_model=Product, status_code=status.HTTP_201_CREATED)
def create_product(data: ProductCreate, c: Container = Depends(get_container)):
    return c.catalog.create(data)


@router.get("", response_model=list[Product])
def search_products(
    request: Request,
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    available: bool | None = None,
    limit: int = 50,
    skip: int = 0,
    c: Container = Depends(get_container),
):
    """Búsqueda. Atributos específicos con prefijo `attr.`, p. ej. `?category=notebooks&attr.ram_gb=16`."""
    attributes = {
        key.removeprefix("attr."): _parse_value(value)
        for key, value in request.query_params.items()
        if key.startswith("attr.")
    }
    criteria = ProductFilter(
        category=category,
        min_price=min_price,
        max_price=max_price,
        available=available,
        attributes=attributes,
        limit=limit,
        skip=skip,
    )
    return c.catalog.search(criteria)


@router.get("/{product_id}", response_model=Product)
def get_product(product_id: str, response: Response, c: Container = Depends(get_container)):
    """Header `X-Cache`: HIT si la respondió la caché, MISS si la respondió MongoDB."""
    result = c.catalog.get_product(product_id)
    response.headers["X-Cache"] = result.source.value
    return result.product


@router.put("/{product_id}", response_model=Product)
def update_product(product_id: str, changes: ProductUpdate, c: Container = Depends(get_container)):
    return c.catalog.update(product_id, changes)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: str, c: Container = Depends(get_container)):
    c.catalog.delete(product_id)
