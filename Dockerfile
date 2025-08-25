# ---- Stage 1: build conda env ----
FROM mambaorg/micromamba:1.5.8 AS conda-builder
SHELL ["/bin/bash", "-lc"]
WORKDIR /app

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg libsndfile1 libportaudio2 ca-certificates \
      build-essential gcc g++ pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY environment-export.yml /tmp/environment.yml
COPY requirements.txt /tmp/requirements.txt

ENV PIP_NO_CACHE_DIR=1 \
    PIP_PREFER_BINARY=1

RUN micromamba create -y -n odyssai -f /tmp/environment.yml -c conda-forge
RUN micromamba install -y -n odyssai -c conda-forge conda-pack

# upgrade pip/setuptools/wheel pour éviter des build foireux
RUN micromamba run -n odyssai python -m pip install -U pip setuptools wheel

# installe toutes les deps Python
RUN micromamba run -n odyssai python -m pip install --no-cache-dir -r /tmp/requirements.txt

RUN micromamba clean --all --yes && rm -rf /opt/conda/pkgs /home/mambauser/.cache

RUN micromamba run -n odyssai conda-pack -n odyssai \
      -o /tmp/conda_env.tar.gz --ignore-editable-packages

# ---- Stage 2: runtime ----
FROM python:3.12-slim AS runtime
SHELL ["/bin/bash", "-lc"]
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    BACKEND_PORT=9000 \
    PORT=9000 \
    HF_HOME=/data/hf/.cache/huggingface \
    TRANSFORMERS_CACHE=/data/hf/.cache/huggingface \
    PATH="/opt/conda-env/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg libsndfile1 libportaudio2 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=conda-builder /tmp/conda_env.tar.gz /tmp/conda_env.tar.gz
RUN mkdir -p /opt/conda-env \
 && tar -xzf /tmp/conda_env.tar.gz -C /opt/conda-env \
 && rm /tmp/conda_env.tar.gz

# scripts + code (et tes permissions existantes si besoin)
COPY --chmod=0755 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY --chmod=0755 start.sh /usr/local/bin/start.sh
COPY . .

EXPOSE 9000
CMD ["bash", "-lc", "/usr/local/bin/start.sh"]