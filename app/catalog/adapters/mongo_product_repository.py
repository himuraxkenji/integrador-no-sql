"""Usen el lenguaje nativo del motor mediante el driver oficial (ver docs/guia-consultas.md). No se admiten ORM/ODM/OGM."""

from typing import Any

from pymongo.database import Database

from app.catalog.domain import Product, ProductFilter
from app.catalog.ports import ProductRepository
from app.infrastructure.mongo_utils import from_document, to_document


class MongoProductRepository(ProductRepository):
    """Productos en MongoDB. Colección sugerida: `products`.

    Ayudas provistas (plomería): `to_document(product)` y `from_document(Product, doc)`
    convierten entre el modelo y el documento (`id` <-> `_id`).
    """

    def __init__(self, db: Database):
        self._col = db["products"]

    def create(self, product: Product) -> Product:
        """Escenarios 01-07 (la carga inicial también pasa por acá)."""
        raise NotImplementedError("TODO(alumnos): insertar el producto en MongoDB")

    def get_by_id(self, product_id: str) -> Product | None:
        """Escenarios 01 y 02. Devolver `None` si no existe."""
        raise NotImplementedError("TODO(alumnos): buscar un producto por id")

    def get_many(self, product_ids: list[str]) -> list[Product]:
        """Escenario 06. Pensar: ¿una consulta o N consultas?"""
        raise NotImplementedError("TODO(alumnos): buscar varios productos por id en una sola consulta")

    def update(self, product_id: str, changes: dict[str, Any]) -> Product | None:
        """Escenario 03. Actualizar solo los campos recibidos y devolver el documento nuevo.

        Pista: revisen las opciones de la operación de update de pymongo para
        obtener el documento DESPUÉS del cambio sin hacer una segunda consulta.
        """
        raise NotImplementedError("TODO(alumnos): actualización parcial de un producto")

    def soft_delete(self, product_id: str) -> bool:
        """Escenario 03. No se elimina el documento: se marca como inactivo."""
        raise NotImplementedError("TODO(alumnos): borrado lógico (active = False)")

    def search(self, criteria: ProductFilter) -> list[Product]:
        """Búsqueda por categoría, disponibilidad, rango de precio y atributos.

        Pistas: armen el filtro de a poco según qué criterios vengan informados.
        Los atributos específicos viven dentro del subdocumento `attributes`.
        Piensen qué índices harían falta y anótenlo en docs/decisions.md.
        """
        raise NotImplementedError("TODO(alumnos): búsqueda con filtros combinados")
