ARG PYTHON_BASE_IMAGE=python:3.12-slim@sha256:dd29372629eeba2dd003fd9e9d35a5b8236c44727875a0364254b5127af88e65

FROM ${PYTHON_BASE_IMAGE} AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv "$VIRTUAL_ENV"
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip check

FROM ${PYTHON_BASE_IMAGE} AS runtime

ARG APP_UID=10001
ARG APP_GID=10001

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid "$APP_GID" lumina \
    && useradd --uid "$APP_UID" --gid "$APP_GID" --no-create-home \
       --shell /usr/sbin/nologin lumina

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
RUN mkdir -p /app/.lumina_conversations /app/runtime-logs/debug /app/logs \
    && chown -R "$APP_UID:$APP_GID" \
       /app/.lumina_conversations /app/runtime-logs /app/logs

COPY --chown=10001:10001 main.py config.py database.py ./
COPY --chown=10001:10001 contracts ./contracts
COPY --chown=10001:10001 database ./database
COPY --chown=10001:10001 models ./models
COPY --chown=10001:10001 routers ./routers
COPY --chown=10001:10001 schemas ./schemas
COPY --chown=10001:10001 services ./services
COPY --chown=10001:10001 testing/__init__.py testing/database_guard.py ./testing/

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD ["curl", "--fail", "--silent", "--show-error", "http://127.0.0.1:8000/health"]

CMD ["gunicorn", "main:app", "-k", "uvicorn.workers.UvicornWorker", "--workers", "4", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-"]
