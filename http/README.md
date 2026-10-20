# Coleccion HTTP de NEXUS

Archivos `.http` para probar la API y los 7 escenarios a mano (y en la demo). Son texto plano: funcionan en VS Code REST Client, JetBrains HTTP Client y kulala.nvim.

Alternativas sin instalar nada: la interfaz de prueba en `/ui` y Swagger UI en `/docs` (ver el README principal). Para mirar los datos en MongoDB, Redis y Neo4j: [Clientes de base de datos](../README.md#clientes-de-base-de-datos).

## Como usarlos

- **VS Code**: extension *REST Client* (humao.rest-client). Abrir un `.http` y clic en `Send Request` sobre cada pedido.
- **JetBrains** (IntelliJ, PyCharm, WebStorm): soporte HTTP Client incluido. Abrir el archivo y usar el icono verde de cada pedido.
- **kulala.nvim**: abrir el archivo y ejecutar `require("kulala").run()` (por defecto `<leader>Rs`).

Cada archivo define `@baseUrl = http://localhost:8000` al inicio. Cambienlo ahi si la API corre en otro lado.

## Requisitos

```bash
cp .env.example .env
docker compose up --build -d   # API en http://localhost:8000
make seed                      # dataset cargado
```

Sin Docker: `ADAPTERS=fake uv run uvicorn app.main:app --reload`. Los TODO sin implementar responden **501**.

## Orden recomendado

`00-health-admin` -> `01-catalog` -> `scenario-01` ... `scenario-07`.

## Estado y datos

Los escenarios **modifican datos** (productos, ordenes, contadores). Los escenarios 01-03 usan ids propios (`demo-s01`, ...): si los repiten, cambien el id en la variable del inicio. Para volver a un estado limpio: `make seed`.

Cuando un pedido necesita un id creado antes (ej. el id de una orden), copienlo en la variable del inicio (`@orderId = ...`), tal como indica el comentario.

## Archivos

| Archivo | Escenario | Que observar |
|---------|-----------|--------------|
| `00-health-admin.http` | Salud y admin | `/health` con los 3 motores `ok`; faults, sync-status, reconcile |
| `01-catalog.http` | Catalogo (CRUD y busquedas) | 201/204/404; filtros por categoria, stock, precio y `attr.*`; notebooks disponibles en rango de precios |
| `scenario-01-first-read.http` | 01 Primera lectura | `X-Cache: MISS`, luego `HIT` |
| `scenario-02-repeated-read.http` | 02 Lectura repetida | `X-Cache: HIT` en lecturas siguientes |
| `scenario-03-update-invalidates.http` | 03 Update sin cache vieja | HIT -> PUT -> precio nuevo con `MISS` -> `HIT`; borrado da 404 |
| `scenario-04-views-activity.http` | 04 Vistas | contador +N, historial reciente sin duplicados, ranking descendente |
| `scenario-05-purchase.http` | 05 Compra | 201, `sync_status: synced`, total, snapshot de precio, 409/404 |
| `scenario-06-recommendations.http` | 06 Recomendaciones | sin lo ya comprado, con detalles de Mongo; antes/despues de comprar `kb-002` |
| `scenario-07-partial-failure.http` | 07 Falla parcial | `failed` -> sync-status -> falla off -> reconcile -> `synced` |
