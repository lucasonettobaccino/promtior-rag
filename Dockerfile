# ---- Builder stage ----
FROM python:3.13-slim AS builder

ENV POETRY_VERSION=2.3.4 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry

WORKDIR /build

COPY pyproject.toml poetry.lock ./

RUN poetry self add poetry-plugin-export \
    && poetry export \
        --format=requirements.txt \
        --output=requirements.txt \
        --without-hashes


# ---- Runtime stage ----
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app --no-create-home app

WORKDIR /app

COPY --from=builder /build/requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app src ./src
COPY --chown=app:app pyproject.toml ./
COPY --chown=app:app README.md ./
COPY --chown=app:app data/vector_store ./data/vector_store
COPY --chown=app:app data/AI_Engineer.pdf ./data/AI_Engineer.pdf

RUN pip install --no-cache-dir --no-deps -e .

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl --fail http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "promtior_rag.api.server:app", "--host", "0.0.0.0", "--port", "8000"]