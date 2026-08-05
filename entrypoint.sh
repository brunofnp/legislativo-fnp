#!/bin/sh
set -e

python manage.py migrate --no-input
python manage.py collectstatic --no-input

exec gunicorn setup.wsgi:application --bind 0.0.0.0:8004 \
    --workers 3 --worker-class gthread --threads 4 --timeout 660
