FROM python:3.12.9-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONFAULTHANDLER=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=off
ENV PIP_DISABLE_PIP_VERSION_CHECK=on
ENV PIP_DEFAULT_TIMEOUT=100
ENV POETRY_VERSION=2.1.1

WORKDIR /app

RUN apt -y update && apt-get clean
RUN pip install "poetry==$POETRY_VERSION"

RUN useradd --create-home --shell /bin/bash agent

COPY ./poetry.lock ./pyproject.toml /app/
RUN POETRY_VIRTUALENVS_CREATE=false poetry install --no-interaction

COPY . .

RUN chown -R agent:agent /app

USER agent
