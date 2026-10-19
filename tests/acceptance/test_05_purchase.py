"""Escenario 05: una compra crea la orden en MongoDB y actualiza las relaciones de compra."""

CUSTOMER = "c-008"


def buy(api, product_id, quantity=1, customer=CUSTOMER):
    return api.post("/orders", json={"customer_id": customer, "items": [{"product_id": product_id, "quantity": quantity}]})


def test_purchase_creates_order_and_syncs_relations(api, new_product):
    product = new_product(price=100.0, stock=10)
    response = buy(api, product["id"], quantity=2)
    assert response.status_code == 201
    order = response.json()
    assert order["sync_status"] == "synced"
    assert order["total"] == 200.0
    assert order["items"][0]["quantity"] == 2

    fetched = api.get(f"/orders/{order['id']}").json()
    assert fetched["sync_status"] == "synced"
    assert order["id"] in [o["id"] for o in api.get(f"/customers/{CUSTOMER}/orders").json()]


def test_order_keeps_price_snapshot(api, new_product):
    product = new_product(price=100.0)
    order = buy(api, product["id"]).json()
    api.put(f"/products/{product['id']}", json={"price": 999.0})
    assert api.get(f"/orders/{order['id']}").json()["items"][0]["unit_price"] == 100.0


def test_insufficient_stock_is_rejected(api, new_product):
    product = new_product(stock=1)
    assert buy(api, product["id"], quantity=5).status_code == 409


def test_unknown_product_or_customer_is_404(api, new_product):
    assert buy(api, "no-existe").status_code == 404
    assert buy(api, new_product()["id"], customer="fantasma").status_code == 404
