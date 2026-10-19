import pytest

from app.catalog.domain import CacheSource, ProductUpdate
from app.shared.errors import NotFoundError
from tests.unit.conftest import TTL


class TestGetProduct:
    def test_first_read_is_miss_and_fills_cache(self, world):
        result = world.catalog.get_product("nb")
        assert result.source == CacheSource.MISS
        assert result.product.name == "Notebook"
        assert world.cache.contains("nb")

    def test_second_read_is_hit(self, world):
        world.catalog.get_product("nb")
        assert world.catalog.get_product("nb").source == CacheSource.HIT

    def test_cache_entry_uses_configured_ttl(self, world):
        world.catalog.get_product("nb")
        assert world.cache.ttls["nb"] == TTL

    def test_unknown_product_raises_and_is_not_cached(self, world):
        with pytest.raises(NotFoundError):
            world.catalog.get_product("nope")
        assert not world.cache.contains("nope")

    def test_inactive_product_is_not_found(self, world):
        world.products.soft_delete("nb")
        with pytest.raises(NotFoundError):
            world.catalog.get_product("nb")


class TestUpdate:
    def test_update_invalidates_cache_so_next_read_is_fresh(self, world):
        world.catalog.get_product("nb")  # llena la caché
        world.catalog.update("nb", ProductUpdate(price=900))
        result = world.catalog.get_product("nb")
        assert result.source == CacheSource.MISS
        assert result.product.price == 900

    def test_update_only_changes_sent_fields(self, world):
        updated = world.catalog.update("nb", ProductUpdate(stock=7))
        assert updated.stock == 7
        assert updated.price == 1000

    def test_update_unknown_product_raises(self, world):
        with pytest.raises(NotFoundError):
            world.catalog.update("nope", ProductUpdate(price=1))


class TestDelete:
    def test_delete_invalidates_cache_and_hides_product(self, world):
        world.catalog.get_product("nb")
        world.catalog.delete("nb")
        assert not world.cache.contains("nb")
        with pytest.raises(NotFoundError):
            world.catalog.get_product("nb")

    def test_delete_is_soft(self, world):
        world.catalog.delete("nb")
        assert world.products.get_by_id("nb").active is False

    def test_delete_unknown_product_raises(self, world):
        with pytest.raises(NotFoundError):
            world.catalog.delete("nope")
