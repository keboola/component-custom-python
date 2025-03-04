#!/bin/sh
set -e

uv run flake8 --config=flake8.cfg
uv run python -m unittest discover