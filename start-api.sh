#!/bin/sh
set -eu
echo "Running Alembic migrations..." >&2
if ! alembic upgrade head; then
  echo "Alembic upgrade failed; refusing to start the API." >&2
  exit 1
fi
echo "Alembic migrations complete." >&2
exec uvicorn tal.main:app --host 0.0.0.0 --port 8000
