# Guía de consultas nativas (MongoDB, Redis, Neo4j)

Esta guía muestra **sintaxis** y cómo cada comando de consola se traduce al **driver oficial de Python**. Usa un dominio distinto al del TP (una **biblioteca**: libros, socios, préstamos, autores, géneros) a propósito.

**No dice qué motor conviene para cada responsabilidad del TP** (opción C): esa decisión y su justificación son de ustedes, en `docs/decisions.md`. Los patrones de Redis aparecen como capacidades del motor; el mismo patrón puede resolverse también en otros motores, y la elección hay que justificarla.

## Regla

| Regla | Detalle |
|-------|---------|
| Lenguaje nativo | Documentos de consulta y pipelines (MongoDB), comandos (Redis), Cypher (Neo4j). |
| Solo drivers oficiales | `pymongo`, `redis`, `neo4j`. Sin ORM/ODM/OGM ni query builders. |
| El motor trabaja | Filtrar, ordenar, contar, agregar y recorrer relaciones se hace en el motor. |
| Python | Arma parámetros y mapea resultados. |

Se verifica con `uv run pytest tests/test_no_orm.py` (imports y dependencias prohibidas) y en la defensa oral (evidencia de `explain()` / `PROFILE` en `docs/decisions.md`).

## Índice

1. [MongoDB](#1-mongodb-mongosh-vs-pymongo)
2. [Redis](#2-redis-redis-cli-vs-redis-py)
3. [Neo4j](#3-neo4j-cypher-shell-vs-driver-neo4j)
4. [Esto NO](#4-esto-no)

Conexiones usadas en los ejemplos (en el repo las provee `Connections`):

```python
from pymongo import MongoClient
import redis
from neo4j import GraphDatabase

db = MongoClient("mongodb://localhost:27017")["biblioteca"]
r = redis.Redis(host="localhost", port=6379, decode_responses=True)
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "<password>"))
```

---

## 1. MongoDB: `mongosh` vs `pymongo`

Documento de ejemplo en `libros`:

```json
{
  "_id": "lib-001",
  "titulo": "Rayuela",
  "autor": {"nombre": "Julio Cortázar", "pais": "AR"},
  "generos": ["novela", "clasico"],
  "anio": 1963,
  "ejemplares": 3,
  "activo": true,
  "atributos": {"paginas": 600}
}
```

### 1.1 Buscar con filtros, proyección, orden y límite

Operadores `$gte` / `$lte` / `$in`, campo anidado (`autor.pais`) y atributo con punto (`atributos.paginas`).

```javascript
// mongosh
db.libros.find(
  {
    activo: true,
    anio: { $gte: 1950, $lte: 1990 },
    generos: { $in: ["novela", "cuento"] },
    "autor.pais": "AR",
    "atributos.paginas": { $lte: 400 }
  },
  { titulo: 1, anio: 1 }          // proyección
).sort({ anio: -1 }).limit(10)
```

```python
# pymongo
cursor = (
    db.libros.find(
        {
            "activo": True,
            "anio": {"$gte": 1950, "$lte": 1990},
            "generos": {"$in": ["novela", "cuento"]},
            "autor.pais": "AR",
            "atributos.paginas": {"$lte": 400},
        },
        {"titulo": 1, "anio": 1},   # proyección
    )
    .sort("anio", -1)               # o .sort([("anio", -1), ("titulo", 1)])
    .limit(10)
)
resultados = list(cursor)           # el filtro, el orden y el límite ya los hizo MongoDB
```

Notas:

- Si el filtro se arma dinámicamente (parámetros opcionales), construyan un `dict` y agreguen claves solo cuando el parámetro existe. Sigue siendo un filtro nativo enviado a MongoDB.
- `find_one({"_id": "lib-001"})` devuelve un documento o `None`.

### 1.2 Mapear `_id`

MongoDB guarda la clave primaria en `_id`. Si el modelo de dominio usa `id`, se traduce al escribir y al leer (en el repo ya existen `to_document` y `from_document`).

```python
doc = db.libros.find_one({"_id": "lib-001"})
libro = {"id": doc.pop("_id"), **doc}     # lectura: _id -> id

nuevo = {"_id": libro["id"], **{k: v for k, v in libro.items() if k != "id"}}  # escritura: id -> _id
db.libros.insert_one(nuevo)
```

### 1.3 Actualizar con `$set` / `$inc` y devolver el documento nuevo

```javascript
// mongosh
db.libros.findOneAndUpdate(
  { _id: "lib-001" },
  { $set: { titulo: "Rayuela (ed. 2024)" }, $inc: { ejemplares: -1 } },
  { returnDocument: "after" }
)
```

```python
# pymongo
from pymongo import ReturnDocument

doc = db.libros.find_one_and_update(
    {"_id": "lib-001"},
    {"$set": {"titulo": "Rayuela (ed. 2024)"}, "$inc": {"ejemplares": -1}},
    return_document=ReturnDocument.AFTER,   # sin esto devuelve el documento ANTERIOR
)
# doc es None si no existe el _id
```

Condicionar en el filtro hace la operación atómica (por ejemplo, descontar solo si hay stock):

```python
db.libros.find_one_and_update(
    {"_id": "lib-001", "ejemplares": {"$gt": 0}},
    {"$inc": {"ejemplares": -1}},
    return_document=ReturnDocument.AFTER,
)
```

### 1.4 Baja lógica (soft delete)

No se borra: se marca. Las lecturas filtran por `activo`.

```javascript
// mongosh
db.libros.updateOne({ _id: "lib-001" }, { $set: { activo: false } })
```

```python
# pymongo
res = db.libros.update_one({"_id": "lib-001"}, {"$set": {"activo": False}})
res.matched_count    # 0 si no existía
```

### 1.5 Pipeline de agregación

Los 5 géneros con más préstamos en un año. Con `$lookup` se une a otra colección.

```javascript
// mongosh
db.prestamos.aggregate([
  { $match: { fecha: { $gte: ISODate("2024-01-01"), $lt: ISODate("2025-01-01") } } },
  { $group: { _id: "$libro_id", total: { $sum: 1 } } },
  { $sort: { total: -1 } },
  { $limit: 5 },
  { $lookup: { from: "libros", localField: "_id", foreignField: "_id", as: "libro" } },
  { $unwind: "$libro" },
  { $project: { _id: 0, libro_id: "$_id", titulo: "$libro.titulo", total: 1 } }
])
```

```python
# pymongo
from datetime import datetime

pipeline = [
    {"$match": {"fecha": {"$gte": datetime(2024, 1, 1), "$lt": datetime(2025, 1, 1)}}},
    {"$group": {"_id": "$libro_id", "total": {"$sum": 1}}},
    {"$sort": {"total": -1}},
    {"$limit": 5},
    {"$lookup": {"from": "libros", "localField": "_id", "foreignField": "_id", "as": "libro"}},
    {"$unwind": "$libro"},
    {"$project": {"_id": 0, "libro_id": "$_id", "titulo": "$libro.titulo", "total": 1}},
]
top = list(db.prestamos.aggregate(pipeline))
```

Regla práctica: `$match` primero (y `$sort`/`$limit` cuanto antes) para que el motor trabaje con pocos documentos.

### 1.6 Índices y `explain()`

Un índice compuesto sigue la regla **igualdad, orden, rango**: primero los campos con igualdad, luego el de orden, al final el de rango.

```javascript
// mongosh
db.libros.createIndex({ activo: 1, "autor.pais": 1, anio: -1 })
db.libros.find({ activo: true, "autor.pais": "AR", anio: { $gte: 1950 } })
         .sort({ anio: -1 }).explain("executionStats")
```

```python
# pymongo
db.libros.create_index([("activo", 1), ("autor.pais", 1), ("anio", -1)], name="activo_pais_anio")

plan = (
    db.libros.find({"activo": True, "autor.pais": "AR", "anio": {"$gte": 1950}})
    .sort("anio", -1)
    .explain()                      # devuelve un dict con el plan
)
stats = plan["executionStats"]
print(plan["queryPlanner"]["winningPlan"])
print(stats["totalKeysExamined"], stats["totalDocsExamined"], stats["nReturned"])
```

Qué mirar en la salida:

| Señal | Bueno | Malo |
|-------|-------|------|
| Etapa en `winningPlan` | `IXSCAN` (y luego `FETCH`) | `COLLSCAN` (recorre toda la colección) |
| `totalDocsExamined` vs `nReturned` | Parecidos | Mucho mayor: el índice no es selectivo o no sirve |
| `SORT` en memoria | No aparece (el índice ya ordena) | Etapa `SORT` explícita |

La estructura exacta de `explain()` puede variar según la versión del servidor (el plan puede estar anidado en `inputStage`); busquen el nombre de la etapa dentro de `winningPlan`.

---

## 2. Redis: `redis-cli` vs `redis-py`

Con `decode_responses=True` las respuestas llegan como `str`; sin él llegan como `bytes` (`b"..."`). Elijan una convención y úsenla en todo el proyecto. Además, Redis devuelve los números como texto: `r.get("x")` devuelve `"3"`, no `3`; conviertan con `int()`.

**Convención de nombres de claves:** `aplicacion:entidad:{id}[:subrecurso]`, por ejemplo `biblioteca:libro:lib-001`, `biblioteca:socio:soc-007:ultimos`, `biblioteca:ranking:prestamos`. Ayuda a leer, a borrar por patrón en desarrollo y a evitar colisiones.

### 2.1 Cadenas con vencimiento: `SET ... EX`, `GET`, `DEL`, `TTL`

```text
# redis-cli
SET biblioteca:libro:lib-001 "{\"titulo\":\"Rayuela\"}" EX 60
GET biblioteca:libro:lib-001
TTL biblioteca:libro:lib-001
DEL biblioteca:libro:lib-001
```

```python
# redis-py
import json

clave = "biblioteca:libro:lib-001"
r.set(clave, json.dumps({"titulo": "Rayuela"}), ex=60)   # valor y TTL en UNA operación atómica
valor = r.get(clave)             # str o None si no existe / venció
ttl = r.ttl(clave)               # segundos restantes; -2 no existe, -1 sin vencimiento
r.delete(clave)                  # devuelve cuántas claves borró (0 si no existía)
```

`SET` y luego `EXPIRE` son dos comandos y entre ambos puede fallar algo; `SET ... EX` es una sola operación.

### 2.2 Contador atómico: `INCR`

```text
# redis-cli
INCR biblioteca:libro:lib-001:prestamos
```

```python
# redis-py
total = r.incr("biblioteca:libro:lib-001:prestamos")   # devuelve el valor nuevo (int)
r.incrby("biblioteca:libro:lib-001:prestamos", 5)
```

Es atómico en el servidor: no hay que hacer `GET`, sumar en Python y `SET` (condición de carrera).

### 2.3 Lista acotada: `LPUSH` + `LTRIM` + `LRANGE`

Los últimos 5 libros mirados por un socio, el más reciente primero.

```text
# redis-cli
LPUSH biblioteca:socio:soc-007:ultimos lib-001
LTRIM biblioteca:socio:soc-007:ultimos 0 4
LRANGE biblioteca:socio:soc-007:ultimos 0 4
```

```python
# redis-py
clave = "biblioteca:socio:soc-007:ultimos"
pipe = r.pipeline()              # MULTI/EXEC por defecto: los dos comandos van juntos
pipe.lpush(clave, "lib-001")
pipe.ltrim(clave, 0, 4)          # conserva solo los índices 0..4
pipe.execute()
ultimos = r.lrange(clave, 0, 4)
```

Una lista no evita repetidos: si hace falta "sin repetidos", piensen qué comando adicional lo resuelve (por ejemplo `LREM` antes del `LPUSH`) o qué otra estructura lo da naturalmente.

### 2.4 Ranking: conjunto ordenado (`ZINCRBY` + `ZREVRANGE WITHSCORES`)

Libros más prestados.

```text
# redis-cli
ZINCRBY biblioteca:ranking:prestamos 1 lib-001
ZREVRANGE biblioteca:ranking:prestamos 0 4 WITHSCORES
ZSCORE biblioteca:ranking:prestamos lib-001
```

```python
# redis-py
r.zincrby("biblioteca:ranking:prestamos", 1, "lib-001")      # (nombre, incremento, miembro)
top = r.zrevrange("biblioteca:ranking:prestamos", 0, 4, withscores=True)
# [("lib-001", 12.0), ("lib-007", 9.0), ...] -> ordenado por el motor, puntaje como float
puntaje = r.zscore("biblioteca:ranking:prestamos", "lib-001")  # float o None
```

`ZREVRANGE` está marcado como obsoleto en la documentación de Redis a favor de `ZRANGE ... REV`, pero sigue funcionando; en redis-py 5 también existe `r.zrange(nombre, 0, 4, desc=True, withscores=True)`.

### 2.5 Hash: `HSET` / `HGETALL`

```text
# redis-cli
HSET biblioteca:socio:soc-007 nombre "Ana" plan "premium"
HGETALL biblioteca:socio:soc-007
HINCRBY biblioteca:socio:soc-007 prestamos 1
```

```python
# redis-py
r.hset("biblioteca:socio:soc-007", mapping={"nombre": "Ana", "plan": "premium"})
socio = r.hgetall("biblioteca:socio:soc-007")     # dict[str, str]; vacío si no existe
r.hincrby("biblioteca:socio:soc-007", "prestamos", 1)
```

Todos los valores de un hash son texto: conviertan tipos al leer.

### 2.6 Persistencia

Redis guarda en memoria. Para sobrevivir a un reinicio usa **RDB** (instantáneas periódicas: se puede perder lo escrito después de la última) y/o **AOF** (registro de cada escritura: pierde menos, pesa más). Qué pasa con sus datos tras un reinicio depende de lo que tenga activado su `compose.yaml`; documenten qué esperan perder y si es aceptable.

---

## 3. Neo4j: `cypher-shell` vs driver `neo4j`

Modelo de ejemplo: `(:Socio {id})-[:PRESTO {fecha}]->(:Libro {id, titulo})-[:DE_GENERO]->(:Genero {nombre})`.

Para identificadores y etiquetas con acentos use nombres sin tilde (`PRESTO`) o escápenlos con acentos graves; es más simple evitarlos.

### 3.1 Restricción de unicidad (crea también un índice)

```cypher
// cypher-shell
CREATE CONSTRAINT socio_id IF NOT EXISTS FOR (s:Socio) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT libro_id IF NOT EXISTS FOR (l:Libro) REQUIRE l.id IS UNIQUE;
```

```python
# driver neo4j
with driver.session() as session:
    session.run("CREATE CONSTRAINT socio_id IF NOT EXISTS FOR (s:Socio) REQUIRE s.id IS UNIQUE")
    session.run("CREATE CONSTRAINT libro_id IF NOT EXISTS FOR (l:Libro) REQUIRE l.id IS UNIQUE")
```

Sin la restricción (o un índice), `MERGE`/`MATCH` por `id` recorre todos los nodos de la etiqueta.

### 3.2 `MERGE` idempotente con parámetros

Registrar que un socio prestó un libro. Ejecutarlo dos veces no duplica nodos ni relaciones.

```cypher
// cypher-shell (los parámetros se declaran con :param)
:param socio_id => 'soc-007';
:param libro_id => 'lib-001';
MERGE (s:Socio {id: $socio_id})
MERGE (l:Libro {id: $libro_id})
MERGE (s)-[p:PRESTO]->(l)
ON CREATE SET p.fecha = datetime()
RETURN s.id, l.id;
```

```python
# driver neo4j: función de transacción + parámetros
def registrar_prestamo(tx, socio_id: str, libro_id: str) -> None:
    tx.run(
        """
        MERGE (s:Socio {id: $socio_id})
        MERGE (l:Libro {id: $libro_id})
        MERGE (s)-[p:PRESTO]->(l)
        ON CREATE SET p.fecha = datetime()
        """,
        socio_id=socio_id,
        libro_id=libro_id,
    )

with driver.session() as session:
    session.execute_write(registrar_prestamo, "soc-007", "lib-001")
```

- `execute_write` / `execute_read` reintentan solos ante errores transitorios, por eso la función de transacción debe ser **idempotente** (otra razón para usar `MERGE`).
- `MERGE` sobre el patrón completo `(s)-[:PRESTO]->(l)` evita relaciones duplicadas.
- En versiones anteriores del driver se llamaban `write_transaction` / `read_transaction`; en 5.x usen `execute_write` / `execute_read`.

### 3.3 Recorrido de 2 saltos: "quienes leyeron lo mismo también leyeron..."

Libros que leyeron otros socios que comparten al menos un libro con el socio dado, excluyendo los que ya leyó, ordenados por cantidad de socios.

```cypher
// cypher-shell
MATCH (s:Socio {id: $socio_id})-[:PRESTO]->(:Libro)<-[:PRESTO]-(otro:Socio)-[:PRESTO]->(l:Libro)
WHERE otro <> s
  AND NOT (s)-[:PRESTO]->(l)
RETURN l.id AS libro_id, l.titulo AS titulo, count(DISTINCT otro) AS lectores
ORDER BY lectores DESC, titulo ASC
LIMIT $limite;
```

```python
# driver neo4j
CONSULTA = """
MATCH (s:Socio {id: $socio_id})-[:PRESTO]->(:Libro)<-[:PRESTO]-(otro:Socio)-[:PRESTO]->(l:Libro)
WHERE otro <> s
  AND NOT (s)-[:PRESTO]->(l)
RETURN l.id AS libro_id, l.titulo AS titulo, count(DISTINCT otro) AS lectores
ORDER BY lectores DESC, titulo ASC
LIMIT $limite
"""

def sugerencias(tx, socio_id: str, limite: int) -> list[dict]:
    resultado = tx.run(CONSULTA, socio_id=socio_id, limite=limite)
    return [
        {"libro_id": rec["libro_id"], "titulo": rec["titulo"], "lectores": rec["lectores"]}
        for rec in resultado      # consumir DENTRO de la transacción
    ]

with driver.session() as session:
    filas = session.execute_read(sugerencias, "soc-007", 5)
```

El recorrido, la exclusión, el conteo y el orden los hace Neo4j. Python solo convierte filas en diccionarios.

### 3.4 Consumir resultados

```python
resultado = tx.run("MATCH (l:Libro) RETURN l.id AS id, l.titulo AS titulo LIMIT 3")

for rec in resultado:                  # iteración: un Record por fila
    rec["id"], rec["titulo"]           # acceso por alias del RETURN

filas = resultado.data()               # list[dict]: {"id": ..., "titulo": ...}
una = resultado.single()               # exactamente una fila (o None / aviso si hay 0 o más de 1)
```

El resultado es un flujo ligado a la transacción: consúmanlo antes de que la función de transacción termine. Un nodo completo (`RETURN l`) llega como objeto `Node`; para propiedades usen `dict(rec["l"])` o, mejor, devuelvan solo lo que necesitan (`RETURN l.id AS id`).

### 3.5 `PROFILE` / `EXPLAIN`

```cypher
// cypher-shell
PROFILE
MATCH (s:Socio {id: 'soc-007'})-[:PRESTO]->(:Libro)<-[:PRESTO]-(otro:Socio)-[:PRESTO]->(l:Libro)
WHERE otro <> s AND NOT (s)-[:PRESTO]->(l)
RETURN l.id, count(DISTINCT otro) AS lectores
ORDER BY lectores DESC LIMIT 5;
```

```python
# driver neo4j: PROFILE ejecuta la consulta; EXPLAIN solo planifica
with driver.session() as session:
    resultado = session.run("PROFILE MATCH (s:Socio {id: $id})-[:PRESTO]->(l:Libro) RETURN l.id", id="soc-007")
    resumen = resultado.consume()              # consumir el resultado devuelve el resumen
    plan = resumen.profile                     # dict con operador, db_hits, rows, children
```

Más simple: pegar `PROFILE` en `cypher-shell` o Neo4j Browser y copiar el resumen.

| Señal | Bueno | Malo |
|-------|-------|------|
| Operador de acceso al nodo inicial | `NodeUniqueIndexSeek` / `NodeIndexSeek` | `AllNodesScan` / `NodeByLabelScan` sobre muchos nodos |
| `db hits` | Pocos y proporcionales al resultado | Crecen con el tamaño total del grafo |
| `rows` por operador | Se reducen rápido | Explosión de filas intermedias |

`EXPLAIN` muestra el plan sin ejecutarlo (útil con consultas que escriben). `PROFILE` ejecuta y agrega `db hits` y filas reales.

---

## 4. Esto NO

Cada caso tiene el anti-patrón y la alternativa correcta.

### 4.a Traer todo y filtrar en Python

```python
# MAL: transfiere TODA la colección y filtra en la aplicación
libros = list(db.libros.find())
argentinos = [l for l in libros if l["autor"]["pais"] == "AR" and l["anio"] >= 1950]
```

```python
# BIEN: el filtro viaja a MongoDB (y puede usar un índice)
argentinos = list(db.libros.find({"autor.pais": "AR", "anio": {"$gte": 1950}}))
```

### 4.b Ordenar con `sorted()` todos los contadores

```python
# MAL: lee todos los contadores y ordena en Python
claves = r.keys("biblioteca:libro:*:prestamos")
conteos = {k: int(r.get(k)) for k in claves}
top = sorted(conteos.items(), key=lambda kv: kv[1], reverse=True)[:5]
```

```python
# BIEN: la estructura ordenada la mantiene el motor; se pide solo el top 5
top = r.zrevrange("biblioteca:ranking:prestamos", 0, 4, withscores=True)
```

(`KEYS` además recorre todo el keyspace y bloquea el servidor.)

### 4.c Cypher armado con f-strings

```python
# MAL: inyección de Cypher y el servidor no puede reutilizar el plan
tx.run(f"MATCH (s:Socio {{id: '{socio_id}'}})-[:PRESTO]->(l:Libro) RETURN l.id")
```

```python
# BIEN: parámetro; el texto de la consulta es constante y el plan se cachea
tx.run("MATCH (s:Socio {id: $socio_id})-[:PRESTO]->(l:Libro) RETURN l.id", socio_id=socio_id)
```

Un `socio_id` como `' }) DETACH DELETE s //` ejecutaría código en la versión con f-string. Los **parámetros** valen para valores; las etiquetas y tipos de relación no se parametrizan (si deben variar, validen contra una lista fija).

### 4.d Un bucle de consultas por nodo (N+1)

```python
# MAL: 1 consulta para los libros del socio + 1 por cada libro
libros = tx.run("MATCH (:Socio {id: $id})-[:PRESTO]->(l) RETURN l.id AS id", id=socio_id).data()
lectores = {}
for libro in libros:
    lectores[libro["id"]] = tx.run(
        "MATCH (o:Socio)-[:PRESTO]->(:Libro {id: $lid}) RETURN count(o) AS n", lid=libro["id"]
    ).single()["n"]
```

```python
# BIEN: un solo recorrido que devuelve todo agrupado
filas = tx.run(
    """
    MATCH (:Socio {id: $id})-[:PRESTO]->(l:Libro)<-[:PRESTO]-(o:Socio)
    RETURN l.id AS id, count(o) AS n
    """,
    id=socio_id,
).data()
```

Lo mismo vale en MongoDB: un `find` por documento dentro de un bucle se reemplaza por `$in` o por `$lookup`.

### 4.e Una clase modelo de ODM

```python
# MAL: ODM (mongoengine / beanie / odmantic): oculta la consulta y no está permitido
class Libro(Document):
    titulo = StringField(required=True)
    anio = IntField()

Libro.objects(anio__gte=1950).order_by("-anio")
```

```python
# BIEN: pymongo con la consulta a la vista; el mapeo a modelo de dominio lo hace el adaptador
docs = db.libros.find({"anio": {"$gte": 1950}}).sort("anio", -1)
libros = [from_document(Libro, d) for d in docs]     # Libro es un modelo de dominio (pydantic), sin lógica de consulta
```

`tests/test_no_orm.py` falla si se importa o declara alguna de estas librerías.
