#!/usr/bin/env bash
set -euo pipefail

# Ajoute l'env packé au PATH (béton)
export PATH="/opt/conda-env/bin:${PATH}"

echo "Starting Odyssai Core (Flask WSGI)…"
echo "PORT=${PORT:-9000}"
echo "whoami=$(whoami) pwd=$(pwd)"
echo "PATH=$PATH"
/opt/conda-env/bin/python -V || true
command -v /opt/conda-env/bin/gunicorn || true

# Params
: "${PORT:=9000}"
: "${WEB_THREADS:=4}"
: "${WEB_TIMEOUT:=180}"
# ⚠️ Mets le bon module Flask :
: "${APP_MODULE:=src.odyssai_core.app:app}"   # module:path_to_flask_app
: "${GUNICORN_CONF:=gunicorn.conf.py}"

# Lancement
exec /opt/conda-env/bin/gunicorn "${APP_MODULE}" \
  -c "${GUNICORN_CONF}" \
  --worker-class gthread \
  --threads "${WEB_THREADS}" \
  --timeout "${WEB_TIMEOUT}" \
  --bind "0.0.0.0:${PORT}"