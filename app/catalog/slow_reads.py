"""Fuente de verdad "lenta" para la demo de caché. PROVISTO (cátedra): no hay que tocarlo.

La caché sirve para evitar leer la fuente principal; con MongoDB local la diferencia entre HIT y MISS
son milisegundos y no se nota. Este wrapper agrega un retardo configurable
(`CACHE_MISS_DELAY_SECONDS`) a la lectura por id que usa el cache-aside, así el MISS tarda
unos segundos y el HIT sigue siendo instantáneo.

Se aplica SOLO en el cableado del `CatalogService` (ver `app/container.py`): órdenes, recomendaciones
y el resto de los consumidores del repositorio reciben el repositorio sin envolver.
"""

import time
from typing import Any

from app.catalog.domain import Product
from app.catalog.ports import ProductRepository


class SlowProductReads:
    """Decorador de `ProductRepository`: duerme antes de `get_by_id`; el resto se delega tal cual.

    Escrituras (`create`, `update`, `soft_delete`) y listados (`search`, `get_many`) NO se demoran:
    no pasan por la caché, así que no tiene sentido simular una fuente lenta ahí.
    """

    def __init__(self, inner: ProductRepository, delay_seconds: float):
        self._inner = inner
        self._delay = delay_seconds

    def get_by_id(self, product_id: str) -> Product | None:
        # El servicio es síncrono (FastAPI lo corre en un hilo del pool): dormir no bloquea el event loop.
        time.sleep(self._delay)
        return self._inner.get_by_id(product_id)

    def __getattr__(self, name: str) -> Any:
        # Solo se invoca para lo que no definimos acá: create, get_many, update, soft_delete, search.
        return getattr(self._inner, name)


def with_miss_delay(repo: ProductRepository, delay_seconds: float) -> ProductRepository:
    """Envuelve `repo` si hay retardo configurado; con `delay_seconds <= 0` devuelve el mismo repo."""
    return SlowProductReads(repo, delay_seconds) if delay_seconds > 0 else repo
