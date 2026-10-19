FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.25 /uv /usr/local/bin/uv

# El entorno virtual vive fuera de /app para que el bind mount de compose no lo tape.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-install-project

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
