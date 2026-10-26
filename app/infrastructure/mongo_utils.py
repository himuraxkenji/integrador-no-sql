"""Kit de la cátedra para MongoDB: mapeo modelo <-> documento e índices. PROVISTO.

Convención: el campo `id` del modelo se guarda como `_id` en Mongo.
Son TRANSPORTE: el filtro, el `$set`, el pipeline y el orden los escribís vos con pymongo.

    col.insert_one(to_document(product))
    producto = from_document(Product, col.find_one({"_id": "p1"}))
    productos = from_documents(Product, col.find({"active": True}).sort("price", 1))
    ensure_indexes(col, [IndexModel([("category", 1), ("price", 1)], name="category_price")])
"""

from collections.abc import Iterable
from typing import Any, TypeVar

from pydantic import BaseModel
from pymongo.collection import Collection
from pymongo.operations import IndexModel

from app.infrastructure.once import already_done, mark_done

M = TypeVar("M", bound=BaseModel)


def to_document(model: BaseModel) -> dict[str, Any]:
    """Modelo -> documento (`id` pasa a `_id`)."""
    doc = model.model_dump(mode="python")
    doc["_id"] = doc.pop("id")
    return doc


def from_document(model_cls: type[M], doc: dict[str, Any]) -> M:
    """Documento -> modelo (`_id` pasa a `id`)."""
    data = dict(doc)
    data["id"] = data.pop("_id")
    return model_cls.model_validate(data)


def from_documents(model_cls: type[M], docs: Iterable[dict[str, Any]]) -> list[M]:
    """Documentos (lista o cursor) -> lista de modelos: `from_documents(Product, col.find(filtro))`."""
    return [from_document(model_cls, doc) for doc in docs]


def ensure_indexes(collection: Collection, indexes: list[IndexModel]) -> None:
    """Crea los índices UNA vez por cliente y colección (`create_indexes` ya es idempotente).

    Es seguro llamarla al inicio de cada operación: las llamadas siguientes no hacen nada.
    Ejemplo: `ensure_indexes(col, [IndexModel([("category", 1), ("price", 1)], name="category_price")])`.
    """
    client = collection.database.client
    key = ("ensure_indexes", collection.full_name, tuple(i.document["name"] for i in indexes))
    if already_done(client, key):
        return
    collection.create_indexes(indexes)
    mark_done(client, key)
