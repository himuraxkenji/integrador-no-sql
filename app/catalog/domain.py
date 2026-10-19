from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Product(BaseModel):
    """Producto del catálogo. La fuente de verdad es MongoDB.

    `attributes` varía según la categoría. Ejemplos:
      notebooks -> {"ram_gb": 16, "cpu": "i5"}   monitors -> {"size_inches": 27, "panel": "IPS"}
    """

    id: str
    name: str
    category: str
    price: float = Field(gt=0)
    stock: int = Field(ge=0)
    active: bool = True  # False = borrado lógico (soft delete)
    attributes: dict[str, Any] = Field(default_factory=dict)


class ProductCreate(BaseModel):
    id: str | None = None  # si no viene, el servicio genera uno
    name: str
    category: str
    price: float = Field(gt=0)
    stock: int = Field(ge=0)
    attributes: dict[str, Any] = Field(default_factory=dict)


class ProductUpdate(BaseModel):
    """Actualización parcial: solo se modifican los campos enviados."""

    name: str | None = None
    category: str | None = None
    price: float | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)
    attributes: dict[str, Any] | None = None  # si viene, reemplaza el dict completo


class ProductFilter(BaseModel):
    """Criterios de búsqueda. Todos opcionales; los que vienen se combinan con AND."""

    category: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    available: bool | None = None  # True = stock > 0, False = stock == 0
    attributes: dict[str, Any] = Field(default_factory=dict)  # igualdad exacta por atributo
    limit: int = 50
    skip: int = 0


class CacheSource(str, Enum):
    """De dónde salió la respuesta. Se expone en el header `X-Cache`."""

    HIT = "HIT"  # la respondió la caché
    MISS = "MISS"  # la respondió MongoDB


@dataclass
class ProductResult:
    """Lo que devuelve `CatalogService.get_product`: el producto + su origen."""

    product: Product
    source: CacheSource
