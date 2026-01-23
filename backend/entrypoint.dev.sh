#!/bin/sh

if [ "$DJANGO_SUPERUSER_PASSWORD" != "" ]; then
    echo "Creating superuser..." # TODO: Remove once it's confirmed that celery doesn't run this
    python manage.py migrate --noinput
    # python manage.py loaddata ... TODO: source from model_bakery?
    python manage.py createsuperuser --username admin --email admin@example.com --noinput
fi

exec "$@"