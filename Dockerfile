FROM quay.io/keboola/docker-custom-python:latest
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# RUN apt-get update && apt-get install -y build-essential

WORKDIR /code/

COPY pyproject.toml .
COPY uv.lock .

# unset VIRTUAL_ENV variable from parent image as it messes up with uv
ENV VIRTUAL_ENV=
ENV UV_PROJECT_ENVIRONMENT="/usr/local/"
RUN uv sync --all-groups --frozen

COPY src/ src/
COPY tests/ tests/
COPY scripts/ scripts/
COPY flake8.cfg .
COPY deploy.sh .

CMD ["python", "/code/src/component.py"]
