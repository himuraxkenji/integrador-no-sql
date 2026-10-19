from pydantic import BaseModel

from app.catalog.domain import Product


class Candidate(BaseModel):
    """Lo que devuelve el `RecommendationFinder`: solo un id, un puntaje y el motivo (sin datos comerciales)."""

    product_id: str
    score: float
    reason: str  # p. ej. "also_bought" o "category_interest"


class Recommendation(BaseModel):
    """Lo que devuelve la API: candidato del finder + detalles comerciales de MongoDB."""

    product: Product
    score: float
    reason: str
