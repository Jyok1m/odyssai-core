# Image base légère avec conda: micromamba
FROM mambaorg/micromamba:1.5.8

SHELL ["/bin/bash", "-lc"]
WORKDIR /app

# Déps système minimales (audio + ffmpeg)
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg libsndfile1 libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

# ---- 1) Déclarer les manifestes AVANT le code (meilleur cache) ----
COPY environment-export.yml /tmp/environment.yml
COPY requirements.txt /tmp/requirements.txt

# ---- 2) Créer l'environnement conda "odyssai" ----
# - Aucun paquet dans "base"
# - Nettoyage agressif des caches
RUN micromamba create -y -n odyssai -f /tmp/environment.yml -c conda-forge && \
    micromamba clean --all --yes && \
    rm -rf /opt/conda/pkgs /root/.cache /home/mambauser/.cache

# ---- 3) Installer les deps pip DANS l'env "odyssai" ----
RUN micromamba run -n odyssai python -m pip install --no-cache-dir -r /tmp/requirements.txt && \
    micromamba clean --all --yes && \
    rm -rf /opt/conda/pkgs /root/.cache /home/mambauser/.cache

# ---- 4) Copier les scripts runtime (petits) ----
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh /usr/local/bin/start.sh

# ---- 5) Copier le reste du code en dernier ----
# (évite d’invalider les couches d’env à chaque commit)
COPY . .

# ---- 6) Env & runtime ----
ENV PYTHONPATH=/app/src \
    BACKEND_PORT=9000 \
    PORT=9000 \
    HF_HOME=/data/hf  # cache modèles HF hors image (volume)

EXPOSE 9000

# Meilleur UID non-root déjà présent: mambauser
USER mambauser

# Si ton entrypoint ne dépend PAS de "conda run", laisse-le.
# Sinon, appelle start.sh via micromamba run (recommandé):
# ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["bash","-lc","micromamba run -n odyssai /usr/local/bin/start.sh"]