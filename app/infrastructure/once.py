"""Ejecutar algo UNA sola vez por conexión (índices, restricciones). PROVISTO: uso interno del kit."""

from typing import Any
from weakref import WeakKeyDictionary

_done: "WeakKeyDictionary[Any, set]" = WeakKeyDictionary()


def already_done(owner: Any, key: Any) -> bool:
    """¿Ya se marcó `key` para este `owner` (cliente/driver)?"""
    return key in _done.get(owner, ())


def mark_done(owner: Any, key: Any) -> None:
    _done.setdefault(owner, set()).add(key)
