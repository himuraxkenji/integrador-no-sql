"""Usen el lenguaje nativo del motor mediante el driver oficial (ver docs/guia-consultas.md). No se admiten ORM/ODM/OGM."""

from app.infrastructure.connections import Connections
from app.recommendations.domain import Candidate
from app.recommendations.ports import RecommendationFinder


class RecommendationFinderAdapter(RecommendationFinder):
    """Búsqueda de candidatos de recomendación. El MOTOR lo eligen ustedes.

    Lee las relaciones que escribió `PurchaseRelationsAdapter` (puede ser el mismo motor
    u otro, si el equipo decide proyectar los datos de otra forma).
    Recibe TODAS las conexiones (`connections.mongo`, `connections.redis`, `connections.neo4j`).
    Si eligen Redis: `connections.redis` solo acepta comandos literales vía
    `execute_command(...)` / `pipeline()` (no métodos de conveniencia de redis-py).

    Decisión de motor: registren en docs/decisions.md qué motor eligieron para recomendar,
    cómo expresan la consulta y por qué descartaron las otras opciones.
    """

    def __init__(self, connections: Connections):
        self._conns = connections

    def candidates(self, customer_id: str, limit: int) -> list[Candidate]:
        """Escenario 06.

        Semántica (ver `RecommendationFinder` en `ports.py`):
          - Principal: clientes que compraron lo mismo que el cliente también compraron X.
          - Excluir lo que el cliente ya compró.
          - Puntaje: ¿cuántos clientes distintos compraron cada candidato?
          - Complemento: productos de las categorías de interés del cliente.
          - `Candidate(product_id=..., score=..., reason="also_bought" | "category_interest")`.
        """
        raise NotImplementedError("TODO(alumnos): calcular candidatos de recomendación")
