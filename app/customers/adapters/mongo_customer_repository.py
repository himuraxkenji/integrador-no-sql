from pymongo.database import Database

from app.customers.domain import Customer
from app.customers.ports import CustomerRepository
from app.infrastructure.mongo_utils import from_document, to_document


class MongoCustomerRepository(CustomerRepository):
    """Clientes en MongoDB. Colección sugerida: `customers`. Misma convención `id` <-> `_id`."""

    def __init__(self, db: Database):
        self._col = db["customers"]

    def create(self, customer: Customer) -> Customer:
        raise NotImplementedError("TODO(alumnos): insertar el cliente en MongoDB")

    def get_by_id(self, customer_id: str) -> Customer | None:
        """Escenarios 05 y 06."""
        raise NotImplementedError("TODO(alumnos): buscar un cliente por id")

    def list(self) -> list[Customer]:
        raise NotImplementedError("TODO(alumnos): listar clientes")
