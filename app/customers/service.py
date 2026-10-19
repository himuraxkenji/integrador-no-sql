from app.customers.domain import Customer
from app.customers.ports import CustomerRepository
from app.shared.errors import NotFoundError


class CustomerService:
    """Lectura de clientes. PROVISTO."""

    def __init__(self, repo: CustomerRepository):
        self._repo = repo

    def get(self, customer_id: str) -> Customer:
        customer = self._repo.get_by_id(customer_id)
        if customer is None:
            raise NotFoundError(f"Cliente '{customer_id}' no encontrado")
        return customer

    def list(self) -> list[Customer]:
        return self._repo.list()
