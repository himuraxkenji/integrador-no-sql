from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración leída de variables de entorno (o del archivo `.env`)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    adapters: Literal["real", "fake"] = "real"

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "nexus"
    redis_url: str = "redis://localhost:6379/0"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "nexus-dev-password"  # solo desarrollo local

    cache_ttl_seconds: int = 60
    # Retardo artificial (s) de la lectura en la fuente cuando la caché no tiene el producto (MISS). 0 = sin retardo.
    cache_miss_delay_seconds: float = Field(default=0, ge=0)
    recent_views_limit: int = 10
