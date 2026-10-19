"""Plomería para mapear modelos pydantic <-> documentos de MongoDB. PROVISTO.

Convención: el campo `id` del modelo se guarda como `_id` en Mongo.
"""

from typing import Any, TypeVar

from pydantic import BaseModel

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
