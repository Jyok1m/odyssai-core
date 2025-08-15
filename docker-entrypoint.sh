#!/usr/bin/env sh
set -e

# Dossier sécurisé pour le secret
mkdir -p /secrets
chmod 700 /secrets

# Option base64 (GCP_TTS_JSON_B64)
if [ -n "$GCP_TTS_JSON_B64" ]; then
  echo "$GCP_TTS_JSON_B64" | base64 -d > /secrets/google_tts.json
  chmod 600 /secrets/google_tts.json
  export GOOGLE_APPLICATION_CREDENTIALS="/secrets/google_tts.json"
fi

# Option brute (GCP_TTS_JSON) si tu ne veux pas de base64
if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ -n "$GCP_TTS_JSON" ]; then
  echo "$GCP_TTS_JSON" > /secrets/google_tts.json
  chmod 600 /secrets/google_tts.json
  export GOOGLE_APPLICATION_CREDENTIALS="/secrets/google_tts.json"
fi

exec "$@"
