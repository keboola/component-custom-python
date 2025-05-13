FROM quay.io/keboola/docker-custom-python:latest
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# RUN apt-get update && apt-get install -y build-essential

WORKDIR /code/

COPY pyproject.toml .
COPY uv.lock .

# Unset VIRTUAL_ENV variable from parent image as it messes up with uv
ENV VIRTUAL_ENV=

# Set UV_CACHE_DIR to override XDG_CACHE_HOME from parent image
# See https://docs.astral.sh/uv/concepts/cache/#cache-directory
ENV UV_CACHE_DIR="/.cache/uv"

# Keboola running containers with "-u 1000:1000" causes permission problems with uv's venvs
# Using the system Python environment as a workaround until we find a better way
ENV UV_PROJECT_ENVIRONMENT="/usr/local/"

RUN uv sync --all-groups --frozen
RUN chown -R 1000:1000 /.cache
RUN chown -R 1000:1000 /code/pyproject.toml

COPY src/ src/
COPY tests/ tests/
COPY scripts/ scripts/
COPY flake8.cfg .
COPY deploy.sh .

CMD ["python", "/code/src/component.py"]
# CMD ["/bin/bash"]
