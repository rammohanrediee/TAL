#!/bin/sh
set -eu

run_migrations() {
  echo "Running Alembic migrations (uses DATABASE_URL_UNPOOLED when set)..." >&2
  if command -v timeout >/dev/null 2>&1; then
    if ! timeout "${ALEMBIC_TIMEOUT_SEC:-120}" alembic upgrade head; then
      echo "Alembic upgrade failed or timed out after ${ALEMBIC_TIMEOUT_SEC:-120}s." >&2
      return 1
    fi
  elif ! alembic upgrade head; then
    echo "Alembic upgrade failed." >&2
    return 1
  fi
  echo "Alembic migrations complete." >&2
  return 0
}

case "${MIGRATE_ON_START:-false}" in
  true|1|yes)
    if ! run_migrations; then
      echo "Refusing to start the API until migrations succeed." >&2
      exit 1
    fi
    ;;
  *)
    echo "Skipping startup migrations (MIGRATE_ON_START is not true). Apply schema on deploy via CI." >&2
    ;;
esac

exec uvicorn tal.main:app --host 0.0.0.0 --port 8000