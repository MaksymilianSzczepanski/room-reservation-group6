#!/bin/sh
set -eu
python -m microservices.bootstrap
python microservices/manage.py migrate --run-syncdb --noinput
if [ "$SERVICE_NAME" = "users" ]; then
  python microservices/manage.py ensure_admin
fi
python -m microservices.register
exec python microservices/manage.py runserver 0.0.0.0:8000
