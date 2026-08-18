# Base image for the RoveQA backend (api and worker share this package).
# Real entrypoints (uvicorn api / temporal worker) are wired in Phase 02.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-install-project --no-dev

COPY src ./src
RUN uv sync --frozen --no-dev

# Placeholder command proving the package is importable; replaced in Phase 02.
CMD ["uv", "run", "--no-dev", "python", "-c", "import agentic_qa; print(f'agentic_qa {agentic_qa.__version__} image OK')"]
