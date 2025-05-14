FROM quay.io/keboola/docker-custom-python:latest
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# RUN apt-get update && apt-get install -y build-essential

# Set UV_CACHE_DIR to override XDG_CACHE_HOME from the base image
# See https://docs.astral.sh/uv/concepts/cache/#cache-directory
RUN mkdir -p /.cache/uv
RUN chown -R 1000:1000 /.cache
ENV UV_CACHE_DIR="/.cache/uv"

# Using the same path as venv defined in the base image so we can use all the preinstalled packages
ENV UV_PROJECT_ENVIRONMENT="/home/default/"

WORKDIR /code/
COPY pyproject.toml .
COPY uv.lock .

# Run uv sync as uid/gid 1000 so we don't have to chown the /home/default directory with 100k files =-O
USER 1000:1000
# The --inexact flag prevents uv from uninstalling the preinstalled packages
RUN uv sync --all-groups --frozen --inexact

# Keboola running containers with "-u 1000:1000" causes permission when installing user defined packages
USER root
RUN chown 1000:1000 /code/pyproject.toml
RUN chown 1000:1000 /code/uv.lock

COPY src/ src/
COPY tests/ tests/
COPY scripts/ scripts/
COPY flake8.cfg .
COPY deploy.sh .

CMD ["uv", "run", "python", "src/component.py"]
