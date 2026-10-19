"""Errores de dominio. Los routers los traducen a códigos HTTP (ver app/main.py)."""


class DomainError(Exception):
    """Base de todos los errores de negocio."""


class NotFoundError(DomainError):
    """El recurso pedido no existe (HTTP 404)."""


class ConflictError(DomainError):
    """La operación choca con el estado actual, p. ej. stock insuficiente (HTTP 409)."""


class RelationsUnavailableError(DomainError):
    """El almacén de relaciones de compra no está disponible (HTTP 503 si se filtra hasta la API)."""
