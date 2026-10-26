"""Kit de la cátedra (`app/infrastructure/*_utils.py`) con drivers falsos: sin Docker."""


from types import SimpleNamespace

import pytest
from pydantic import BaseModel
from pymongo import IndexModel

from app.infrastructure.connections import Connections, RedisCommands
from app.infrastructure.mongo_utils import ensure_indexes, from_document, from_documents, to_document
from app.infrastructure.neo4j_utils import cypher_read, cypher_read_one, cypher_schema, cypher_write
from app.infrastructure.redis_utils import as_int, pairs, redis_cmd, redis_pipeline, redis_tx


# ---------- Redis ----------
class StubRedis:
    """Cliente redis-py falso: registra los comandos y cómo se enviaron."""

    def __init__(self, replies=None):
        self.calls: list[tuple] = []
        self.pipelines: list[bool] = []
        self.replies = replies or {}

    def execute_command(self, *args):
        self.calls.append(args)
        return self.replies.get(args[0], "OK")

    def pipeline(self, transaction=True):
        self.pipelines.append(transaction)
        return StubPipeline(self)


class StubPipeline:
    def __init__(self, parent):
        self.parent, self.queued, self.was_reset = parent, [], False

    def execute_command(self, *args):
        self.queued.append(args)

    def execute(self):
        self.parent.calls.extend(self.queued)
        return [f"r{i}" for i, _ in enumerate(self.queued)]

    def reset(self):
        self.was_reset = True


def test_pairs_accepts_nested_format_of_redis_py_8():
    assert pairs([["p1", 12.0], ["p2", 9.0]]) == [("p1", 12.0), ("p2", 9.0)]


def test_pairs_accepts_flat_format_of_older_redis_py():
    assert pairs(["p1", "12", "p2", "9"]) == [("p1", 12.0), ("p2", 9.0)]


def test_pairs_empty():
    assert pairs([]) == []


@pytest.mark.parametrize("reply, expected", [(None, 0), ("3", 3), (3, 3), (3.0, 3), ("3.0", 3)])
def test_as_int(reply, expected):
    assert as_int(reply) == expected


def test_as_int_custom_default():
    assert as_int(None, default=-1) == -1


def test_redis_cmd_sends_one_literal_command_through_restricted_client():
    stub = StubRedis({"ZSCORE": 4.0})
    assert redis_cmd(RedisCommands(stub), "ZSCORE", "k", "m") == 4.0
    assert stub.calls == [("ZSCORE", "k", "m")]


def test_redis_cmd_accepts_connections_object():
    stub = StubRedis()
    conns = Connections(mongo_client=None, mongo=None, redis=RedisCommands(stub), neo4j=None)
    redis_cmd(conns, "DEL", "k")
    assert stub.calls == [("DEL", "k")]


def test_redis_tx_runs_multi_exec_in_order_and_returns_replies():
    stub = StubRedis()
    replies = redis_tx(RedisCommands(stub), [["LPUSH", "k", "a"], ["LTRIM", "k", 0, 4]])
    assert stub.pipelines == [True]  # transaction=True -> MULTI/EXEC
    assert stub.calls == [("LPUSH", "k", "a"), ("LTRIM", "k", 0, 4)]
    assert replies == ["r0", "r1"]


def test_redis_pipeline_is_not_transactional():
    stub = StubRedis()
    redis_pipeline(RedisCommands(stub), [["GET", "a"], ["GET", "b"]])
    assert stub.pipelines == [False]
    assert stub.calls == [("GET", "a"), ("GET", "b")]


# ---------- Neo4j ----------
class FakeRecord:
    def __init__(self, data):
        self._data = data

    def data(self):
        return self._data


class FakeResult:
    def __init__(self, rows):
        self.rows, self.consumed = rows, False

    def __iter__(self):
        return iter(FakeRecord(r) for r in self.rows)

    def consume(self):
        self.consumed = True


class FakeTx:
    def __init__(self, log, rows):
        self.log, self.rows = log, rows

    def run(self, query, parameters=None, **kwargs):  # misma firma que neo4j.Transaction.run
        params = {**(parameters or {}), **kwargs}
        self.log.append(("tx.run", query, params))
        result = FakeResult(self.rows)
        self.log.append(result)
        return result


