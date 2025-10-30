#!/bin/sh

python manage.py migrate --noinput
# python manage.py loaddata ... TODO: source from model_bakery?
python manage.py createsuperuser --username admin --email admin@example.com --noinput

exec "$@"