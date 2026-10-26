"""Verifica que el proyecto use solo los drivers oficiales (sin ORM/ODM/OGM).

Regla (ENUNCIADO.md, secciones 6 y 7.4): las consultas se escriben en el lenguaje
nativo de cada motor (MongoDB, Redis, Neo4j) mediante pymongo, redis-py y neo4j.
En Redis, además, los comandos van LITERALES: `execute_command("ZINCRBY", ...)`, no
`zincrby(...)`. `Connections.redis` lo hace cumplir (ver los tests al final).
Guía con ejemplos: docs/guia-consultas.md.

Límite de este test: NO intenta detectar "filtrar/ordenar/agregar en Python"
(eso no se puede decidir estáticamente de forma confiable). Ese punto se controla
en la defensa oral y con la evidencia de `explain()` / `PROFILE` pedida en
docs/decisions.md.

Se ejecuta con: uv run pytest tests/test_no_orm.py
"""

import ast
import re
import tomllib
from pathlib import Path

import pytest

from app.infrastructure.connections import RedisCommands

ROOT = Path(__file__).resolve().parent.parent

# Módulos de primer nivel prohibidos: ORM / ODM / OGM / constructores de consultas.
# Importar cualquiera de ellos implica que la consulta ya no está escrita en el
# lenguaje nativo del motor.
FORBIDDEN_MODULES = frozenset(
    {
        "mongoengine",
        "beanie",
        "odmantic",
        "motor_odm",
        "redis_om",
        "neomodel",
        "py2neo",
        "sqlalchemy",
        "sqlmodel",
        "peewee",
        "pony",
        "tortoise",
        "umongo",
    }
)

# Nombres de distribución (PyPI) prohibidos en pyproject.toml, ya normalizados.
FORBIDDEN_DISTRIBUTIONS = frozenset(
    {
        "mongoengine",
        "beanie",
        "odmantic",
        "motor-odm",
        "redis-om",
        "neomodel",
        "py2neo",
        "sqlalchemy",
        "sqlmodel",
        "peewee",
        "pony",
        "tortoise-orm",
        "tortoise",
        "umongo",
    }
)

SOURCE_DIRS = ("app", "scripts")


def _normalize(name: str) -> str:
    """Normaliza un nombre de distribución (PEP 503): minúsculas y `-` para `_`/`.`."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _requirement_name(requirement: str) -> str:
    """Extrae el nombre de una línea PEP 508 (`redis-om[extra]>=1; python_version...`)."""
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", requirement)
    return _normalize(match.group(1)) if match else ""


def _python_files() -> list[Path]:
    files: list[Path] = []
    for directory in SOURCE_DIRS:
        files.extend(sorted((ROOT / directory).rglob("*.py")))
    return files


def _imports_in(path: Path) -> list[tuple[int, str]]:
    """Devuelve (línea, módulo de primer nivel) por cada import del archivo."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name.split(".")[0]) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append((node.lineno, node.module.split(".")[0]))
    return found


def test_no_orm_imports_in_source():
    assert _python_files(), "No se encontraron archivos .py en app/ ni scripts/."
    violations = [
        f"{path.relative_to(ROOT)}:{lineno} importa '{module}'"
        for path in _python_files()
        for lineno, module in _imports_in(path)
        if module.lower() in FORBIDDEN_MODULES
    ]
    assert not violations, (
        "No se admiten ORM/ODM/OGM ni constructores de consultas. Las consultas deben "
        "escribirse en el lenguaje nativo de cada motor con el driver oficial "
        "(pymongo, redis-py, neo4j). Ver docs/guia-consultas.md y ENUNCIADO.md (7.4).\n"
        "Imports prohibidos encontrados:\n  " + "\n  ".join(violations)
    )


