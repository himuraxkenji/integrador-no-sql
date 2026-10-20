# Guía de consultas nativas (MongoDB, Redis, Neo4j)

Esta guía muestra **sintaxis** y cómo cada comando de consola se traduce al **driver oficial de Python**. Usa un dominio distinto al del TP (una **biblioteca**: libros, socios, préstamos, autores, géneros) a propósito.

**No dice qué motor conviene para cada responsabilidad del TP** (opción C): esa decisión y su justificación son de ustedes, en `docs/decisions.md`. Los patrones de Redis aparecen como capacidades del motor; el mismo patrón puede resolverse también en otros motores, y la elección hay que justificarla.

## Regla

| Regla | Detalle |
|-------|---------|
| Lenguaje nativo | Documentos de consulta y pipelines (MongoDB), comandos literales con `execute_command` (Redis), Cypher (Neo4j). |
| Solo drivers oficiales | `pymongo`, `redis`, `neo4j`. Sin ORM/ODM/OGM ni query builders. |
| El motor trabaja | Filtrar, ordenar, contar, agregar y recorrer relaciones se hace en el motor. |
| Python | Arma parámetros y mapea resultados. |

**Por qué Redis es literal y MongoDB no:** el MQL de `pymongo` (`find`, `aggregate`...) ya es el mismo documento de consulta que en `mongosh`; en cambio los métodos de conveniencia de `redis-py` (`zincrby`, `lrange`...) ocultan el comando. Por eso en Redis se envía el comando tal cual con `execute_command("ZINCRBY", ...)`, igual que en `redis-cli`. `Connections.redis` lo exige: solo expone `execute_command` y `pipeline`; cualquier otro método lanza `AttributeError`.

Se verifica con `uv run pytest tests/test_no_orm.py` (imports, dependencias prohibidas y cliente Redis restringido) y en la defensa oral (evidencia de `explain()` / `PROFILE` en `docs/decisions.md`).

## Índice

