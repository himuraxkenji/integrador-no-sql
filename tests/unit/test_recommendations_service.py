from app.orders.domain import Order, OrderItem


def buy(world, customer, *product_ids):
    """Registra compras directo en el fake de relaciones, para probar SOLO recomendaciones."""
    items = [OrderItem(product_id=p, quantity=1, unit_price=1) for p in product_ids]
    world.relations.record_purchase(Order(id="o", customer_id=customer, items=items, total=len(items)))


class TestRecommend:
    def test_recommends_what_similar_customers_bought(self, world):
        buy(world, "ana", "nb", "ms")
        buy(world, "luis", "nb", "kb")
        ids = [r.product.id for r in world.recommendations.recommend("ana")]
        assert "kb" in ids

    def test_excludes_products_already_bought(self, world):
        buy(world, "ana", "nb", "ms")
        buy(world, "luis", "nb", "ms", "kb")
        ids = [r.product.id for r in world.recommendations.recommend("ana")]
        assert "nb" not in ids and "ms" not in ids

    def test_enriches_with_mongo_details(self, world):
        buy(world, "ana", "nb")
        buy(world, "luis", "nb", "kb")
        rec = next(r for r in world.recommendations.recommend("ana") if r.product.id == "kb")
        assert rec.product.name == "Teclado"
        assert rec.product.price == 80
        assert rec.reason == "also_bought"

    def test_drops_inactive_products(self, world):
        buy(world, "ana", "nb")
        buy(world, "luis", "nb", "kb")
        world.products.soft_delete("kb")
        ids = [r.product.id for r in world.recommendations.recommend("ana")]
        assert "kb" not in ids

    def test_respects_finder_order(self, world):
        buy(world, "ana", "nb")
        buy(world, "luis", "nb", "kb")
        scores = [r.score for r in world.recommendations.recommend("ana")]
        assert scores == sorted(scores, reverse=True)
