# Decisiones de diseño

## Tabla de motores elegidos (OBLIGATORIA)

**Completen esta tabla primero. MongoDB es fijo como fuente de verdad; el motor de cada fila es decisión de ustedes.** Condición: entre todas las filas deben usar **MongoDB, Redis y Neo4j** con una responsabilidad real cada uno.

| Responsabilidad | Motor elegido | Patrón de acceso | Justificación | Alternativa descartada y por qué |
|-----------------|---------------|------------------|---------------|----------------------------------|
| Caché de productos | | | | |
| Contadores de vistas | | | | |
| Actividad reciente | | | | |
| Ranking de más vistos | | | | |
| Relaciones de compra | | | | |
| Recomendaciones | | | | |

| Verificación | Sí / No y evidencia |
|--------------|---------------------|
| ¿Usan los tres motores con responsabilidad real? | |

## Cómo completar

Para cada decisión usen este formato:

```
Decisión: ...
Alternativas consideradas: ...
Por qué elegimos esta: ...
Qué costo/riesgo aceptamos: ...
```

## 1. Estructuras de actividad (según el motor elegido)

- [ ] ¿Qué estructura o modelo eligieron para el **ranking de más vistos** y por qué?
- [ ] ¿Y para el **historial reciente** (acotado, sin repetidos)?
- [ ] ¿Y para el **contador** por producto? ¿Por qué no usar la misma estructura que el ranking (o sí)?
- [ ] ¿Cómo eligieron el **TTL** de la caché y cómo lo implementa el motor elegido? ¿Qué pasa si es muy corto? ¿Y muy largo?

## 2. Caché

- [ ] ¿Qué pasa con la caché si **se reinicia el motor elegido para la caché**? ¿Se pierde algo importante?
- [ ] ¿Qué pasa con los **contadores e historial** si se reinicia su motor? ¿Es aceptable? (Si usan Redis: Compose activa AOF, ¿qué cambia con y sin él?)
- [ ] Al actualizar un producto, ¿invalidan **antes o después** de escribir en Mongo? ¿Qué carrera existe entre una lectura y una escritura concurrentes?
- [ ] ¿Por qué invalidar y no actualizar la caché en el `update`?
- [ ] ¿Qué pasa si falla la invalidación (el motor de la caché caído en el `update`)?

## 3. Consistencia entre motores

- [ ] ¿Por qué la orden se guarda en Mongo **antes** que en las relaciones de compra y no al revés?
- [ ] ¿Qué estados intermedios puede observar un usuario? (Ej.: orden creada, recomendaciones todavía sin esa compra.)
- [ ] ¿Qué garantiza que `reconcile` sea **idempotente**? ¿Qué pasa si dos reconciliaciones corren a la vez?
- [ ] ¿Qué pasa si la app se cae **entre** guardar la orden y actualizar el estado? ¿En qué estado queda esa orden y quién la recupera?
- [ ] ¿Cuándo conviene reconciliar automáticamente (job periódico) en lugar de un endpoint manual?
- [ ] ¿Qué harían para **no** tener consistencia eventual? ¿Qué costo tendría?

## 4. MongoDB

- [ ] ¿Qué índices crearon y para qué consultas?
- [ ] ¿Embebieron o referenciaron los ítems de la orden? ¿Por qué?
- [ ] ¿Cómo manejan el stock ante compras simultáneas? (Aunque no lo implementen: ¿qué problema aparece?)

## 5. Relaciones y recomendaciones (según el motor elegido)

- [ ] ¿Por qué el motor elegido para recomendar y no una consulta sobre Mongo? ¿A partir de qué volumen se nota?
- [ ] ¿Cómo combinan "también compraron" con intereses por categoría? ¿Cómo ponderan?
- [ ] ¿Qué pasa con un producto que se da de baja (soft delete) pero sigue en las relaciones derivadas?

## Evidencia de que el motor hace el trabajo

Plantilla a completar. Regla: consultas nativas con el driver oficial, sin ORM, y filtros/ordenamientos/conteos/recorridos resueltos en el motor (ver [guia-consultas.md](guia-consultas.md)). Esta evidencia se revisa en la defensa oral.

### Búsqueda de productos (MongoDB)

- Índice(s) creado(s) (`create_index`): `<COMPLETAR>`
- Consulta ejecutada (filtro, proyección, sort, limit): `<COMPLETAR>`
- Resumen de `explain("executionStats")`:

| Dato | Valor |
|------|-------|
| `winningPlan` (stage) | `<COMPLETAR: IXSCAN o COLLSCAN>` |
| `indexName` | `<COMPLETAR>` |
| `totalKeysExamined` | `<COMPLETAR>` |
| `totalDocsExamined` | `<COMPLETAR>` |
| `nReturned` | `<COMPLETAR>` |

- Conclusión: `<COMPLETAR: ¿IXSCAN? ¿docs examinados cercanos a los devueltos?>`

### Recomendaciones

Si están en Neo4j, pegar el resumen de `PROFILE` (o `EXPLAIN`) de la consulta de recomendación. Si están en otro motor, la evidencia equivalente (por ejemplo `explain()` del pipeline o los comandos usados y su complejidad).

- Consulta (Cypher / pipeline / comandos): `<COMPLETAR>`
- Resumen del plan:

| Dato | Valor |
|------|-------|
| Operadores de acceso (`NodeIndexSeek` / `NodeByLabelScan` / `AllNodesScan`) | `<COMPLETAR>` |
| `db hits` totales | `<COMPLETAR>` |
| Filas devueltas | `<COMPLETAR>` |

- Conclusión: `<COMPLETAR>`

### Operaciones que corren en el motor, por almacén derivado

| Almacén derivado | Motor | Operaciones resueltas por el motor | Qué hace Python |
|------------------|-------|------------------------------------|-----------------|
| Caché de productos | `<COMPLETAR>` | `<COMPLETAR: p. ej. expiración, borrado de clave>` | `<COMPLETAR: serializar/deserializar>` |
| Actividad (contadores, historial, ranking) | `<COMPLETAR>` | `<COMPLETAR: incremento atómico, recorte, orden por puntaje>` | `<COMPLETAR>` |
| Relaciones de compra | `<COMPLETAR>` | `<COMPLETAR: upsert idempotente, restricciones>` | `<COMPLETAR>` |
| Recomendaciones | `<COMPLETAR>` | `<COMPLETAR: recorrido, exclusión, conteo y orden>` | `<COMPLETAR>` |

- [ ] Ninguna consulta trae colecciones completas para filtrar u ordenar en Python
- [ ] Ningún recorrido de relaciones se hace con bucles de consultas (N+1)
- [ ] Todo Cypher usa parámetros (sin concatenar datos del usuario)

## 6. Pruebas y límites

- [ ] ¿Qué escenarios de falla probaron además del 07 (motor de caché caído, Mongo caído)? ¿Qué hace la API?
- [ ] ¿Qué dejaron fuera y por qué?

## Registro de cambios (opcional)

| Fecha | Decisión | Motivo |
|-------|----------|--------|
| | | |
