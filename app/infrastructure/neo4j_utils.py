"""Kit de la cátedra para Neo4j: plomería del driver. PROVISTO.

Son TRANSPORTE: la consulta Cypher (con parámetros, nunca f-strings) la escribís vos.
Se abre una transacción administrada (`execute_read` / `execute_write`, con reintentos
ante errores transitorios), se ejecuta y se consumen los resultados.

    cypher_write(connections, "MERGE (s:Socio {id: $id})", id="soc-007")
    filas = cypher_read(connections, "MATCH (l:Libro) RETURN l.id AS id LIMIT $n", n=3)
    fila = cypher_read_one(connections, "MATCH (l:Libro {id: $id}) RETURN l.titulo AS t", id="lib-001")
    cypher_schema(connections, ["CREATE CONSTRAINT libro_id IF NOT EXISTS FOR (l:Libro) REQUIRE l.id IS UNIQUE"])

El primer argumento puede ser el objeto `Connections` completo o `connections.neo4j`.
Como la transacción se reintenta, la escritura debe ser IDEMPOTENTE (usá `MERGE`).
"""

from collections.abc import Sequence
from typing import Any

from neo4j import Driver

from app.infrastructure.connections import Connections
from app.infrastructure.once import already_done, mark_done

Neo4jSource = Connections | Driver


def _driver(source: Neo4jSource) -> Driver:
    return source.neo4j if isinstance(source, Connections) else source


def cypher_write(source: Neo4jSource, query: str, /, **params: Any) -> None:
    """Ejecuta una escritura en una transacción administrada (`execute_write`).

    Ejemplo: `cypher_write(conns, "MERGE (s:Socio {id: $id})", id="soc-007")`.
    """
    with _driver(source).session() as session:
        session.execute_write(lambda tx: tx.run(query, params).consume())


def cypher_read(source: Neo4jSource, query: str, /, **params: Any) -> list[dict[str, Any]]:
    """Ejecuta una lectura (`execute_read`) y devuelve una lista de dicts, uno por fila.

    Las claves son los alias del `RETURN`.
    Ejemplo: `cypher_read(conns, "MATCH (l:Libro) RETURN l.id AS id LIMIT $n", n=3)`.
    """
    with _driver(source).session() as session:
        return session.execute_read(lambda tx: [r.data() for r in tx.run(query, params)])


def cypher_read_one(source: Neo4jSource, query: str, /, **params: Any) -> dict[str, Any] | None:
    """Como `cypher_read` pero devuelve la primera fila, o `None` si no hay ninguna.

    Ejemplo: `cypher_read_one(conns, "MATCH (l:Libro {id: $id}) RETURN l.titulo AS t", id="lib-001")`.
    """
    rows = cypher_read(source, query, **params)
    return rows[0] if rows else None


def cypher_schema(source: Neo4jSource, statements: Sequence[str]) -> None:
    """Ejecuta sentencias de esquema (constraints/índices `IF NOT EXISTS`) UNA vez por driver.

    Es seguro llamarla antes de cada operación: las llamadas siguientes no hacen nada.
    Ejemplo: `cypher_schema(conns, ["CREATE CONSTRAINT libro_id IF NOT EXISTS FOR (l:Libro) REQUIRE l.id IS UNIQUE"])`.
    """
    driver = _driver(source)
    key = ("cypher_schema", tuple(statements))
    if already_done(driver, key):
        return
    with driver.session() as session:
        for statement in statements:
            session.run(statement).consume()
    mark_done(driver, key)
