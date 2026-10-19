from typing import Any, Protocol

from app.catalog.domain import Product, ProductFilter


class ProductRepository(Protocol):
    """Persistencia de productos en MongoDB (fuente de verdad).

    Convención: el repositorio NO filtra por `active` salvo en `search`.
    Decidir qué hacer con un producto inactivo es responsabilidad del servicio.
    """

    def create(self, product: Product) -> Product:
        """Inserta el producto (el `id` ya viene definido) y lo devuelve."""
        ...

    def get_by_id(self, product_id: str) -> Product | None:
        """Devuelve el producto (activo o no) o `None` si no existe."""
        ...

    def get_many(self, product_ids: list[str]) -> list[Product]:
        """Devuelve los productos que existan para esos ids (activos o no).

        Los ids inexistentes se ignoran. No se garantiza el orden.
        Lo usa recomendaciones (escenario 06) para traer detalles comerciales.
        """
        ...

    def update(self, product_id: str, changes: dict[str, Any]) -> Product | None:
        """Aplica solo los campos de `changes` y devuelve el producto ya actualizado.

        Devuelve `None` si no existe. Escenario 03.
        """
        ...

    def soft_delete(self, product_id: str) -> bool:
        """Marca `active = False` (NO borra el documento). `False` si no existía."""
        ...

    def search(self, criteria: ProductFilter) -> list[Product]:
        """Busca productos ACTIVOS que cumplan todos los criterios informados.

        Ver `ProductFilter`: categoría, rango de precio, disponibilidad y atributos.
        Respeta `limit` y `skip`.
        """
        ...


class ProductCache(Protocol):
    """Caché de productos (motor a elección del equipo). Solo guarda y recupera; no decide políticas."""

    def get(self, product_id: str) -> Product | None:
        """Devuelve el producto cacheado o `None` si no está (o expiró). Escenarios 01 y 02."""
        ...

    def set(self, product: Product, ttl_seconds: int) -> None:
        """Guarda el producto con vencimiento (TTL). Escenario 01."""
        ...

    def invalidate(self, product_id: str) -> None:
        """Elimina la entrada. Debe ser seguro llamarla si la clave no existe. Escenario 03."""
        ...
