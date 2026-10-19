"""Escenario 07: si las relaciones de compra fallan, la orden NO se pierde, el estado parcial se DETECTA y se RECUPERA."""

CUSTOMER = "c-008"


def buy(api, product_id):
    return api.post("/orders", json={"customer_id": CUSTOMER, "items": [{"product_id": product_id, "quantity": 1}]})


def unsynced_ids(api):
    return [o["id"] for o in api.get("/admin/sync-status").json()["unsynced"]]


def test_relations_failure_keeps_the_order_and_marks_it_failed(api, new_product, relations_fault):
    relations_fault(True)
    response = buy(api, new_product()["id"])
    assert response.status_code == 201  # la compra se registró
    order = response.json()
    assert order["sync_status"] == "failed"
    assert api.get(f"/orders/{order['id']}").json()["sync_status"] == "failed"


def test_partial_state_is_detectable(api, new_product, relations_fault):
    relations_fault(True)
    order = buy(api, new_product()["id"]).json()
    status = api.get("/admin/sync-status").json()
    assert status["counts"]["failed"] >= 1
    assert order["id"] in unsynced_ids(api)


def test_reconcile_recovers_the_order(api, new_product, relations_fault):
    relations_fault(True)
    order = buy(api, new_product()["id"]).json()

    relations_fault(False)
    report = api.post("/admin/reconcile").json()

    assert order["id"] in report["synced_order_ids"]
    assert api.get(f"/orders/{order['id']}").json()["sync_status"] == "synced"
    assert order["id"] not in unsynced_ids(api)


def test_reconcile_with_relations_still_down_does_not_lose_anything(api, new_product, relations_fault):
    relations_fault(True)
    order = buy(api, new_product()["id"]).json()
    report = api.post("/admin/reconcile").json()
    assert report["still_failed"] >= 1
    assert order["id"] in unsynced_ids(api)


def test_reconcile_twice_is_safe(api, relations_fault):
    relations_fault(False)
    api.post("/admin/reconcile")
    second = api.post("/admin/reconcile").json()
    assert second["checked"] == 0
