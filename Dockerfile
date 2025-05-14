FROM quay.io/keboola/docker-custom-python:latest
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# RUN apt-get update && apt-get install -y build-essential

WORKDIR /code/

COPY pyproject.toml .
COPY uv.lock .

# Set UV_CACHE_DIR to override XDG_CACHE_HOME from the base image
# See https://docs.astral.sh/uv/concepts/cache/#cache-directory
ENV UV_CACHE_DIR="/.cache/uv"

# Using the same path as venv defined in the base image so we can use all the preinstalled packages
ENV UV_PROJECT_ENVIRONMENT="/home/default/"

# The --inexact flag prevents uv from uninstalling the preinstalled packages
RUN uv sync --all-groups --frozen --inexact

# Keboola running containers with "-u 1000:1000" causes permission when installing user defined packages
RUN chown -R 1000:1000 /.cache
RUN chown -R 1000:1000 /code/pyproject.toml
RUN chown -R 1000:1000 /code/uv.lock

COPY src/ src/
COPY tests/ tests/
COPY scripts/ scripts/
COPY flake8.cfg .
COPY deploy.sh .

CMD ["uv", "run", "python", "src/component.py"]
