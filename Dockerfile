FROM quay.io/keboola/docker-custom-python:latest

# install gcc to be able to build packages - e.g. required by regex, dateparser, also required for pandas
# RUN apt-get update && apt-get install -y build-essential

RUN pip install uv

# COPY requirements.txt /code/requirements.txt
# COPY requirements-tests.txt /code/requirements-tests.txt
COPY pyproject.toml /code/pyproject.toml

WORKDIR /code/
RUN uv sync

COPY /src /code/src/
COPY /tests /code/tests/
COPY /scripts /code/scripts/
COPY flake8.cfg /code/flake8.cfg
COPY deploy.sh /code/deploy.sh

CMD uv run /code/src/component.py
