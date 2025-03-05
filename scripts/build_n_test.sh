#!/bin/sh
set -e

uv run --active flake8 --config=flake8.cfg
uv run --active python -m unittest discover