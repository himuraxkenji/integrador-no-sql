"""Escenario 03: tras actualizar o borrar, la caché no sirve datos viejos."""


def test_update_is_visible_immediately(api, new_product):
    product = new_product(price=100.0)
    url = f"/products/{product['id']}"
    api.get(url)
    assert api.get(url).headers["X-Cache"] == "HIT"

    assert api.put(url, json={"price": 150.0}).status_code == 200

    after = api.get(url)
    assert after.json()["price"] == 150.0  # no quedó el precio viejo
    assert after.headers["X-Cache"] == "MISS"  # se re-leyó de Mongo
    assert api.get(url).headers["X-Cache"] == "HIT"  # y volvió a cachearse


def test_partial_update_keeps_other_fields(api, new_product):
    product = new_product(price=100.0)
    updated = api.put(f"/products/{product['id']}", json={"stock": 3}).json()
    assert updated["stock"] == 3
    assert updated["price"] == 100.0


def test_delete_is_soft_and_cache_is_not_stale(api, new_product):
    product = new_product()
    url = f"/products/{product['id']}"
    api.get(url)
    assert api.delete(url).status_code == 204
    assert api.get(url).status_code == 404
    found = api.get("/products", params={"category": product["category"], "limit": 200}).json()
    assert product["id"] not in [p["id"] for p in found]
