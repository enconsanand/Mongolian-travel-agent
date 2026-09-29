FROM python:3.14-slim-bookworm AS base

COPY --from=ghcr.io/astral-sh/uv:0.11.1 /uv /bin/uv

ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  UV_COMPILE_BYTECODE=1 \
  UV_LINK_MODE=copy \
  UV_PYTHON_DOWNLOADS=never \
  TZ=${TIMEZONE:-UTC} \
  PATH="/app/.venv/bin:$PATH"

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

# Create non-root user
RUN groupadd --system --gid 1001 appgroup && \
  useradd --system --uid 1001 --gid appgroup --create-home --home-dir /app appuser

COPY ./back/uv.lock ./back/pyproject.toml ./

RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen && \
  chown -R appuser:appgroup /app

USER appuser

# Development target (for volume mounts)
FROM base AS dev
USER root

# Production target (secure)
FROM base AS prod
USER appuser
COPY --chown=appuser:appgroup ./back ./
