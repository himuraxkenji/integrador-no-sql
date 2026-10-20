from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.activity.router import router as activity_router
from app.admin.router import router as admin_router
from app.catalog.router import router as catalog_router
from app.config import Settings
from app.container import build_container
from app.customers.router import router as customers_router
from app.orders.router import router as orders_router
from app.recommendations.router import router as recommendations_router
from app.shared.errors import ConflictError, RelationsUnavailableError, NotFoundError


@asynccontextmanager
async def lifespan(app: FastAPI):
    container = build_container(Settings())
    app.state.container = container
    yield
    container.close()


app = FastAPI(title="NEXUS", lifespan=lifespan)

for router in (
    catalog_router,
    customers_router,
    activity_router,
    orders_router,
    recommendations_router,
    admin_router,
):
    app.include_router(router)


def _error(status_code: int):
    async def handler(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=status_code)

    return handler


app.add_exception_handler(NotFoundError, _error(404))
app.add_exception_handler(ConflictError, _error(409))
app.add_exception_handler(RelationsUnavailableError, _error(503))
# Un TODO sin implementar responde 501 con el mensaje que dice qué falta hacer.
app.add_exception_handler(NotImplementedError, _error(501))


@app.get("/health", tags=["health"])
def health(request: Request):
    """Verifica conectividad con los tres motores (MongoDB, Redis y Neo4j)."""
    engines = request.app.state.container.health()
    ok = all(v in ("ok", "fake") for v in engines.values())
    return JSONResponse({"status": "ok" if ok else "degraded", **engines}, status_code=200 if ok else 503)


# Interfaz de prueba (HTML/JS estático, sin build): http://localhost:8000/ui
app.mount("/ui", StaticFiles(directory=Path(__file__).parent / "ui", html=True), name="ui")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse("/ui/")
