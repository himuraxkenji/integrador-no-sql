"""Kit de la cátedra para Redis: plomería del cliente restringido. PROVISTO.

Son TRANSPORTE: enviás comandos LITERALES (como en `redis-cli`) y te devuelven la respuesta
cruda. No hay métodos de conveniencia (`zincrby`, `set`, ...) ni armado de comandos.

    redis_cmd(connections, "SET", "biblioteca:libro:lib-001", "...", "EX", 60)
    redis_tx(connections, [["LPUSH", k, "lib-001"], ["LTRIM", k, 0, 4]])   # MULTI/EXEC
    pairs(redis_cmd(connections, "ZRANGE", k, 0, 4, "REV", "WITHSCORES"))
    as_int(redis_cmd(connections, "ZSCORE", k, "lib-001"))                 # nil -> 0

El primer argumento puede ser el objeto `Connections` completo o `connections.redis`.
"""

from collections.abc import Sequence
from typing import Any

from app.infrastructure.connections import Connections, RedisCommands

RedisSource = Connections | RedisCommands
Command = Sequence[Any]  # ["ZINCRBY", clave, 1, miembro]


def _client(source: RedisSource) -> RedisCommands:
    return source.redis if isinstance(source, Connections) else source


def redis_cmd(source: RedisSource, *args: Any) -> Any:
    """Un comando literal: `redis_cmd(conns, "GET", "biblioteca:libro:lib-001")`."""
    return _client(source).execute_command(*args)


def redis_tx(source: RedisSource, commands: Sequence[Command]) -> list[Any]:
    """Varios comandos en una transacción MULTI/EXEC: se aplican todos o ninguno.

    Devuelve una respuesta por comando, en orden:
    `redis_tx(conns, [["LPUSH", k, "lib-001"], ["LTRIM", k, 0, 4]])` -> `[1, True]`.
    """
    return _run(source, commands, transaction=True)


def redis_pipeline(source: RedisSource, commands: Sequence[Command]) -> list[Any]:
    """Como `redis_tx` pero SIN MULTI/EXEC: ahorra viajes de red, no da atomicidad."""
    return _run(source, commands, transaction=False)


def _run(source: RedisSource, commands: Sequence[Command], transaction: bool) -> list[Any]:
    with _client(source).pipeline(transaction=transaction) as pipe:
        for command in commands:
            pipe.execute_command(*command)
        return pipe.execute()


def pairs(reply: Sequence[Any]) -> list[tuple[str, float]]:
    """Respuesta de `... WITHSCORES` -> `[(miembro, puntaje)]`, venga plana o en pares.

    redis-py 8.x devuelve `[[m, score], ...]`; versiones anteriores `[m, score, m, score]`.
    Ejemplo: `pairs(redis_cmd(conns, "ZRANGE", k, 0, 4, "REV", "WITHSCORES"))`.
    """
    if reply and isinstance(reply[0], (list, tuple)):
        return [(member, float(score)) for member, score in reply]
    return [(member, float(score)) for member, score in zip(reply[0::2], reply[1::2])]


def as_int(reply: Any, default: int = 0) -> int:
    """Respuesta -> `int`; `nil` (None) pasa a `default`. Acepta `"3"`, `3`, `3.0`.

    Ejemplo: `as_int(redis_cmd(conns, "ZSCORE", k, "lib-001"))` -> 0 si el miembro no existe.
    """
    if reply is None:
        return default
    try:
        return int(reply)
    except ValueError:  # "3.0" (texto con decimales)
        return int(float(reply))
