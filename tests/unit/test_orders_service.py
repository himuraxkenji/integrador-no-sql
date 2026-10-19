import pytest

from app.orders.domain import OrderSyncStatus, OrderItemRequest
from app.shared.errors import ConflictError, NotFoundError


def items(product_id="nb", quantity=1):
    return [OrderItemRequest(product_id=product_id, quantity=quantity)]


class TestPlaceOrder:
    def test_happy_path_persists_order_and_updates_relations(self, world):
        order = world.orders.place_order("ana", items("nb", 2))
        assert order.sync_status == OrderSyncStatus.SYNCED
        assert order.total == 2000
        assert world.orders_repo.get(order.id).sync_status == OrderSyncStatus.SYNCED
        assert "nb" in world.relations.purchases["ana"]

    def test_price_is_a_snapshot(self, world):
        order = world.orders.place_order("ana", items("nb"))
        world.products.update("nb", {"price": 1})
        assert world.orders_repo.get(order.id).items[0].unit_price == 1000

    def test_relations_failure_keeps_order_as_failed(self, world):
        world.faults.relations_down = True
        order = world.orders.place_order("ana", items("nb"))
        stored = world.orders_repo.get(order.id)
        assert stored is not None
        assert stored.sync_status == OrderSyncStatus.FAILED
        assert stored.sync_error
        assert "ana" not in world.relations.purchases or "nb" not in world.relations.purchases["ana"]

    def test_insufficient_stock_persists_nothing(self, world):
        with pytest.raises(ConflictError):
            world.orders.place_order("ana", items("kb", 2))
        assert world.orders_repo.list_by_customer("ana") == []

    def test_unknown_customer(self, world):
        with pytest.raises(NotFoundError):
            world.orders.place_order("fantasma", items())

    def test_unknown_product(self, world):
        with pytest.raises(NotFoundError):
            world.orders.place_order("ana", items("nope"))

    def test_inactive_product_cannot_be_bought(self, world):
        world.products.soft_delete("nb")
        with pytest.raises(NotFoundError):
            world.orders.place_order("ana", items("nb"))


class TestReconcile:
    def test_sync_status_detects_failed_orders(self, world):
        world.faults.relations_down = True
        order = world.orders.place_order("ana", items())
        status = world.orders.sync_status()
        assert status.counts["failed"] == 1
        assert [o.id for o in status.unsynced] == [order.id]

    def test_reconcile_recovers_failed_orders(self, world):
        world.faults.relations_down = True
        order = world.orders.place_order("ana", items())
        world.faults.relations_down = False

        report = world.orders.reconcile()

        assert report.synced == 1 and report.still_failed == 0
        assert order.id in report.synced_order_ids
        assert world.orders_repo.get(order.id).sync_status == OrderSyncStatus.SYNCED
        assert "nb" in world.relations.purchases["ana"]

    def test_reconcile_with_relations_still_down_keeps_failed(self, world):
        world.faults.relations_down = True
        world.orders.place_order("ana", items())
        report = world.orders.reconcile()
        assert report.synced == 0 and report.still_failed == 1

    def test_reconcile_is_idempotent(self, world):
        world.faults.relations_down = True
        world.orders.place_order("ana", items())
        world.faults.relations_down = False
        world.orders.reconcile()
        second = world.orders.reconcile()
        assert second.checked == 0
