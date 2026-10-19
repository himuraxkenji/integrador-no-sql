from typing import Protocol

from app.activity.domain import ProductViews


class ActivityStore(Protocol):
    """Actividad de navegación (motor a elección del equipo). Escenario 04.

    El puerto NO dice qué motor ni qué estructura usar: esa decisión es de ustedes
    (y hay que justificarla en docs/decisions.md).
    """

    def register_view(self, customer_id: str, product_id: str) -> None:
        """Registra que un cliente vio un producto. Debe hacer DOS cosas:

        1. Incrementar el contador de vistas del producto.
        2. Actualizar el historial reciente del cliente.

        Piensen: ¿qué pasa si las dos escrituras no son atómicas?
        """
        ...

    def get_view_count(self, product_id: str) -> int:
        """Cantidad total de vistas del producto (0 si nunca fue visto)."""
        ...

    def recent_products(self, customer_id: str, limit: int) -> list[str]:
        """Ids de los últimos productos vistos por el cliente, el más reciente primero.

        Reglas: sin repetidos (ver dos veces el mismo producto lo deja una sola vez,
        en primera posición) y el historial está ACOTADO: nunca guarda más de
        `RECENT_VIEWS_LIMIT` elementos por cliente (se configura en el constructor del adaptador).
        """
        ...

    def top_products(self, limit: int) -> list[ProductViews]:
        """Los `limit` productos más vistos, de mayor a menor cantidad de vistas."""
        ...
