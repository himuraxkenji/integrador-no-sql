from pydantic import BaseModel


class ProductViews(BaseModel):
    """Un producto con su cantidad de vistas (para el ranking)."""

    product_id: str
    views: int


class ViewIn(BaseModel):
    customer_id: str
