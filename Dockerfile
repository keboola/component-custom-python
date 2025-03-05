FROM quay.io/keboola/docker-custom-python:latest

# install gcc to be able to build packages - e.g. required by regex, dateparser, also required for pandas
# RUN apt-get update && apt-get install -y build-essential

RUN pip install uv

WORKDIR /code/

COPY pyproject.toml .
COPY uv.lock .

RUN uv pip sync --system pyproject.toml

COPY src/ src/
COPY tests/ tests/
COPY scripts/ scripts/
COPY flake8.cfg .
COPY deploy.sh .

CMD uv run --active /code/src/component.py
