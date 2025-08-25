FROM mambaorg/micromamba:1.5.8

SHELL ["/bin/bash", "-lc"]
WORKDIR /app

# Passe root le temps d’installer les paquets système
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg libsndfile1 libportaudio2 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# (suite identique)
COPY environment-export.yml /tmp/environment.yml
COPY requirements.txt /tmp/requirements.txt

RUN micromamba create -y -n odyssai -f /tmp/environment.yml -c conda-forge && \
    micromamba clean --all --yes && \
    rm -rf /opt/conda/pkgs /home/mambauser/.cache

RUN micromamba run -n odyssai python -m pip install --no-cache-dir -r /tmp/requirements.txt && \
    micromamba clean --all --yes && \
    rm -rf /opt/conda/pkgs /home/mambauser/.cache

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY start.sh /usr/local/bin/start.sh
RUN install -m 0755 /usr/local/bin/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh && \
    install -m 0755 /usr/local/bin/start.sh /usr/local/bin/start.sh

    USER mambauser
COPY . .

ENV PYTHONPATH=/app/src BACKEND_PORT=9000 PORT=9000 HF_HOME=/data/hf
EXPOSE 9000

# Démarre l’app dans l’env conda
CMD ["bash","-lc","micromamba run -n odyssai /usr/local/bin/start.sh"]
