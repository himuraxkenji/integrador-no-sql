# Modelo de datos

**Completen este documento con lo que realmente implementaron.** Los ejemplos entre corchetes son orientativos; reemplácenlos. Si el código y este archivo se contradicen, hay un error en alguno de los dos.

## MongoDB

| Colección | Qué guarda | Forma del documento (completar) | Índices (completar) |
|-----------|------------|---------------------------------|---------------------|
| `products` | Catálogo | `_id`, `name`, `category`, `price`, `stock`, `active`, `attributes{...}` | |
| `customers` | Clientes | | |
| `orders` | Compras | `_id`, `customer_id`, `items[{product_id, quantity, unit_price}]`, `total`, `created_at`, `sync_status`, `sync_error` | |

Preguntas:

- ¿Por qué `attributes` es un subdocumento y no columnas fijas? ¿Qué consultas lo aprovechan?
- ¿Por qué los ítems de la orden van **embebidos** y con el precio copiado? ¿Qué pasaría si solo guardaran `product_id`?
- ¿Qué índices crearon para `search` y para `list_by_sync_status`? Muestren una consulta y su `explain()`.

## Modelo de los almacenes derivados (completar según su elección)

Los almacenes derivados (caché, actividad, relaciones, recomendaciones) los **elige cada equipo**. Completen **solo las secciones de los motores que usaron** y aclaren qué responsabilidad cumple cada uno (debe figurar en `docs/decisions.md`).

### MongoDB (derivados, si lo usaron)

| Responsabilidad | Colección | Forma del documento (completar) | Índices / TTL (completar) |
|-----------------|-----------|---------------------------------|---------------------------|
| | | | |

### Redis (si lo usaron)

| Responsabilidad | Estructura elegida | Clave (convención) | TTL / límite | Comandos usados |
|-----------------|--------------------|--------------------|--------------|-----------------|
| | | | | |

### Neo4j (si lo usaron)

| Elemento | Etiqueta / tipo | Propiedades | Restricciones o índices |
|----------|-----------------|-------------|--------------------------|
| | | | |

Preguntas (respondan las que apliquen a su elección):

- ¿Cómo logran que `record_purchase` sea idempotente con el motor elegido?
- ¿Cómo garantizan que el historial no crece sin límite y no repite productos?
- ¿Cómo obtienen el ranking **sin ordenar en Python**?
- ¿Las dos escrituras de `register_view` son atómicas? ¿Importa?
- ¿Qué propiedades del producto viven en el almacén de relaciones y cuáles **no** (y por qué)?
- Peguen la consulta de recomendaciones y expliquen cada parte.

## Dónde vive cada dato

| Dato | Mongo | Redis | Neo4j | Fuente de verdad |
|------|:-----:|:-----:|:-----:|------------------|
| Precio del producto | sí | completar | completar | Mongo |
| Vistas de un producto | | | | |
| Compra de un cliente | sí | completar | completar | Mongo |
| Categorías de interés | sí | | | |
