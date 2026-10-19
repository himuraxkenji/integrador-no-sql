from app.catalog.domain import (
    CacheSource,
    Product,
    ProductCreate,
    ProductFilter,
    ProductResult,
    ProductUpdate,
)
from app.catalog.ports import ProductCache, ProductRepository
from app.shared.errors import NotFoundError
from app.shared.ids import new_id


class CatalogService:
    """Coordina MongoDB (verdad) y la caché de productos para los productos."""

    def __init__(self, repo: ProductRepository, cache: ProductCache, ttl_seconds: int):
        self._repo = repo
        self._cache = cache
        self._ttl = ttl_seconds

    # ---- PROVISTO -------------------------------------------------------

    def create(self, data: ProductCreate) -> Product:
        product = Product(
            id=data.id or new_id("p"),
            name=data.name,
            category=data.category,
            price=data.price,
            stock=data.stock,
            attributes=data.attributes,
        )
        return self._repo.create(product)

    def search(self, criteria: ProductFilter) -> list[Product]:
        return self._repo.search(criteria)

    # ---- TODO(alumnos) ---------------------------------------------------

    def get_product(self, product_id: str) -> ProductResult:
        """Escenarios 01 y 02: lectura con patrón cache-aside.

        Pasos esperados:
          1. Consultar la caché. Si está, devolver `ProductResult(producto, CacheSource.HIT)`.
          2. Si no está, leer de MongoDB (`self._repo`).
             Si no existe o está inactivo (`active == False`), lanzar `NotFoundError`.
          3. Guardar el producto en la caché con el TTL (`self._ttl`).
          4. Devolver `ProductResult(producto, CacheSource.MISS)`.

        Pregunta para pensar: ¿se cachea algo cuando el producto no existe? ¿Qué pasaría si sí?
        """
        raise NotImplementedError("TODO(alumnos): cache-aside en CatalogService.get_product (escenarios 01 y 02)")

    def update(self, product_id: str, changes: ProductUpdate) -> Product:
        """Escenario 03: actualizar sin dejar la caché desactualizada.

        Pasos esperados:
          1. Persistir en MongoDB solo los campos enviados
             (pista: `changes.model_dump(exclude_unset=True)`).
             Si el producto no existe, lanzar `NotFoundError`.
          2. Invalidar la entrada de la caché.
          3. Devolver el producto actualizado.

        Pregunta para pensar: ¿invalidar antes o después de escribir en Mongo? ¿Qué carrera aparece?
        """
        raise NotImplementedError("TODO(alumnos): actualizar + invalidar caché (escenario 03)")

    def delete(self, product_id: str) -> None:
        """Escenario 03: borrado lógico + caché coherente.

        Pasos esperados:
          1. Borrado lógico en MongoDB. Si no existe, lanzar `NotFoundError`.
          2. Invalidar la caché: un producto borrado no puede seguir sirviéndose desde la caché.
        """
        raise NotImplementedError("TODO(alumnos): soft delete + invalidar caché (escenario 03)")
