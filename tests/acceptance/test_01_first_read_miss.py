"""Escenario 01: la primera lectura la responde MongoDB y deja una entrada en caché."""


def test_first_get_is_served_by_mongo(api, new_product):
    product = new_product()
    response = api.get(f"/products/{product['id']}")
    assert response.status_code == 200
    assert response.headers["X-Cache"] == "MISS"
    assert response.json()["name"] == product["name"]


def test_first_get_creates_cache_entry(api, new_product):
    product = new_product()
    api.get(f"/products/{product['id']}")
    assert api.get(f"/products/{product['id']}").headers["X-Cache"] == "HIT"


def test_unknown_product_is_404(api):
    assert api.get("/products/no-existe").status_code == 404
