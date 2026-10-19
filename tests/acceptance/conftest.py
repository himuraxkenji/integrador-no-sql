"""Pruebas de aceptación: pegan contra la API REAL corriendo (docker compose up).

Asumen que ya cargaron el dataset:  make seed   (o `python -m scripts.seed`)
Si quieren que los tests lo carguen solos, exporten NEXUS_RUN_SEED=1 (requiere
correr pytest dentro del contenedor: `docker compose exec app pytest tests/acceptance`).

Solo verifican comportamiento OBSERVABLE: headers, contadores, estados, contenido.
"""

import os
import subprocess
import sys
import uuid

import httpx
import pytest

BASE_URL = os.environ.get("NEXUS_BASE_URL", "http://localhost:8000")


def pytest_collection_modifyitems(items):
    for item in items:
        if "acceptance" in str(item.fspath):
            item.add_marker(pytest.mark.acceptance)


@pytest.fixture(scope="session", autouse=True)
def seeded_api():
    if os.environ.get("NEXUS_RUN_SEED") == "1":
        subprocess.run([sys.executable, "-m", "scripts.seed"], check=True)
    try:
        httpx.get(f"{BASE_URL}/health", timeout=5)
    except httpx.HTTPError as exc:
        pytest.exit(f"La API no responde en {BASE_URL}. ¿Levantaron `docker compose up`? ({exc})", returncode=2)


@pytest.fixture(scope="session")
def api():
    with httpx.Client(base_url=BASE_URL, timeout=10) as client:
        yield client


@pytest.fixture
def new_product(api):
    """Fábrica de productos únicos: así cada test arranca con la caché vacía para ese id."""

    def _create(price=100.0, stock=10, category="notebooks", **attrs):
        body = {
            "name": f"Producto de prueba {uuid.uuid4().hex[:6]}",
            "category": category,
            "price": price,
            "stock": stock,
            "attributes": attrs,
        }
        response = api.post("/products", json=body)
        assert response.status_code == 201, response.text
        return response.json()

    return _create


@pytest.fixture
def relations_fault(api):
    """Enciende/apaga la falla de las relaciones de compra (relations_down) y SIEMPRE la apaga al terminar."""

    def _set(down: bool):
        assert api.post("/admin/faults", json={"relations_down": down}).status_code == 200

    yield _set
    api.post("/admin/faults", json={"relations_down": False})
