from uuid import uuid4


def new_id(prefix: str) -> str:
    """Genera un id legible, p. ej. `o-3f9a1c2b`."""
    return f"{prefix}-{uuid4().hex[:8]}"
