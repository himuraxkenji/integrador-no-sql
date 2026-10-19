from app.catalog.domain import Product
from app.catalog.ports import ProductCache
from app.infrastructure.connections import Connections


class ProductCacheAdapter(ProductCache):
    """Caché de productos. El MOTOR lo eligen ustedes (MongoDB, Redis o Neo4j).

    Semántica requerida (ver `ProductCache` en `ports.py`):
      - `get` devuelve `None` si la entrada no existe O ya venció (TTL).
      - `set` guarda el producto con vencimiento; escritura y TTL, ¿una sola operación?
      - `invalidate` no falla si la entrada no existe.
    Escenarios: 01 (miss y carga), 02 (hit), 03 (la actualización invalida).

    Recibe TODAS las conexiones (`connections.mongo`, `connections.redis`,
    `connections.neo4j`) para que usen la que elijan. Pistas de plomería:
    `product.model_dump_json()` serializa y `Product.model_validate_json(texto)` deserializa.

    Decisión de motor: registren en docs/decisions.md qué motor eligieron para la caché,
    cómo modelaron las entradas (convención de claves/documentos) y cómo logran el vencimiento
    con ese motor. Documenten la convención en docs/data-model.md.
    """

    def __init__(self, connections: Connections):
        self._conns = connections

    def get(self, product_id: str) -> Product | None:
        """Escenarios 01 y 02. `None` si la entrada no existe o ya expiró."""
        raise NotImplementedError("TODO(alumnos): leer el producto de la caché")

    def set(self, product: Product, ttl_seconds: int) -> None:
        """Escenario 01. La escritura y el vencimiento deberían ser una sola operación."""
        raise NotImplementedError("TODO(alumnos): guardar el producto en la caché con TTL")

    def invalidate(self, product_id: str) -> None:
        """Escenario 03. No debe fallar si la entrada no existe."""
        raise NotImplementedError("TODO(alumnos): eliminar la entrada de la caché")
