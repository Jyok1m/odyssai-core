#!/bin/bash
set -e

echo "Starting Odyssai Core..."
echo "Environment variables:"
echo "PORT: $PORT"
echo "BACKEND_PORT: $BACKEND_PORT"
echo "PYTHONPATH: $PYTHONPATH"

echo "Testing Python import..."
conda run --no-capture-output -n odyssai python -c "from src.odyssai_core.app import app; print('Flask app imported successfully')"

echo "Starting Gunicorn..."
exec conda run --no-capture-output -n odyssai gunicorn -c gunicorn.conf.py --bind 0.0.0.0:${PORT:-9000} src.odyssai_core.app:app
