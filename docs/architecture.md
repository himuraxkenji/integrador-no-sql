# Arquitectura

**Cada petición pasa por `router → service → puerto → adaptador`. Los puertos son las interfaces; los adaptadores hablan con un motor.** Ustedes escriben adaptadores y la coordinación en los servicios.

## Flujo de una lectura con caché (escenarios 01-02)

```mermaid
sequenceDiagram
    participant C as Cliente
    participant R as Router
    participant S as CatalogService
    participant K as ProductCache (motor a elección)
    participant M as ProductRepository (Mongo)
    C->>R: GET /products/nb-001
    R->>S: get_product
    S->>K: get
    alt en caché
        K-->>S: producto
        S-->>R: (producto, HIT)
    else no está
        S->>M: get_by_id
        M-->>S: producto
        S->>K: set(ttl)
        S-->>R: (producto, MISS)
    end
    R-->>C: 200 + header X-Cache
```

## Flujo de una compra (escenarios 05 y 07)

```mermaid
sequenceDiagram
    participant S as OrderService
    participant M as Mongo
    participant G as PurchaseRelations (motor a elección)
    S->>M: validar cliente, productos y stock
    S->>M: guardar orden (sync_status = pending)
    S->>G: reflejar compra (idempotente)
    alt ok
        S->>M: sync_status = synced
    else falla
        S->>M: sync_status = failed
    end
```

La orden **nunca** se pierde: MongoDB es la verdad y las relaciones de compra son una proyección derivada que se puede reconstruir (`reconcile`).

## Mapa de carpetas

| Pieza | Quién la escribe | Para qué |
|-------|------------------|----------|
| `domain.py` | Cátedra | Modelos pydantic |
| `ports.py` | Cátedra | Contrato de cada adaptador (docstrings = semántica esperada) |
| `router.py` | Cátedra | REST completo |
| `service.py` | Mixto | Provisto lo trivial; `TODO(alumnos)` donde hay coordinación entre motores |
| `adapters/` | **Alumnos** | Mongo (fijo) y los almacenes derivados (motor a elección: caché, actividad, relaciones, recomendaciones) |
| `app/fakes.py` | Cátedra | Todos los puertos en memoria |
| `app/container.py` | Cátedra | Elige real/fake según `ADAPTERS` |
| `app/admin/faults.py` | Cátedra | `FaultyPurchaseRelations`: simula las relaciones de compra caídas |
| `app/infrastructure/` | Cátedra | Conexiones y mapeo `id` ↔ `_id` |
| `app/seeding.py` | Cátedra | Carga el dataset usando los puertos |

## Observabilidad que usan los tests

| Qué | Dónde |
|-----|-------|
| Origen de la lectura | Header `X-Cache: HIT \| MISS` en `GET /products/{id}` |
| Estado de sincronización por orden | Campo `sync_status` (`pending \| synced \| failed`) persistido en Mongo |
| Falla inyectada | `POST /admin/faults {"relations_down": true}` |
| Detección | `GET /admin/sync-status` |
| Recuperación | `POST /admin/reconcile` |

## Reglas que los puertos imponen

- El repositorio de productos **no filtra por `active`** (salvo `search`): el servicio decide.
- `PurchaseRelations` es **idempotente**: ejecutar dos veces deja lo mismo que una.
- `RecommendationFinder` devuelve **solo ids y puntajes**; los datos comerciales vienen de Mongo.
- `ActivityStore`, `ProductCache`, `PurchaseRelations` y `RecommendationFinder` **no imponen motor ni estructura**: los eligen ustedes y los justifican en `docs/decisions.md`.
- Entre todos los almacenes derivados deben usarse **MongoDB, Redis y Neo4j** con una responsabilidad real cada uno.