1. [MongoDB](#1-mongodb-mongosh-vs-pymongo)
2. [Redis](#2-redis-redis-cli-vs-execute_command)
3. [Neo4j](#3-neo4j-cypher-shell-vs-driver-neo4j)
4. [Esto NO](#4-esto-no)

Conexiones usadas en los ejemplos (en el repo las provee `Connections`):

```python
from pymongo import MongoClient
import redis
from neo4j import GraphDatabase

db = MongoClient("mongodb://localhost:27017")["biblioteca"]
r = redis.Redis(host="localhost", port=6379, decode_responses=True)  # en el repo: connections.redis (solo execute_command / pipeline)
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

## 2. Redis: `redis-cli` vs `execute_command`

En Python **cada comando se envía literal**: `r.execute_command("COMANDO", arg1, arg2, ...)`, igual que lo escribirían en `redis-cli`. No se usan los métodos de conveniencia de `redis-py` (`r.set`, `r.get`, `r.zincrby`, `r.lrange`...). En el repo `connections.redis` solo acepta `execute_command` y `pipeline`; lo demás lanza `AttributeError`.

Con `decode_responses=True` las respuestas llegan como `str`; sin él llegan como `bytes` (`b"..."`). Además, con `execute_command` **la conversión de tipos es la que hace `redis-py` por comando** (verificado con redis-py 8.1.0, la versión de `uv.lock`, contra Redis 7): `GET` devuelve `str` (`"3"`, no `3`; conviertan con `int()`), `INCR`/`DEL`/`LPUSH` devuelven `int`, `SET` devuelve `True`, y los puntajes de `ZINCRBY`/`ZSCORE` llegan como `float` (`1.0`). No lo asuman: imprímanlo una vez (`print(repr(...))`) con su versión.

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
# redis-py: execute_command
import json

clave = "biblioteca:libro:lib-001"
r.execute_command("SET", clave, json.dumps({"titulo": "Rayuela"}), "EX", 60)  # True; valor y TTL en UNA operación atómica
valor = r.execute_command("GET", clave)      # str, o None si no existe / venció
ttl = r.execute_command("TTL", clave)        # int: segundos restantes; -2 no existe, -1 sin vencimiento
borradas = r.execute_command("DEL", clave)   # int: cuántas claves borró (0 si no existía)
```

`SET` y luego `EXPIRE` son dos comandos y entre ambos puede fallar algo; `SET ... EX` es una sola operación.

### 2.2 Contador atómico: `INCR`

```text
# redis-cli
INCR biblioteca:libro:lib-001:prestamos
INCRBY biblioteca:libro:lib-001:prestamos 5
```

```python
# redis-py: execute_command
total = r.execute_command("INCR", "biblioteca:libro:lib-001:prestamos")   # int: el valor nuevo
r.execute_command("INCRBY", "biblioteca:libro:lib-001:prestamos", 5)
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
# redis-py: execute_command
clave = "biblioteca:socio:soc-007:ultimos"
r.execute_command("LPUSH", clave, "lib-001")     # int: largo de la lista
r.execute_command("LTRIM", clave, 0, 4)          # True; conserva solo los índices 0..4
ultimos = r.execute_command("LRANGE", clave, 0, 4)   # list[str]; [] si la clave no existe
```

Estos dos comandos de escritura, enviados por separado, no son atómicos: ver 2.7 (pipeline `MULTI`/`EXEC`).

Una lista no evita repetidos: si hace falta "sin repetidos", piensen qué comando adicional lo resuelve (por ejemplo `LREM` antes del `LPUSH`) o qué otra estructura lo da naturalmente.

### 2.4 Ranking: conjunto ordenado (`ZINCRBY` + `ZRANGE ... REV WITHSCORES`)

Libros más prestados.

```text
# redis-cli
ZINCRBY biblioteca:ranking:prestamos 1 lib-001
ZRANGE biblioteca:ranking:prestamos 0 4 REV WITHSCORES
ZSCORE biblioteca:ranking:prestamos lib-001
```

```python
# redis-py: execute_command
r.execute_command("ZINCRBY", "biblioteca:ranking:prestamos", 1, "lib-001")     # (clave, incremento, miembro) -> float: puntaje nuevo
top = r.execute_command("ZRANGE", "biblioteca:ranking:prestamos", 0, 4, "REV", "WITHSCORES")
puntaje = r.execute_command("ZSCORE", "biblioteca:ranking:prestamos", "lib-001")  # float, o None si el miembro no existe
```

Forma de `top` (ordenado por el motor): con **redis-py 8.1.0** (`uv.lock`) llega como lista de pares con el puntaje `float`: `[["lib-001", 12.0], ["lib-007", 9.0]]`. Con versiones anteriores de `redis-py` puede llegar como lista **plana** `["lib-001", "12", "lib-007", "9"]`, porque `execute_command` no le pasa a la conversión la opción `WITHSCORES`. Para no depender de la versión:

```python
def pares(respuesta):
    """Normaliza ZRANGE ... WITHSCORES a [(miembro, puntaje_float)], venga plano o en pares."""
    if respuesta and isinstance(respuesta[0], (list, tuple)):
        return [(m, float(p)) for m, p in respuesta]
    return [(m, float(p)) for m, p in zip(respuesta[0::2], respuesta[1::2])]
```

(Los comandos antiguos `ZREVRANGE` y similares están obsoletos desde Redis 6.2.)

### 2.5 Hash: `HSET` / `HGETALL`

```text
# redis-cli
HSET biblioteca:socio:soc-007 nombre "Ana" plan "premium"
HGETALL biblioteca:socio:soc-007
HINCRBY biblioteca:socio:soc-007 prestamos 1
```

```python
# redis-py: execute_command
r.execute_command("HSET", "biblioteca:socio:soc-007", "nombre", "Ana", "plan", "premium")  # int: campos nuevos
socio = r.execute_command("HGETALL", "biblioteca:socio:soc-007")   # dict[str, str]; {} si no existe
r.execute_command("HINCRBY", "biblioteca:socio:soc-007", "prestamos", 1)                  # int
```

Todos los valores de un hash son texto: conviertan tipos al leer.

### 2.6 Persistencia

Redis guarda en memoria. Para sobrevivir a un reinicio usa **RDB** (instantáneas periódicas: se puede perder lo escrito después de la última) y/o **AOF** (registro de cada escritura: pierde menos, pesa más). Qué pasa con sus datos tras un reinicio depende de lo que tenga activado su `compose.yaml`; documenten qué esperan perder y si es aceptable.

### 2.7 Varios comandos atómicos: pipeline `MULTI` / `EXEC`

```text
# redis-cli
MULTI
LPUSH biblioteca:socio:soc-007:ultimos lib-001
LTRIM biblioteca:socio:soc-007:ultimos 0 4
EXEC
```

```python
# redis-py: pipeline + execute_command
clave = "biblioteca:socio:soc-007:ultimos"
pipe = r.pipeline(transaction=True)      # MULTI/EXEC: los comandos se ejecutan juntos o ninguno
pipe.execute_command("LPUSH", clave, "lib-001")
pipe.execute_command("LTRIM", clave, 0, 4)
resultados = pipe.execute()              # [1, True]: una respuesta por comando, en orden
```

En el pipeline también se usa `execute_command`; `execute()` envía todo. El pipeline restringido del repo solo expone esos dos métodos.

---

## 3. Neo4j: `cypher-shell` vs driver `neo4j`

Modelo de ejemplo: `(:Socio {id})-[:PRESTO {fecha}]->(:Libro {id, titulo})-[:DE_GENERO]->(:Genero {nombre})` y `(:Autor {id, nombre})-[:ESCRIBIO]->(:Libro)`.

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

### 3.3 Recorrido de varios saltos: autores que comparten género

Autores distintos del dado que escribieron libros de alguno de sus géneros.

```cypher
// cypher-shell
MATCH (:Autor {id: $autor_id})-[:ESCRIBIO]->(:Libro)-[:DE_GENERO]->(g:Genero)
      <-[:DE_GENERO]-(:Libro)<-[:ESCRIBIO]-(otro:Autor)
WHERE otro.id <> $autor_id
RETURN DISTINCT otro.id AS autor_id, otro.nombre AS nombre
ORDER BY nombre
LIMIT $limite;
```

```python
# driver neo4j
CONSULTA = """
MATCH (:Autor {id: $autor_id})-[:ESCRIBIO]->(:Libro)-[:DE_GENERO]->(g:Genero)
      <-[:DE_GENERO]-(:Libro)<-[:ESCRIBIO]-(otro:Autor)
WHERE otro.id <> $autor_id
RETURN DISTINCT otro.id AS autor_id, otro.nombre AS nombre
ORDER BY nombre
LIMIT $limite
"""

def autores_afines(tx, autor_id: str, limite: int) -> list[dict]:
    resultado = tx.run(CONSULTA, autor_id=autor_id, limite=limite)
    return [
        {"autor_id": rec["autor_id"], "nombre": rec["nombre"]}
        for rec in resultado      # consumir DENTRO de la transacción
    ]

with driver.session() as session:
    filas = session.execute_read(autores_afines, "aut-001", 10)
```

El recorrido, el `DISTINCT`, el orden y el límite los hace Neo4j. Python solo convierte filas en diccionarios.

### 3.4 Camino más corto con longitud variable (`shortestPath`)

Conexión entre dos socios a través de libros que ambos tomaron en préstamo (socio, libro, socio, ...). `*..6` es la **cota superior**: sin ella la búsqueda de longitud variable puede explotar.

```cypher
// cypher-shell
MATCH (a:Socio {id: $desde}), (b:Socio {id: $hasta}),
      p = shortestPath((a)-[:PRESTO*..6]-(b))
RETURN [n IN nodes(p) | coalesce(n.titulo, n.id)] AS camino, length(p) AS saltos;
```

```python
# driver neo4j
CAMINO = """
MATCH (a:Socio {id: $desde}), (b:Socio {id: $hasta}),
      p = shortestPath((a)-[:PRESTO*..6]-(b))
RETURN [n IN nodes(p) | coalesce(n.titulo, n.id)] AS camino, length(p) AS saltos
"""

def conexion(tx, desde: str, hasta: str) -> dict | None:
    rec = tx.run(CAMINO, desde=desde, hasta=hasta).single()
    return None if rec is None else {"camino": rec["camino"], "saltos": rec["saltos"]}

with driver.session() as session:
    resultado = session.execute_read(conexion, "soc-001", "soc-009")   # None si no hay camino
```

### 3.5 Filtro de existencia: `WHERE NOT (patrón)`

Un patrón dentro de `WHERE` pregunta si existe (o no) una relación. Ejemplo independiente: libros que nunca fueron prestados.

```cypher
// cypher-shell
MATCH (l:Libro)
WHERE NOT ()-[:PRESTO]->(l)
RETURN l.titulo AS titulo
ORDER BY titulo;
```

```python
# driver neo4j
SIN_PRESTAR = """
MATCH (l:Libro)
WHERE NOT ()-[:PRESTO]->(l)
RETURN l.titulo AS titulo
ORDER BY titulo
"""

with driver.session() as session:
    titulos = session.execute_read(lambda tx: [r["titulo"] for r in tx.run(SIN_PRESTAR)])
```

### 3.6 Consumir resultados

```python
resultado = tx.run("MATCH (l:Libro) RETURN l.id AS id, l.titulo AS titulo LIMIT 3")

for rec in resultado:                  # iteración: un Record por fila
    rec["id"], rec["titulo"]           # acceso por alias del RETURN

filas = resultado.data()               # list[dict]: {"id": ..., "titulo": ...}
una = resultado.single()               # exactamente una fila (o None / aviso si hay 0 o más de 1)
```

El resultado es un flujo ligado a la transacción: consúmanlo antes de que la función de transacción termine. Un nodo completo (`RETURN l`) llega como objeto `Node`; para propiedades usen `dict(rec["l"])` o, mejor, devuelvan solo lo que necesitan (`RETURN l.id AS id`).

### 3.7 `PROFILE` / `EXPLAIN`

Se muestra sobre la consulta de autores afines (3.3).

```cypher
// cypher-shell
PROFILE
MATCH (:Autor {id: 'aut-001'})-[:ESCRIBIO]->(:Libro)-[:DE_GENERO]->(g:Genero)
      <-[:DE_GENERO]-(:Libro)<-[:ESCRIBIO]-(otro:Autor)
WHERE otro.id <> 'aut-001'
RETURN DISTINCT otro.nombre AS autor, g.nombre AS genero;
```

```python
# driver neo4j: PROFILE ejecuta la consulta; EXPLAIN solo planifica
with driver.session() as session:
    resultado = session.run(
        "PROFILE MATCH (:Autor {id: $id})-[:ESCRIBIO]->(l:Libro) RETURN l.titulo", id="aut-001"
    )
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
claves = r.execute_command("KEYS", "biblioteca:libro:*:prestamos")
conteos = {k: int(r.execute_command("GET", k)) for k in claves}
top = sorted(conteos.items(), key=lambda kv: kv[1], reverse=True)[:5]
```

```python
# BIEN: la estructura ordenada la mantiene el motor; se pide solo el top 5
top = r.execute_command("ZRANGE", "biblioteca:ranking:prestamos", 0, 4, "REV", "WITHSCORES")
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
# MAL: 1 consulta para los géneros del autor + 1 por cada género
generos = tx.run(
    "MATCH (:Autor {id: $id})-[:ESCRIBIO]->(:Libro)-[:DE_GENERO]->(g:Genero) RETURN DISTINCT g.nombre AS nombre",
    id=autor_id,
).data()
colegas = {}
for g in generos:
    colegas[g["nombre"]] = tx.run(
        "MATCH (:Genero {nombre: $n})<-[:DE_GENERO]-(:Libro)<-[:ESCRIBIO]-(a:Autor) RETURN DISTINCT a.nombre AS nombre",
        n=g["nombre"],
    ).data()
```

```python
# BIEN: un solo recorrido que devuelve todo agrupado por género
filas = tx.run(
    """
    MATCH (:Autor {id: $id})-[:ESCRIBIO]->(:Libro)-[:DE_GENERO]->(g:Genero)
          <-[:DE_GENERO]-(:Libro)<-[:ESCRIBIO]-(otro:Autor)
    WHERE otro.id <> $id
    RETURN g.nombre AS genero, collect(DISTINCT otro.nombre) AS autores
    """,
    id=autor_id,
).data()
```

Lo mismo vale en MongoDB: un `find` por documento dentro de un bucle se reemplaza por `$in` o por `$lookup`.

### 4.e Métodos de conveniencia de redis-py

```python
# MAL: oculta el comando; no se lee como redis-cli (y connections.redis lo rechaza con AttributeError)
r.zincrby("biblioteca:ranking:prestamos", 1, "lib-001")
r.set("biblioteca:libro:lib-001", "...", ex=60)
```

```python
# BIEN: el comando literal
r.execute_command("ZINCRBY", "biblioteca:ranking:prestamos", 1, "lib-001")
r.execute_command("SET", "biblioteca:libro:lib-001", "...", "EX", 60)
```

### 4.f Una clase modelo de ODM

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
