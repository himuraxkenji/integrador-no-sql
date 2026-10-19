from typing import Protocol

from app.recommendations.domain import Candidate


class RecommendationFinder(Protocol):
    """Consulta de candidatos de recomendación (motor a elección del equipo). Escenario 06."""

    def candidates(self, customer_id: str, limit: int) -> list[Candidate]:
        """Productos candidatos para el cliente, del mejor al peor puntaje.

        Reglas:
          - Principal: "clientes que compraron lo mismo que vos también compraron X".
          - Complemento: productos de las categorías de interés del cliente.
          - NUNCA incluir productos que el cliente ya compró.
          - Sin repetidos. Como máximo `limit` candidatos.
          - Devuelve solo ids, puntaje y motivo: los detalles los pone MongoDB.
        """
        ...
