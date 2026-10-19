"""Escenario 04: las vistas actualizan contadores, historial reciente y ranking."""

import os

CUSTOMER = "c-008"
RECENT_LIMIT = int(os.environ.get("RECENT_VIEWS_LIMIT", "10"))


def view(api, product_id, customer=CUSTOMER):
    assert api.post(f"/products/{product_id}/views", json={"customer_id": customer}).status_code == 202


def count(api, product_id):
    return api.get(f"/products/{product_id}/views").json()["views"]


def test_view_counter_increments(api, new_product):
    pid = new_product()["id"]
    assert count(api, pid) == 0
    for _ in range(3):
        view(api, pid)
    assert count(api, pid) == 3


def test_recent_history_most_recent_first_without_duplicates(api, new_product):
    a, b = new_product()["id"], new_product()["id"]
    view(api, a)
    view(api, b)
    view(api, a)  # ver 'a' de nuevo la deja primera, sin repetirse
    recent = api.get(f"/customers/{CUSTOMER}/recent").json()["product_ids"]
    assert recent[:2] == [a, b]
    assert len(recent) == len(set(recent))


def test_recent_history_is_bounded(api, new_product):
    for _ in range(RECENT_LIMIT + 2):
        view(api, new_product()["id"], customer="c-007")
    recent = api.get("/customers/c-007/recent", params={"limit": 1000}).json()["product_ids"]
    assert len(recent) == RECENT_LIMIT


def test_top_products_ranks_by_views(api, new_product):
    popular, quiet = new_product()["id"], new_product()["id"]
    for _ in range(50):
        view(api, popular, customer="c-006")
    view(api, quiet, customer="c-006")
    top = api.get("/activity/top", params={"limit": 100}).json()
    ids = [t["product_id"] for t in top]
    assert ids.index(popular) < ids.index(quiet)
    views = [t["views"] for t in top]
    assert views == sorted(views, reverse=True)
