FROM quay.io/keboola/docker-custom-python:latest
ENV PYTHONIOENCODING utf-8



# Create directory for user packages
# This directory is usually created automatically by pip
# ... but if it doesn't exist when you run the script
# ... then the modules installed during the transformation are not loaded automatically!
# ... because the loader thinks that this directory does not exist (it did not exist at the start of the script)
# Eg. mkdir -p /var/www/.local/lib/python3.8/site-packages
RUN . "$VIRTUAL_ENV/bin/activate" && mkdir -p $(su www-data -s /bin/bash -c "python -c 'import site; print(site.USER_SITE)'")

# Make home directory writable
RUN chown -R www-data:www-data /var/www

COPY /src /code/src/
COPY /tests /code/tests/
COPY /scripts /code/scripts/
COPY requirements.txt /code/requirements.txt
COPY requirements-tests.txt /code/requirements-tests.txt
COPY flake8.cfg /code/flake8.cfg
COPY deploy.sh /code/deploy.sh

# install gcc to be able to build packages - e.g. required by regex, dateparser, also required for pandas
RUN apt-get update && apt-get install -y build-essential

RUN . "$VIRTUAL_ENV/bin/activate" && pip freeze

RUN . "$VIRTUAL_ENV/bin/activate" && pip install -r /code/requirements-tests.txt

RUN . "$VIRTUAL_ENV/bin/activate" && pip install -r /code/requirements.txt

WORKDIR /code/

RUN . "$VIRTUAL_ENV/bin/activate" && pip freeze
CMD . "$VIRTUAL_ENV/bin/activate" && python -u /code/src/component.py
