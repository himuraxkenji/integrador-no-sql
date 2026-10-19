from app.catalog.ports import ProductRepository
from app.recommendations.domain import Recommendation
from app.recommendations.ports import RecommendationFinder


class RecommendationService:
    """El `RecommendationFinder` decide QUÉ recomendar; MongoDB aporta los detalles comerciales."""

    def __init__(self, finder: RecommendationFinder, products: ProductRepository):
        self._finder = finder
        self._products = products

    def recommend(self, customer_id: str, limit: int = 5) -> list[Recommendation]:
        """Escenario 06.

        Pasos esperados:
          1. Pedir candidatos al `RecommendationFinder`.
          2. Traer los productos de MongoDB en UNA sola consulta (`get_many`).
          3. Descartar los candidatos cuyo producto no exista o esté inactivo
             (el almacén derivado puede conocer productos que ya fueron dados de baja).
          4. Devolver `Recommendation` conservando el orden de puntaje del finder.

        Pregunta para pensar: si descartan productos, ¿cuántos candidatos conviene pedirle al finder?
        """
        raise NotImplementedError("TODO(alumnos): enriquecer candidatos con datos de MongoDB (escenario 06)")
