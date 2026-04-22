#!/bin/sh
set -eu

echo "Applying database migrations..."
if ! python manage.py migrate; then
  cat <<'EOF'

Database startup failed.
If the error above mentions "password authentication failed" or "role ... does not exist",
the Postgres volume was likely initialized earlier with different DB_* values.

To fix a disposable local database:
  docker compose down -v
  docker compose up --build

If you need to keep the existing data, restore the previous DB_NAME/DB_USER/DB_PASS
values or create the missing role and database inside the existing Postgres volume.
EOF
  exit 1
fi

python manage.py ensure_superuser
python manage.py runserver 0.0.0.0:8000
