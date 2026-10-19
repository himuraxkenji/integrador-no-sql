from app.activity.domain import ProductViews
from app.activity.ports import ActivityStore


class ActivityService:
    """Delegación fina al `ActivityStore`. PROVISTO: el trabajo está en el adaptador `ActivityStoreAdapter`."""

    def __init__(self, store: ActivityStore):
        self._store = store

    def register_view(self, customer_id: str, product_id: str) -> None:
        self._store.register_view(customer_id, product_id)

    def view_count(self, product_id: str) -> int:
        return self._store.get_view_count(product_id)

    def recent(self, customer_id: str, limit: int) -> list[str]:
        return self._store.recent_products(customer_id, limit)

    def top(self, limit: int) -> list[ProductViews]:
        return self._store.top_products(limit)
