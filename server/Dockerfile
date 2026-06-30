FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Cache dependency installation
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy source and sync the project
COPY src ./src
COPY resources ./resources
RUN uv sync --frozen --no-dev

# Final slim runtime image
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Copy the built virtual environment from the builder
COPY --from=builder /app/.venv /app/.venv

# Copy the application code
COPY src ./src
COPY resources ./resources

# Add the virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
