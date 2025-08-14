FROM continuumio/miniconda3:latest

SHELL ["/bin/bash", "-lc"]
WORKDIR /app

# Dépendances système utiles pour l'audio/ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg libsndfile1 libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

# Optionnel mais recommandé : installer mamba pour accélérer la résol
RUN conda install -n base -c conda-forge -y mamba \
    && conda clean -afy

# Environnement conda MINIMAL (python + pip + libs natives)
COPY environment-export.yml /tmp/environment.yml
RUN mamba env create -n odyssai -f /tmp/environment.yml --override-channels -c conda-forge \
    && conda clean -afy

# Packages Python via pip dans l'env
COPY requirements-export.txt /tmp/requirements.txt
RUN conda run -n odyssai pip install --no-cache-dir -r /tmp/requirements.txt

# Code
COPY . .

# Runtime
ENV PYTHONPATH=/app/src \
    BACKEND_PORT=9000
EXPOSE 9000

# (A) Utiliser conda run (robuste)
CMD ["conda","run","--no-capture-output","-n","odyssai","gunicorn","-c","gunicorn.conf.py","src.odyssai_core.app:app"]
