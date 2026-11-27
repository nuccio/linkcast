FROM python:3.13-slim

RUN pip install --no-cache-dir uv==0.11.17

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src ./src
ENV PYTHONPATH=/app/src

RUN useradd --system --no-create-home linkcast
USER linkcast

# Cloud Run sets PORT. The service refuses to start without a valid FEED_TOKEN.
# No access log: it would contain the token (the service writes its own log).
CMD exec gunicorn --bind "0.0.0.0:${PORT:-8080}" --workers 1 --threads 4 --timeout 120 "linkcast.app:create_app()"
