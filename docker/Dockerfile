FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONFAULTHANDLER=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

RUN useradd --create-home --shell /bin/bash agent

# Copy dependency files from project root
COPY pyproject.toml uv.lock /app/

# Install dependencies (skip installing the project itself for now)
RUN uv sync --frozen --no-install-project --no-dev

# Copy application code from project root
COPY . /app/

# Now install the project itself
RUN uv sync --frozen --no-dev

RUN chown -R agent:agent /app

USER agent
