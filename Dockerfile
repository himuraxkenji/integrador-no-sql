# syntax=docker/dockerfile:1

# --- Etapa 1: build. Acá vive uv y se arma el entorno virtual. ---
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.25 /uv /usr/local/bin/uv

# UV_COMPILE_BYTECODE: precompila .pyc para que la app arranque más rápido.
# UV_LINK_MODE=copy: el caché es un mount, así que los archivos se copian al venv.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app
COPY pyproject.toml uv.lock ./

# El caché de uv va en un mount: se reutiliza entre builds pero no queda en la imagen.
# --no-dev: pytest/httpx no se necesitan en el contenedor (los tests corren desde el host).
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# --- Etapa 2: runtime. Solo Python, el venv y el código: ni uv ni caché. ---
FROM python:3.12-slim

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY app ./app
COPY scripts ./scripts
COPY datasets ./datasets

RUN useradd --create-home nexus
USER nexus

EXPOSE 8000
# Sin --reload: en desarrollo lo agrega compose.yaml junto al bind mount.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
