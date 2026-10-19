"""Escenario 02: las lecturas repetidas las responde la caché (X-Cache: HIT)."""


def test_repeated_gets_are_served_by_cache(api, new_product):
    product = new_product()
    url = f"/products/{product['id']}"
    assert api.get(url).headers["X-Cache"] == "MISS"
    for _ in range(3):
        response = api.get(url)
        assert response.status_code == 200
        assert response.headers["X-Cache"] == "HIT"
        assert response.json() == api.get(url).json()
