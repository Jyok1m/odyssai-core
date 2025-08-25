# ---- Stage 1: build conda env (conserve ton début) ----
FROM mambaorg/micromamba:1.5.8 AS conda-builder

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

# ---- 3bis. Installer conda-pack et packer l'env ----
RUN micromamba install -y -n odyssai -c conda-forge conda-pack && \
    micromamba run -n odyssai conda-pack -n odyssai \
      -o /tmp/conda_env.tar.gz --ignore-editable-packages

# =====================================================================

# ---- Stage 2: runtime ultra-mince (image finale) ----
FROM python:3.12-slim AS runtime
SHELL ["/bin/bash", "-lc"]
WORKDIR /app

# ---- 6. Variables d'env (conservées + HF cache volume-friendly) ----
ENV PYTHONPATH=/app/src \
    BACKEND_PORT=9000 \
    PORT=9000 \
    HF_HOME=/data/hf/.cache/huggingface \
    TRANSFORMERS_CACHE=/data/hf/.cache/huggingface \
    PATH="/opt/conda-env/bin:$PATH"

# Déps runtime minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg libsndfile1 libportaudio2 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ---- Déployer l'environnement conda packé ----
COPY --from=conda-builder /tmp/conda_env.tar.gz /tmp/conda_env.tar.gz
RUN mkdir -p /opt/conda-env \
 && tar -xzf /tmp/conda_env.tar.gz -C /opt/conda-env \
 && rm /tmp/conda_env.tar.gz

# ---- 4. Copier les scripts runtime avec bons droits (inchangé) ----
COPY --chmod=0755 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY --chmod=0755 start.sh /usr/local/bin/start.sh

# ---- 5. Copier le reste du code ----
# (on reste root ici; si tu veux un user non-root, on l'ajoute, mais garde l'accès au volume)
COPY . .

EXPOSE 9000

# ---- 7. Commande de démarrage (conserve ton start.sh) ----
# (micromamba n'est plus nécessaire : le PATH pointe sur /opt/conda-env/bin)
CMD ["bash", "-lc", "/usr/local/bin/start.sh"]