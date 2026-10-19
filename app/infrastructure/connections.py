"""Creación y cierre de los clientes de cada motor. PROVISTO: no hace falta tocarlo.

Los adaptadores reciben este objeto `Connections` completo y usan el motor que
corresponda. MongoDB es fijo para repositorios; los almacenes derivados son a elección.
Clientes disponibles:
  - MongoDB: `pymongo.database.Database`
  - Redis:   `redis.Redis` (con decode_responses=True: devuelve `str`, no `bytes`)
  - Neo4j:   `neo4j.Driver` (usen `driver.session()` en cada operación)
"""

from dataclasses import dataclass

from neo4j import Driver, GraphDatabase
from pymongo import MongoClient
from pymongo.database import Database
from redis import Redis

from app.config import Settings


@dataclass
class Connections:
    mongo_client: MongoClient
    mongo: Database
    redis: Redis
    neo4j: Driver

    @classmethod
    def open(cls, settings: Settings) -> "Connections":
        mongo_client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=3000)
        return cls(
            mongo_client=mongo_client,
            mongo=mongo_client[settings.mongo_db],
            redis=Redis.from_url(settings.redis_url, decode_responses=True),
            neo4j=GraphDatabase.driver(
                settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
            ),
        )

    def ping(self) -> dict[str, str]:
        """Estado de cada motor: 'ok' o el mensaje de error."""
        checks = {
            "mongo": lambda: self.mongo_client.admin.command("ping"),
            "redis": lambda: self.redis.ping(),
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
        self.redis.close()
        self.mongo_client.close()
