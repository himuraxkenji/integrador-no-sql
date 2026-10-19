from fastapi import APIRouter, Depends

from app.container import Container, get_container
from app.recommendations.domain import Recommendation

router = APIRouter(tags=["recommendations"])


@router.get("/customers/{customer_id}/recommendations", response_model=list[Recommendation])
def get_recommendations(customer_id: str, limit: int = 5, c: Container = Depends(get_container)):
    return c.recommendations.recommend(customer_id, limit)
