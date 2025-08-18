#!/bin/bash
set -Eeuo pipefail

echo "Starting Odyssai Core..."
echo "PORT=${PORT:-9000} ODYSSAI_APP_TYPE=${ODYSSAI_APP_TYPE:-ASGI}"

# (Optionnel) Détection rapide pour afficher le type
conda run --no-capture-output -n odyssai python - <<'PY'
from src.odyssai_core.app import app
print("App imported OK.")
PY

# Lancer avec la conf unique
exec conda run --no-capture-output -n odyssai gunicorn \
  -c gunicorn.conf.py \
  src.odyssai_core.app:app
