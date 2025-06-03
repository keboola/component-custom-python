FROM quay.io/keboola/docker-custom-python:latest
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# RUN apt-get update && apt-get install -y build-essential

# Create user to correctly set the $HOME env variable (used by certain packages, eg. stanza, for caching data)
ARG USERNAME=keboola
RUN adduser --uid 1000 --disabled-password ${USERNAME}

# Set UV_CACHE_DIR to override XDG_CACHE_HOME from the base image
# See https://docs.astral.sh/uv/concepts/cache/#cache-directory
RUN mkdir -p /.cache/uv
RUN chown -R 1000:1000 /.cache
ENV UV_CACHE_DIR="/.cache/uv"

# Using the same path as venv defined in the base image so we can use all the preinstalled packages
ENV UV_PROJECT_ENVIRONMENT="/home/default/"

# Run uv sync as uid/gid 1000 so we don't have to chown the /home/default directory with 100k files =-O
USER 1000:1000

# Add Github SSH host key to known_hosts file
RUN mkdir /home/${USERNAME}/.ssh
COPY .ssh/known_hosts /home/${USERNAME}/.ssh/known_hosts

WORKDIR /code/
COPY pyproject.toml .
COPY uv.lock .

# The --inexact flag prevents uv from uninstalling the preinstalled packages
RUN uv sync --all-groups --frozen --inexact

# Keboola running containers with "-u 1000:1000" causes permission issues when installing user defined packages
# so we need to chown the files to 1000:1000
USER root
RUN chown 1000:1000 pyproject.toml
RUN chown 1000:1000 uv.lock

COPY src/ src/
COPY tests/ tests/
COPY scripts/ scripts/
COPY flake8.cfg .
COPY deploy.sh .

RUN chown -R 1000:1000 *

CMD ["uv", "run", "python", "src/component.py"]
