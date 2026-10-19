.PHONY: up down seed test test-unit test-acceptance run-fake

up:               ## Levanta MongoDB, Redis, Neo4j y la API
	docker compose up --build -d

down:             ## Baja todo (agregá -v a mano para borrar los volúmenes)
	docker compose down

seed:             ## Carga el dataset en los tres motores (requiere adapters implementados)
	docker compose exec app python -m scripts.seed

run-fake:         ## API en memoria, sin Docker
	ADAPTERS=fake uv run uvicorn app.main:app --reload

test-unit:        ## Flujos de servicio con fakes (no necesita Docker)
	uv run pytest tests/unit

test-acceptance:  ## Escenarios 01-07 contra la API corriendo
	uv run pytest tests/acceptance -m acceptance

test: test-unit test-acceptance