def test_no_orm_dependencies_in_pyproject():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    declared: list[str] = list(data.get("project", {}).get("dependencies", []))
    for group in data.get("project", {}).get("optional-dependencies", {}).values():
        declared.extend(group)
    for group in data.get("dependency-groups", {}).values():
        # Los grupos pueden incluir tablas ({include-group = ...}); solo contamos strings.
        declared.extend(item for item in group if isinstance(item, str))

    violations = [
        requirement
        for requirement in declared
        if _requirement_name(requirement) in FORBIDDEN_DISTRIBUTIONS
    ]
    assert not violations, (
        "pyproject.toml declara dependencias prohibidas (ORM/ODM/OGM o query builders). "
        "Solo se admiten los drivers oficiales: pymongo, redis, neo4j. "
        "Ver docs/guia-consultas.md y ENUNCIADO.md (7.4).\n"
        "Dependencias prohibidas: " + ", ".join(violations)
    )


class _StubRedis:
    """Cliente redis-py falso: registra lo que recibe, sin conectarse a nada."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def execute_command(self, *args):
        self.calls.append(args)
        return "OK"

    def pipeline(self, transaction=True):
        return _StubPipeline(self)


class _StubPipeline:
    def __init__(self, parent: _StubRedis) -> None:
        self.parent = parent
        self.queued: list[tuple] = []

    def execute_command(self, *args):
        self.queued.append(args)

    def execute(self):
        self.parent.calls.extend(self.queued)
        return ["OK"] * len(self.queued)

    def reset(self) -> None:
        self.queued.clear()


@pytest.mark.parametrize("method", ["zincrby", "set", "get", "lrange", "zrange", "flushdb"])
def test_redis_rejects_convenience_methods(method):
    redis = RedisCommands(_StubRedis())
    with pytest.raises(AttributeError, match="execute_command"):
        getattr(redis, method)


def test_redis_allows_execute_command_and_pipeline():
    stub = _StubRedis()
    redis = RedisCommands(stub)

    assert redis.execute_command("ZINCRBY", "nexus:views", 1, "p1") == "OK"

    pipe = redis.pipeline(transaction=True)
    pipe.execute_command("LPUSH", "k", "a")
    pipe.execute_command("LTRIM", "k", 0, 4)
    assert pipe.execute() == ["OK", "OK"]

    assert stub.calls == [
        ("ZINCRBY", "nexus:views", 1, "p1"),
        ("LPUSH", "k", "a"),
        ("LTRIM", "k", 0, 4),
    ]


def test_redis_pipeline_rejects_convenience_methods():
    pipe = RedisCommands(_StubRedis()).pipeline()
    for method in ("zincrby", "lpush", "ltrim", "set"):
        with pytest.raises(AttributeError, match="execute_command"):
            getattr(pipe, method)


def test_raw_redis_client_only_touched_in_connections():
    """Nadie fuera de connections.py puede saltarse el cliente restringido (`._raw`)."""
    allowed = ROOT / "app" / "infrastructure" / "connections.py"
    violations = [
        f"{path.relative_to(ROOT)}:{node.lineno}"
        for path in _python_files()
        if path != allowed
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Attribute) and node.attr == "_raw"
    ]
    assert not violations, (
        "Usen connections.redis.execute_command('COMANDO', ...) (ver docs/guia-consultas.md). "
        "No accedan al cliente interno: " + ", ".join(violations)
    )


def test_kit_is_transport_not_a_query_builder():
    """El kit de la cátedra no expone métodos de conveniencia de redis-py ni constructores de consultas."""
    from app.infrastructure import mongo_utils, neo4j_utils, redis_utils

    redis_py_convenience = {"get", "set", "zincrby", "zrange", "zscore", "lrange", "lpush", "ltrim", "hset", "incr", "delete"}
    for module in (mongo_utils, neo4j_utils, redis_utils):
        public = {name.lower() for name in vars(module) if not name.startswith("_")}
        assert not public & redis_py_convenience, f"{module.__name__} expone {public & redis_py_convenience}"
        assert not any("builder" in name or name.startswith("zincr") for name in public)
    # Las funciones del kit reciben la consulta/comando ya escrito: no la construyen.
    assert redis_utils.redis_cmd.__code__.co_varnames[:2] == ("source", "args")
    assert neo4j_utils.cypher_write.__code__.co_varnames[:2] == ("source", "query")
