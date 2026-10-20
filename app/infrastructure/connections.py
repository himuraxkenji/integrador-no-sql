"""Creación y cierre de los clientes de cada motor. PROVISTO: no hace falta tocarlo.

Los adaptadores reciben este objeto `Connections` completo y usan el motor que
corresponda. MongoDB es fijo para repositorios; los almacenes derivados son a elección.
Clientes disponibles:
  - MongoDB: `pymongo.database.Database`
  - Redis:   `RedisCommands` (abajo): SOLO `execute_command(...)` y `pipeline()`.
             Comandos literales, como en redis-cli. decode_responses=True: devuelve `str`.
  - Neo4j:   `neo4j.Driver` (usen `driver.session()` en cada operación)
"""

from dataclasses import dataclass

from neo4j import Driver, GraphDatabase
from pymongo import MongoClient
from pymongo.database import Database
from redis import Redis

from app.config import Settings

REDIS_LITERAL_MSG = (
    "Usen comandos literales: execute_command('ZINCRBY', ...). "
    "Ver docs/guia-consultas.md"
)


class RedisPipeline:
    """Pipeline restringido: solo `execute_command(...)` y `execute()`."""

    __slots__ = ("_pipe",)

    def __init__(self, pipe) -> None:
        self._pipe = pipe

    def execute_command(self, *args):
        self._pipe.execute_command(*args)
        return self

    def execute(self):
        return self._pipe.execute()

    def __enter__(self) -> "RedisPipeline":
        return self

    def __exit__(self, *exc) -> None:
        self._pipe.reset()

    def __getattr__(self, name: str):
        raise AttributeError(f"pipeline.{name}: {REDIS_LITERAL_MSG}")


class RedisCommands:
    """Cliente Redis restringido: la regla "lenguaje nativo" aplicada en código.

    Solo expone `execute_command(*args)` y `pipeline(transaction=True)`. Cualquier
    método de conveniencia de redis-py (zincrby, set, get, lrange, ...) falla.
    """

    __slots__ = ("_raw",)

    def __init__(self, raw) -> None:
        self._raw = raw  # uso interno de connections.py; no tocar desde los adaptadores

    def execute_command(self, *args):
        return self._raw.execute_command(*args)

    def pipeline(self, transaction: bool = True) -> RedisPipeline:
        return RedisPipeline(self._raw.pipeline(transaction=transaction))

    def __getattr__(self, name: str):
        raise AttributeError(f"redis.{name}: {REDIS_LITERAL_MSG}")


@dataclass
class Connections:
    mongo_client: MongoClient
    mongo: Database
    redis: RedisCommands
    neo4j: Driver

    @classmethod
    def open(cls, settings: Settings) -> "Connections":
        mongo_client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=3000)
        return cls(
            mongo_client=mongo_client,
            mongo=mongo_client[settings.mongo_db],
            redis=RedisCommands(Redis.from_url(settings.redis_url, decode_responses=True)),
            neo4j=GraphDatabase.driver(
                settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
            ),
        )

    def ping(self) -> dict[str, str]:
        """Estado de cada motor: 'ok' o el mensaje de error."""
        checks = {
            "mongo": lambda: self.mongo_client.admin.command("ping"),
            "redis": lambda: self.redis.execute_command("PING"),
            "neo4j": lambda: self.neo4j.verify_connectivity(),
        }
        result = {}
        for name, check in checks.items():
            try:
                check()
                result[name] = "ok"
            except Exception as exc:  # noqa: BLE001 - queremos reportar cualquier falla
                result[name] = f"error: {exc}"
        return result

    def close(self) -> None:
        self.neo4j.close()
        self.redis._raw.close()
        self.mongo_client.close()
