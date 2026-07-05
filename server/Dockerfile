FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Cache dependency installation
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy source
COPY src ./src
COPY resources ./resources

# Final slim runtime image
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    UNMESSIT_DOCKER=1
WORKDIR /app

# Copy the built virtual environment from the builder
COPY --from=builder /app/.venv /app/.venv

# Copy the application code
COPY src ./src
COPY resources ./resources

# Add the virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 2317
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "2317"]