class FakeSession:
    def __init__(self, log, rows):
        self.log, self.rows = log, rows

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.log.append("session.closed")

    def execute_write(self, fn):
        self.log.append("execute_write")
        return fn(FakeTx(self.log, self.rows))

    def execute_read(self, fn):
        self.log.append("execute_read")
        return fn(FakeTx(self.log, self.rows))

    def run(self, query, **params):  # auto-commit: lo usa solo cypher_schema
        self.log.append(("session.run", query, params))
        return FakeResult([])


class FakeDriver:
    def __init__(self, rows=()):
        self.log, self.rows = [], list(rows)

    def session(self):
        return FakeSession(self.log, self.rows)


def test_cypher_write_uses_managed_write_transaction_and_consumes():
    driver = FakeDriver()
    assert cypher_write(driver, "MERGE (n:X {id: $id})", id="a") is None
    assert driver.log[0] == "execute_write"
    assert driver.log[1] == ("tx.run", "MERGE (n:X {id: $id})", {"id": "a"})
    assert driver.log[2].consumed is True
    assert driver.log[-1] == "session.closed"


def test_cypher_read_uses_managed_read_transaction_and_returns_dicts():
    driver = FakeDriver(rows=[{"id": "a"}, {"id": "b"}])
    assert cypher_read(driver, "MATCH (n) RETURN n.id AS id LIMIT $n", n=2) == [{"id": "a"}, {"id": "b"}]
    assert driver.log[0] == "execute_read"
    assert driver.log[1][2] == {"n": 2}


def test_cypher_read_one_returns_first_row_or_none():
    assert cypher_read_one(FakeDriver(rows=[{"t": 1}, {"t": 2}]), "Q") == {"t": 1}
    assert cypher_read_one(FakeDriver(rows=[]), "Q") is None


def test_cypher_param_names_do_not_collide_with_helper_arguments():
    driver = FakeDriver()
    cypher_write(driver, "Q", query="x", source="y")
    assert driver.log[1][2] == {"query": "x", "source": "y"}


def test_cypher_accepts_connections_object():
    driver = FakeDriver(rows=[{"a": 1}])
    conns = Connections(mongo_client=None, mongo=None, redis=None, neo4j=driver)
    assert cypher_read(conns, "Q") == [{"a": 1}]


def test_cypher_schema_runs_once_per_driver():
    driver = FakeDriver()
    statements = ["CREATE CONSTRAINT a IF NOT EXISTS ...", "CREATE CONSTRAINT b IF NOT EXISTS ..."]
    cypher_schema(driver, statements)
    cypher_schema(driver, statements)
    runs = [e for e in driver.log if isinstance(e, tuple) and e[0] == "session.run"]
    assert [r[1] for r in runs] == statements


def test_cypher_schema_is_not_marked_done_if_it_fails():
    driver = FakeDriver()
    original = FakeSession.run
    FakeSession.run = lambda self, q, **p: (_ for _ in ()).throw(RuntimeError("down"))
    try:
        with pytest.raises(RuntimeError):
            cypher_schema(driver, ["S"])
    finally:
        FakeSession.run = original
    cypher_schema(driver, ["S"])  # reintenta y ahora sí corre
    assert ("session.run", "S", {}) in driver.log


# ---------- MongoDB ----------
class Item(BaseModel):
    id: str
    name: str


class FakeClient:
    pass


class FakeCollection:
    def __init__(self, client, full_name="db.items"):
        self.database = SimpleNamespace(client=client)
        self.full_name = full_name
        self.created: list[list] = []

    def create_indexes(self, indexes):
        self.created.append(indexes)


def test_mongo_document_roundtrip_and_from_documents():
    doc = to_document(Item(id="a", name="A"))
    assert doc == {"name": "A", "_id": "a"}
    assert from_document(Item, doc) == Item(id="a", name="A")
    cursor = iter([{"_id": "a", "name": "A"}, {"_id": "b", "name": "B"}])  # un cursor es iterable
    assert from_documents(Item, cursor) == [Item(id="a", name="A"), Item(id="b", name="B")]
    assert from_documents(Item, []) == []


def test_ensure_indexes_creates_once_per_client_and_collection():
    client = FakeClient()
    col = FakeCollection(client)
    indexes = [IndexModel([("price", 1)], name="price")]
    ensure_indexes(col, indexes)
    ensure_indexes(col, indexes)
    ensure_indexes(FakeCollection(client), indexes)  # otra instancia de la misma colección
    assert len(col.created) == 1
    other_client_col = FakeCollection(FakeClient())
    ensure_indexes(other_client_col, indexes)
    assert len(other_client_col.created) == 1
