#!/bin/sh
# ─────────────────────────────────────────────────────────────
# Container entrypoint.
#
# Order matters:
#   1. Wait for Postgres (compose's depends_on healthcheck already does
#      this, but we re-check defensively in case someone runs without it).
#   2. Apply migrations — fast no-op on subsequent boots.
#   3. Seed reference data ONLY if tables are empty (--if-empty).
#   4. Collect static files (admin, drf-spectacular UI).
#   5. Hand off to gunicorn via exec so it becomes PID 1 and receives
#      SIGTERM directly (graceful shutdown).
# ─────────────────────────────────────────────────────────────
set -e

echo "[entrypoint] Waiting for database at ${DB_HOST}:${DB_PORT}..."
python -c "
import os, socket, time, sys
host, port = os.environ['DB_HOST'], int(os.environ['DB_PORT'])
for i in range(60):
    try:
        with socket.create_connection((host, port), timeout=2):
            print(f'[entrypoint] DB reachable after {i}s'); sys.exit(0)
    except OSError:
        time.sleep(1)
print('[entrypoint] DB never came up'); sys.exit(1)
"

echo "[entrypoint] Generating any missing migrations from models.py..."
# No-op when models.py matches the committed migrations.
# When a dev edits models.py, this generates the new migration file
# inside the bind-mounted /app, so it lands on the host filesystem
# ready to be committed to git.
python manage.py makemigrations --noinput

echo "[entrypoint] Applying migrations..."
python manage.py migrate --noinput

echo "[entrypoint] Seeding reference data (skips if already populated)..."
python manage.py import_seed_data --if-empty

echo "[entrypoint] Collecting static files..."
python manage.py collectstatic --noinput

echo "[entrypoint] Starting gunicorn on 0.0.0.0:${PORT:-8000}"
exec gunicorn DjangoProject.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${GUNICORN_WORKERS:-3}" \
    --threads "${GUNICORN_THREADS:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-30}" \
    --access-logfile - \
    --error-logfile -
