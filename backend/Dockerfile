# RoveQA backend image (api and worker share this package).
#
# The virtualenv lives outside /app so a bind mount of the source during development
# cannot shadow it: the dev stage mounts ./backend over /app and still finds its
# dependencies.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS base

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml uv.lock .python-version ./


FROM base AS runtime
RUN uv sync --frozen --no-install-project --no-dev
COPY src ./src
RUN uv sync --frozen --no-dev

CMD ["python", "-c", "import agentic_qa; print(f'agentic_qa {agentic_qa.__version__} image OK')"]


# Worker stage: the runtime plus a real Chromium.
#
# Only the worker drives a browser, so the API image stays free of ~400MB of browser
# and system libraries it would never open.
FROM runtime AS worker
RUN playwright install --with-deps chromium

CMD ["python", "-m", "agentic_qa.infrastructure.workflows.temporal.worker"]


# Development/test stage: dev dependencies plus a real Chromium.
#
# Running the suite here rather than on the host is what removes the Windows-only
# event-loop conflict (psycopg needs a selector loop, Playwright needs a proactor
# one): on Linux a single default loop serves both.
FROM base AS dev
RUN uv sync --frozen --no-install-project
RUN playwright install --with-deps chromium

COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic
RUN uv sync --frozen

CMD ["pytest"]
