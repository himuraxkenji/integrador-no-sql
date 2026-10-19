"""Escenario 06: recomendaciones = candidatos del RecommendationFinder + detalles de MongoDB, sin lo ya comprado.

Se apoya en el dataset de `datasets/`: Ana (c-001) compró nb-001 y ms-001; Luis y Carlos
compraron ms-001 y kb-001; Sofía compró nb-001, mn-002 y mn-004 (hoy inactivo).
"""


def recs(api, customer, limit=20):
    response = api.get(f"/customers/{customer}/recommendations", params={"limit": limit})
    assert response.status_code == 200
    return response.json()


def ids(recommendations):
    return [r["product"]["id"] for r in recommendations]


def test_customers_who_bought_the_same_also_bought(api):
    result = recs(api, "c-001")
    assert ids(result)[0] == "kb-001"  # lo compraron 2 clientes que comparten compras con Ana
    assert "mn-002" in ids(result)


def test_excludes_what_the_customer_already_bought(api):
    result = ids(recs(api, "c-001"))
    assert "nb-001" not in result and "ms-001" not in result


def test_recommendations_carry_commercial_details_from_mongo(api):
    first = recs(api, "c-001")[0]
    assert first["product"]["name"] == "Teclado Mecánico Forge"
    assert first["product"]["price"] == 90
    assert first["score"] > 0 and first["reason"]


def test_inactive_products_are_dropped(api):
    assert "mn-004" not in ids(recs(api, "c-001"))


def test_a_new_purchase_is_excluded_from_then_on(api):
    # Valentina (c-007) se interesa por teclados: kb-002 es un candidato hasta que lo compra.
    target = "kb-002"
    order = api.post("/orders", json={"customer_id": "c-007", "items": [{"product_id": target, "quantity": 1}]})
    assert order.status_code == 201
    assert target not in ids(recs(api, "c-007"))
