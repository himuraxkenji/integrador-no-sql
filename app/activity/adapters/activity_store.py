"""Usen el lenguaje nativo del motor mediante el driver oficial (ver docs/guia-consultas.md). No se admiten ORM/ODM/OGM."""

from app.activity.domain import ProductViews
from app.activity.ports import ActivityStore
from app.infrastructure.connections import Connections
from app.infrastructure.redis_utils import as_int, pairs, redis_cmd, redis_tx  # noqa: F401  (kit de la cátedra)


class ActivityStoreAdapter(ActivityStore):
    """Contadores de vistas, historial reciente y ranking. El MOTOR lo eligen ustedes.

    Pueden usar un motor distinto para cada necesidad (contador, historial, ranking),
    siempre que cada una cumpla la semántica del puerto `ActivityStore`:
      - contador de vistas por producto (0 si nunca fue visto)
      - historial reciente por cliente: más reciente primero, sin repetidos, ACOTADO a `recent_limit`
      - ranking de más vistos, ordenado de mayor a menor, sin recorrer ni ordenar todo en Python

    `recent_limit` viene de la configuración (RECENT_VIEWS_LIMIT).
    Recibe TODAS las conexiones (`connections.mongo`, `connections.redis`, `connections.neo4j`).
    Si eligen Redis: `connections.redis` solo acepta comandos literales vía
    `execute_command(...)` / `pipeline()` (no métodos de conveniencia de redis-py).

    Kit de la cátedra (`app/infrastructure/redis_utils.py`), plomería lista para usar. Ejemplos con otro dominio:
        redis_cmd(self._conns, "INCR", "biblioteca:visitas")                       # un comando literal
        redis_tx(self._conns, [["INCR", "biblioteca:visitas"], ["SADD", "biblioteca:socios", "soc-007"]])  # MULTI/EXEC
        pairs(redis_cmd(self._conns, "ZRANGE", clave, 0, 4, "REV", "WITHSCORES"))  # [(miembro, puntaje)]
        as_int(redis_cmd(self._conns, "HGET", "biblioteca:socio:soc-007", "prestamos"))  # nil -> 0
    Si eligen otro motor: `cypher_write` / `cypher_read` (`neo4j_utils.py`) o pymongo + `mongo_utils.py`.

    Decisión de motor: registren en docs/decisions.md qué motor eligieron para cada una de las
    tres necesidades, el patrón de acceso y la alternativa descartada.
    """

    def __init__(self, connections: Connections, recent_limit: int):
        self._conns = connections
        self._recent_limit = recent_limit

    def register_view(self, customer_id: str, product_id: str) -> None:
        """Escenario 04. Contador + historial. ¿Qué pasa si las dos escrituras no son atómicas?"""
        raise NotImplementedError("TODO(alumnos): registrar vista (contador + historial acotado)")

    def get_view_count(self, product_id: str) -> int:
        """Escenario 04. Devolver 0 si el producto nunca fue visto."""
        raise NotImplementedError("TODO(alumnos): leer el contador de vistas")

    def recent_products(self, customer_id: str, limit: int) -> list[str]:
        """Escenario 04. Más reciente primero, sin repetidos."""
        raise NotImplementedError("TODO(alumnos): leer el historial reciente del cliente")

    def top_products(self, limit: int) -> list[ProductViews]:
        """Escenario 04. ¿Cómo obtiene el motor elegido un ranking ordenado sin ordenar en Python?"""
        raise NotImplementedError("TODO(alumnos): ranking de productos más vistos")
