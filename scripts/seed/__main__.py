"""Seed: BORRA y vuelve a cargar MongoDB, Redis y Neo4j.   python -m scripts.seed

PROVISTO. El borrado usa los clientes crudos (no los puertos); la CARGA usa los puertos,
así que falla con NotImplementedError hasta que implementen los adaptadores
de Mongo (productos, clientes, órdenes) y de las relaciones de compra (PurchaseRelationsAdapter).
"""

from app.catalog.adapters.mongo_product_repository import MongoProductRepository
from app.config import Settings
from app.customers.adapters.mongo_customer_repository import MongoCustomerRepository
from app.infrastructure.connections import Connections
from app.orders.adapters.mongo_order_repository import MongoOrderRepository
from app.orders.adapters.purchase_relations import PurchaseRelationsAdapter
from app.seeding import load_dataset


def main() -> None:
    conns = Connections.open(Settings())
    try:
        print("Borrando datos previos...")
        conns.mongo_client.drop_database(conns.mongo.name)
        conns.redis.flushdb()
        with conns.neo4j.session() as session:
            session.run("MATCH (n) DETACH DELETE n").consume()

        print("Cargando dataset a través de los puertos...")
        load_dataset(
            products=MongoProductRepository(conns.mongo),
            customers=MongoCustomerRepository(conns.mongo),
            orders=MongoOrderRepository(conns.mongo),
            relations=PurchaseRelationsAdapter(conns),
        )
        print("Listo.")
    finally:
        conns.close()


if __name__ == "__main__":
    main()
