#!/usr/bin/env bash
set -euo pipefail

echo "Starting Odyssai Core..."
echo "PORT=${PORT:-9000} ODYSSAI_APP_TYPE=${ODYSSAI_APP_TYPE:-WSGI}"

# Diagnostics
echo "whoami=$(whoami) pwd=$(pwd)"
echo "PATH=$PATH"
command -v python || true
python -V || true
command -v gunicorn || true

# Par défaut on part sur WSGI (Flask) vu ton import '...app:app'
: "${PORT:=9000}"
: "${WEB_THREADS:=4}"
: "${WEB_TIMEOUT:=180}"
: "${APP_MODULE:=src.odyssai_core.app:app}"   # Flask WSGI
: "${GUNICORN_CONF:=gunicorn.conf.py}"

# Lancement
exec gunicorn "${APP_MODULE}" \
  -c "${GUNICORN_CONF}" \
  --worker-class gthread \
  --threads "${WEB_THREADS}" \
  --timeout "${WEB_TIMEOUT}" \
  --bind "0.0.0.0:${PORT}"