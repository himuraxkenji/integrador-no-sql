"""La interfaz de prueba (/ui) se sirve desde la misma API, sin Docker (ADAPTERS=fake)."""

import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from app.main import app

    patch = pytest.MonkeyPatch()
    patch.setenv("ADAPTERS", "fake")
    try:
        with TestClient(app) as c:
            yield c
    finally:
        patch.undo()


def test_root_redirects_to_ui(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/ui/"


def test_ui_index_is_html_with_app_root(client):
    response = client.get("/ui/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert 'id="app"' in response.text


def test_assets_referenced_by_index_are_served(client):
    html = client.get("/ui/").text
    assets = re.findall(r'(?:href|src)="([^"]+)"', html)
    assert assets, "index.html debería referenciar CSS y JS"
    for asset in assets:
        if asset.startswith("data:"):
            continue
        assert not asset.startswith(("http:", "https:", "//")), f"{asset}: la UI debe funcionar sin red"
        assert client.get(f"/ui/{asset}").status_code == 200, asset


def test_js_modules_imported_by_main_are_served(client):
    main = client.get("/ui/js/main.js").text
    modules = re.findall(r'from "\./([\w.]+)"', main)
    assert modules
    for module in modules:
        response = client.get(f"/ui/js/{module}")
        assert response.status_code == 200, module
        assert "javascript" in response.headers["content-type"]


def test_ui_routes_are_not_in_openapi(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert not [p for p in paths if p == "/" or p.startswith("/ui")]


def test_ui_has_loading_feedback_respecting_reduced_motion(client):
    css = client.get("/ui/styles.css").text
    assert "@keyframes spin" in css and ".activity-bar" in css
    assert "prefers-reduced-motion: reduce" in css
    api = client.get("/ui/js/api.js").text
    assert "export function onBusy" in api
    util = client.get("/ui/js/util.js").text
    assert "aria-busy" in util and 'role: "status"' in util
