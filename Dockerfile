FROM mambaorg/micromamba:1.5.8

SHELL ["/bin/bash", "-lc"]
WORKDIR /app

# ---- 1. Dépendances système ----
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg libsndfile1 libportaudio2 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ---- 2. Installer les deps conda ----
COPY environment-export.yml /tmp/environment.yml
COPY requirements.txt /tmp/requirements.txt

RUN micromamba create -y -n odyssai -f /tmp/environment.yml -c conda-forge && \
    micromamba clean --all --yes && \
    rm -rf /opt/conda/pkgs /home/mambauser/.cache

# ---- 3. Installer les deps pip ----
RUN micromamba run -n odyssai python -m pip install --no-cache-dir -r /tmp/requirements.txt && \
    micromamba clean --all --yes && \
    rm -rf /opt/conda/pkgs /home/mambauser/.cache

# ---- 4. Copier les scripts runtime avec bons droits ----
COPY --chmod=0755 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY --chmod=0755 start.sh /usr/local/bin/start.sh

# ---- 5. Copier le reste du code ----
USER mambauser
COPY . .

# ---- 6. Variables d'env ----
ENV PYTHONPATH=/app/src \
    BACKEND_PORT=9000 \
    PORT=9000 \
    HF_HOME=/data/hf

EXPOSE 9000

# ---- 7. Commande de démarrage ----
CMD ["bash", "-lc", "micromamba run -n odyssai /usr/local/bin/start.sh"]
