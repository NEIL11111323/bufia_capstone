#!/usr/bin/env bash

set -o errexit
set -o nounset

echo "==> Installing Python dependencies"
python -m pip install -r requirements.txt

echo "==> Collecting static files"
python manage.py collectstatic --no-input
