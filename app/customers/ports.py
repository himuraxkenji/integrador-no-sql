from typing import Protocol

from app.customers.domain import Customer


class CustomerRepository(Protocol):
    """Clientes en MongoDB. La API los expone solo de lectura; `create` es para la carga inicial."""

    def create(self, customer: Customer) -> Customer:
        """Inserta el cliente (el `id` ya viene definido). Lo usa el seed."""
        ...

    def get_by_id(self, customer_id: str) -> Customer | None:
        """Devuelve el cliente o `None` si no existe. Escenarios 05 y 06."""
        ...

    def list(self) -> list[Customer]:
        """Devuelve todos los clientes (el dataset es chico)."""
        ...
