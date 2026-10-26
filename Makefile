.PHONY: up down clients clients-down mongosh redis-cli cypher-shell seed test test-unit test-acceptance wait-api run-fake

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

# Si la API corre en Docker, la reinicia con CACHE_MISS_DELAY_SECONDS=0 para que
# los tests no esperen 5 s por cada MISS, y al terminar la deja como estaba.
test-acceptance:  ## Escenarios 01-07 contra la API corriendo (sin el retardo del MISS)
	@if [ -n "$$(docker compose ps -q --status running app 2>/dev/null)" ]; then \
		CACHE_MISS_DELAY_SECONDS=0 docker compose up -d app && $(MAKE) --no-print-directory wait-api; \
		uv run pytest tests/acceptance -m acceptance; status=$$?; \
		docker compose up -d app && $(MAKE) --no-print-directory wait-api; \
		exit $$status; \
	else \
		uv run pytest tests/acceptance -m acceptance; \
	fi

wait-api:
	@for i in $$(seq 1 30); do curl -fs http://localhost:8000/health >/dev/null && exit 0; sleep 1; done; \
		echo "La API no respondió en http://localhost:8000/health" >&2; exit 1

test: test-unit test-acceptance
