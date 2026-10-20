.PHONY: up down clients clients-down mongosh redis-cli cypher-shell seed test test-unit test-acceptance run-fake

up:               ## Levanta MongoDB, Redis, Neo4j y la API
	docker compose up --build -d

down:             ## Baja todo, incluidos los clientes (agregá -v a mano para borrar los volúmenes)
	docker compose --profile clients down

clients:          ## Levanta mongo-express (:8081) y RedisInsight (:5540)
	docker compose --profile clients up -d mongo-express redisinsight

clients-down:     ## Baja solo los clientes web (las bases siguen corriendo)
	docker compose --profile clients rm -sf mongo-express redisinsight

mongosh:          ## Consola de MongoDB sobre la base del TP
	docker compose exec mongo mongosh $${MONGO_DB:-nexus}

redis-cli:        ## Consola de Redis
	docker compose exec redis redis-cli

cypher-shell:     ## Consola de Neo4j (usuario neo4j, clave tomada del contenedor)
	docker compose exec neo4j sh -c 'cypher-shell -u neo4j -p "$${NEO4J_AUTH#neo4j/}"'

seed:             ## Carga el dataset en los tres motores (requiere adapters implementados)
	docker compose exec app python -m scripts.seed

run-fake:         ## API en memoria, sin Docker
	ADAPTERS=fake uv run uvicorn app.main:app --reload

test-unit:        ## Flujos de servicio con fakes (no necesita Docker)
	uv run pytest tests/unit

test-acceptance:  ## Escenarios 01-07 contra la API corriendo
	uv run pytest tests/acceptance -m acceptance

test: test-unit test-acceptance
