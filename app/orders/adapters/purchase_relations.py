"""Usen el lenguaje nativo del motor mediante el driver oficial (ver docs/guia-consultas.md). No se admiten ORM/ODM/OGM."""

from app.catalog.domain import Product
from app.customers.domain import Customer
from app.infrastructure.connections import Connections
from app.orders.domain import Order
from app.orders.ports import PurchaseRelations


class PurchaseRelationsAdapter(PurchaseRelations):
    """Relaciones de compra derivadas de MongoDB. El MOTOR lo eligen ustedes.

    Información a representar (el modelado concreto depende del motor):
      - qué cliente compró qué producto
      - a qué categoría pertenece cada producto
      - en qué categorías está interesado cada cliente (`customer.interests`)
    Esta información alimenta las recomendaciones (escenario 06).

    Requisito central: TODAS las operaciones deben ser IDEMPOTENTES. Ejecutarlas dos veces
    deja el mismo resultado que ejecutarlas una; la reconciliación (escenario 07) depende de eso.
    ¿Cómo lo garantiza el motor que eligieron?

    Recibe TODAS las conexiones (`connections.mongo`, `connections.redis`, `connections.neo4j`).

    Decisión de motor: registren en docs/decisions.md qué motor eligieron para las relaciones
    de compra, cómo las modelaron y por qué descartaron las otras opciones.
    """

    def __init__(self, connections: Connections):
        self._conns = connections

    def upsert_customer(self, customer: Customer) -> None:
        """Asegura el cliente y sus intereses por categoría. Idempotente."""
        raise NotImplementedError("TODO(alumnos): upsert del cliente y sus intereses")

    def upsert_product(self, product: Product) -> None:
        """Asegura el producto y su pertenencia a una categoría. Idempotente."""
        raise NotImplementedError("TODO(alumnos): upsert del producto y su categoría")

    def record_purchase(self, order: Order) -> None:
        """Escenarios 05 y 07. Si se ejecuta dos veces para la misma orden, no duplica relaciones."""
        raise NotImplementedError("TODO(alumnos): registrar la compra de forma idempotente")
